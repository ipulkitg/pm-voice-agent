"""
Phase 1 & 2: RAG Pipeline Setup
- Phase 1: Loads context data, chunks it semantically, indexes with Pinecone,
  and sets up hybrid retrieval (Vector + BM25)
- Phase 2: Creates hybrid retriever, adds reranking, and sets up query engine
"""

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# LlamaIndex imports
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext
from llama_index.core.node_parser import SemanticSplitterNodeParser, SentenceSplitter
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import ResponseMode
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle

# Reranking imports (optional dependency)
try:
    from llama_index.postprocessor.cohere_rerank import CohereRerank
except ImportError:
    CohereRerank = None  # Optional – script will continue without reranking

# Pinecone imports
from pinecone import Pinecone, ServerlessSpec

# Load environment variables
load_dotenv()

CONTEXT_FILE = Path("context") / "all_content.md"
PINECONE_INDEX_NAME = "sales-agent-kb"
DEFAULT_EMBED_MODEL = "text-embedding-3-small"
DEFAULT_EMBED_DIM = 1536  # OpenAI text-embedding-3-small dimension
DEFAULT_RERANK_MODEL = "rerank-english-v3.0"
SEMANTIC_BUFFER_SIZE = 1
SEMANTIC_BREAKPOINT_PERCENTILE = 95


def _ensure_context_file() -> Path:
    """Validate that the markdown knowledge base exists."""
    if not CONTEXT_FILE.exists():
        raise FileNotFoundError(
            f"Context file not found: {CONTEXT_FILE}. "
            "Run preprocess_articles.py or place all_content.md in the context directory."
        )
    return CONTEXT_FILE


def _load_documents():
    """Load markdown content into LlamaIndex Document objects."""
    context_file = _ensure_context_file()
    return SimpleDirectoryReader(
        input_files=[str(context_file)],
        required_exts=[".md"],
    ).load_data()


def _get_embed_model() -> OpenAIEmbedding:
    """Create the shared embedding model, ensuring credentials are present."""
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    return OpenAIEmbedding(
        model=DEFAULT_EMBED_MODEL,
        api_key=openai_api_key,
    )


def _chunk_documents(documents, embed_model):
    """Split documents with the semantic splitter so both vector and BM25 retrievers share chunks."""
    semantic_splitter = SemanticSplitterNodeParser(
        buffer_size=SEMANTIC_BUFFER_SIZE,
        breakpoint_percentile_threshold=SEMANTIC_BREAKPOINT_PERCENTILE,
        embed_model=embed_model,
    )
    return semantic_splitter.get_nodes_from_documents(documents)


def _get_or_create_pinecone_index():
    """Set up the Pinecone index used by LlamaIndex."""
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    if not pinecone_api_key:
        raise ValueError("PINECONE_API_KEY not found in environment variables")
    
    pc = Pinecone(api_key=pinecone_api_key)
    
    # Check if index exists, create if it doesn't
    existing_indexes = [idx.name for idx in pc.list_indexes()]
    if PINECONE_INDEX_NAME not in existing_indexes:
        print(f"📦 Creating Pinecone index: {PINECONE_INDEX_NAME}")
        # Use serverless spec (free tier compatible)
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=DEFAULT_EMBED_DIM,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )
        print(f"✅ Index created: {PINECONE_INDEX_NAME}")
    else:
        print(f"♻️  Using existing Pinecone index: {PINECONE_INDEX_NAME}")
    
    return pc.Index(PINECONE_INDEX_NAME)


def _create_bm25_retriever(nodes, similarity_top_k=10):
    """Helper to keep BM25 creation consistent."""
    return BM25Retriever.from_defaults(nodes=nodes, similarity_top_k=similarity_top_k)


def _build_reranker(rerank_top_n: int):
    """Create the Cohere reranker, ensuring the dependency and key exist."""
    if CohereRerank is None:
        raise ImportError(
            "Missing llama-index-postprocessor-cohere-rerank. "
            "Install it with `uv pip install llama-index-postprocessor-cohere-rerank`."
        )

    cohere_api_key = os.getenv("COHERE_API_KEY")
    if not cohere_api_key:
        raise ValueError("COHERE_API_KEY not found in environment variables")

    return CohereRerank(
        top_n=rerank_top_n,
        api_key=cohere_api_key,
        model=DEFAULT_RERANK_MODEL,
    )


@dataclass
class RagArtifacts:
    index: VectorStoreIndex
    nodes: List
    hybrid_retriever: BaseRetriever
    query_engine: RetrieverQueryEngine
    reranker: Optional["CohereRerank"]


def _prepare_index_and_nodes(embed_model, rebuild_index: bool = False):
    """Load documents, chunk them, and either build or load the Pinecone-backed index."""
    pinecone_index = _get_or_create_pinecone_index()
    vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Check if index is empty (Pinecone doesn't have a simple count method)
    # We'll use rebuild_index flag or check index stats
    index_stats = pinecone_index.describe_index_stats()
    index_count = index_stats.get('total_vector_count', 0)
    should_rebuild = rebuild_index or index_count == 0
    
    if should_rebuild:
        # Only chunk and embed when rebuilding
        documents = _load_documents()
        print(f"✅ Loaded {len(documents)} document(s) from {CONTEXT_FILE}")
        print(f"   Document size: {len(documents[0].text)} characters")

        print("📝 Chunking documents (this requires embeddings for semantic splitting)...")
        nodes = _chunk_documents(documents, embed_model)
        chunk_sizes = [len(node.text) for node in nodes]
        avg_chunk = sum(chunk_sizes) // len(chunk_sizes)
        print(f"✅ Created {len(nodes)} semantic chunks | avg={avg_chunk} chars, min={min(chunk_sizes)}, max={max(chunk_sizes)}")

        print("🔁 Building vector index inside Pinecone (embedding chunks)...")
        index = VectorStoreIndex(
            nodes=nodes,
            storage_context=storage_context,
            embed_model=embed_model,
            show_progress=True,
        )
        print(f"✅ Uploaded {len(nodes)} vectors to Pinecone")
    else:
        # Reuse existing index - no need to re-chunk semantically
        print(f"♻️  Reusing existing Pinecone index ({index_count} vectors)...")
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            embed_model=embed_model,
        )
        
        # For BM25, we need nodes but don't need semantic chunking
        # Use a simple sentence splitter to avoid embedding calls
        print("📝 Loading documents for BM25 retriever (using simple chunking, no embeddings)...")
        documents = _load_documents()
        # Use simple sentence splitter - no embeddings needed
        simple_splitter = SentenceSplitter(chunk_size=2000, chunk_overlap=200)
        nodes = simple_splitter.get_nodes_from_documents(documents)
        print(f"✅ Created {len(nodes)} nodes for BM25 retriever (simple chunking)")

    print(f"💾 Pinecone index: {PINECONE_INDEX_NAME}")
    return index, nodes


def _build_hybrid_retriever(index, nodes, embed_model, similarity_top_k: int):
    """Return a single hybrid retriever that always combines dense and sparse signals."""
    vector_retriever = index.as_retriever(
        similarity_top_k=similarity_top_k,
        embed_model=embed_model,
    )
    bm25_retriever = _create_bm25_retriever(nodes, similarity_top_k=similarity_top_k)
    return HybridRetriever(
        vector_retriever=vector_retriever,
        bm25_retriever=bm25_retriever,
        top_k=similarity_top_k,
        rrf_k=60,
    )


class HybridRetriever(BaseRetriever):
    """
    Custom hybrid retriever that combines Vector and BM25 retrievers
    using Reciprocal Rank Fusion (RRF)
    """
    
    def __init__(
        self,
        vector_retriever: BaseRetriever,
        bm25_retriever: BaseRetriever,
        top_k: int = 15,
        rrf_k: int = 60,
    ):
        """
        Args:
            vector_retriever: Vector/semantic retriever
            bm25_retriever: BM25/keyword retriever
            top_k: Number of results to return
            rrf_k: RRF constant (typically 60)
        """
        super().__init__()
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        self.top_k = top_k
        self.rrf_k = rrf_k
    
    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """Retrieve nodes using hybrid search with RRF"""
        # Get results from both retrievers
        vector_nodes = self.vector_retriever.retrieve(query_bundle)
        bm25_nodes = self.bm25_retriever.retrieve(query_bundle)
        
        # Combine results using Reciprocal Rank Fusion
        combined_scores = {}
        
        # Add vector results
        for rank, node in enumerate(vector_nodes, start=1):
            node_id = node.node.node_id
            rrf_score = 1.0 / (self.rrf_k + rank)
            if node_id in combined_scores:
                combined_scores[node_id]["score"] += rrf_score
            else:
                combined_scores[node_id] = {
                    "node": node.node,
                    "score": rrf_score,
                    "metadata": node.node.metadata
                }
        
        # Add BM25 results
        for rank, node in enumerate(bm25_nodes, start=1):
            node_id = node.node.node_id
            rrf_score = 1.0 / (self.rrf_k + rank)
            if node_id in combined_scores:
                combined_scores[node_id]["score"] += rrf_score
            else:
                combined_scores[node_id] = {
                    "node": node.node,
                    "score": rrf_score,
                    "metadata": node.node.metadata
                }
        
        # Sort by combined score and return top_k
        sorted_results = sorted(
            combined_scores.values(),
            key=lambda x: x["score"],
            reverse=True
        )[:self.top_k]
        
        # Convert back to NodeWithScore format
        return [
            NodeWithScore(node=item["node"], score=item["score"])
            for item in sorted_results
        ]


def setup_rag(
    rebuild_index: bool = False,
    similarity_top_k: int = 15,
    rerank_top_n: int = 5,
    use_reranking: bool = True,
    response_mode: ResponseMode = ResponseMode.COMPACT,
    verbose: bool = True,
) -> RagArtifacts:
    """
    Set up the full RAG stack:
    - semantic chunking over context/all_content.md
    - persistent Pinecone vector index
    - single hybrid retriever (dense + BM25 via RRF)
    - optional Cohere reranking
    """
    print("🚀 Setting up hybrid RAG pipeline")
    embed_model = _get_embed_model()
    index, nodes = _prepare_index_and_nodes(embed_model, rebuild_index=rebuild_index)
    hybrid_retriever = _build_hybrid_retriever(index, nodes, embed_model, similarity_top_k=similarity_top_k)
    print(f"✅ Hybrid retriever ready (top_k={similarity_top_k}, mode=RRF)")

    reranker = None
    if use_reranking:
        reranker = _build_reranker(rerank_top_n)
        print(f"✅ Cohere reranker ready ({DEFAULT_RERANK_MODEL}, top_n={rerank_top_n})")

    query_engine = RetrieverQueryEngine.from_args(
        retriever=hybrid_retriever,
        response_mode=response_mode,
        node_postprocessors=[reranker] if reranker else [],
        verbose=verbose,
    )
    print("✅ Query engine initialized")

    final_top_k = rerank_top_n if reranker else similarity_top_k
    print(
        f"\n📊 Configuration: hybrid_top_k={similarity_top_k}, "
        f"reranking={'on' if reranker else 'off'}, final_top_k={final_top_k}"
    )

    return RagArtifacts(
        index=index,
        nodes=nodes,
        hybrid_retriever=hybrid_retriever,
        query_engine=query_engine,
        reranker=reranker,
    )


def get_query_engine(**kwargs) -> RetrieverQueryEngine:
    """Convenience helper to return just the query engine."""
    artifacts = setup_rag(**kwargs)
    return artifacts.query_engine


def _demo_queries(query_engine: RetrieverQueryEngine):
    """Run a few smoke-test queries so setup issues surface quickly."""
    sample_queries = [
        "What is product sense?",
        "How do you differentiate a product?",
        "What are the key points about the W Framework?",
    ]

    for query in sample_queries:
        print(f"\n{'=' * 60}\nQuery: {query}\n{'=' * 60}")
        try:
            response = query_engine.query(query)
            text = response.response or ""
            print(f"\n✅ Response preview:\n{text[:500]}{'...' if len(text) > 500 else ''}")
            print(f"📚 Source nodes: {len(response.source_nodes)}")
        except Exception as exc:
            print(f"❌ Query failed: {exc}")


def _main():
    parser = argparse.ArgumentParser(description="Hybrid RAG setup using LlamaIndex + Pinecone + Cohere reranking.")
    parser.add_argument(
        "--rebuild-index",
        action="store_true",
        help="Force re-embedding context/all_content.md into Pinecone.",
    )
    parser.add_argument(
        "--no-rerank",
        action="store_true",
        help="Skip Cohere reranking (not recommended).",
    )
    parser.add_argument(
        "--similarity-top-k",
        type=int,
        default=15,
        help="How many nodes to pull from the hybrid retriever before reranking.",
    )
    parser.add_argument(
        "--rerank-top-n",
        type=int,
        default=5,
        help="How many nodes to keep after Cohere reranking.",
    )
    parser.add_argument(
        "--skip-demo",
        action="store_true",
        help="Only set up the pipeline without running sample questions.",
    )
    args = parser.parse_args()

    artifacts = setup_rag(
        rebuild_index=args.rebuild_index,
        similarity_top_k=args.similarity_top_k,
        rerank_top_n=args.rerank_top_n,
        use_reranking=not args.no_rerank,
    )

    if not args.skip_demo:
        _demo_queries(artifacts.query_engine)


if __name__ == "__main__":
    _main()


if __name__ == "__main__":
    import sys
    
    # Check if user wants to run Phase 1, Phase 2, or both
    run_phase1 = "--phase1" in sys.argv or "--all" in sys.argv or len(sys.argv) == 1
    run_phase2 = "--phase2" in sys.argv or "--all" in sys.argv or len(sys.argv) == 1
    
    if run_phase1:
        # Run Phase 1 setup
        rag_pipeline = setup_rag_pipeline()
        
        # Test retrieval (optional)
        print("\n" + "=" * 60)
        print("🧪 Testing Phase 1 Retrieval...")
        print("=" * 60)
        
        test_query = "What is product sense?"
        print(f"\nQuery: {test_query}")
        
        # Test vector retriever
        vector_results = rag_pipeline["vector_retriever"].retrieve(test_query)
        print(f"\n✅ Vector retriever found {len(vector_results)} results")
        print(f"   First result preview: {vector_results[0].text[:200]}...")
        
        # Test BM25 retriever (if available)
        if rag_pipeline.get("bm25_retriever"):
            bm25_results = rag_pipeline["bm25_retriever"].retrieve(test_query)
            print(f"\n✅ BM25 retriever found {len(bm25_results)} results")
            print(f"   First result preview: {bm25_results[0].text[:200]}...")
        else:
            print("\n⚠️  BM25 retriever not available (vector-only mode)")
    
    if run_phase2:
        # Run Phase 2 setup
        print("\n" + "=" * 60)
        print("🧪 Testing Phase 2 Query Engine...")
        print("=" * 60)
        
        # Get query engine (will load from Phase 1 if needed)
        if run_phase1 and 'rag_pipeline' in locals():
            query_engine = setup_query_engine(rag_pipeline=rag_pipeline)
        else:
            query_engine = get_query_engine()
        
        # Test query
        test_queries = [
            "What is product sense?",
            "How do you differentiate a product?",
            "What are the key points about the W Framework?"
        ]
        
        for test_query in test_queries:
            print(f"\n{'='*60}")
            print(f"Query: {test_query}")
            print(f"{'='*60}")
            
            try:
                response = query_engine.query(test_query)
                print(f"\n✅ Response:")
                print(f"{response.response[:500]}...")
                print(f"\n📊 Retrieved {len(response.source_nodes)} source nodes")
            except Exception as e:
                print(f"\n❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Setup Complete!")
    print("=" * 60)
    print("\n💡 Usage in your agent:")
    print("   from setup_rag import get_query_engine")
    print("   query_engine = get_query_engine()")
    print("   response = query_engine.query('your question')")
