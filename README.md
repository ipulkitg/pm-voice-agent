# Sales Agent with LiveKit - Product Mentor AI

A real-time voice AI agent that serves as a product management mentor, powered by Lenny's Newsletter and Podcast knowledge base. Built with LiveKit for real-time communication, RAG (Retrieval-Augmented Generation) for knowledge retrieval, and a modern Next.js frontend.

## Table of Contents

- [Design Document](#design-document)
  - [System Architecture](#system-architecture)
  - [End-to-End Flow](#end-to-end-flow)
  - [RAG Integration](#rag-integration)
  - [Tools & Frameworks](#tools--frameworks)
- [Setup Instructions](#setup-instructions)
  - [Prerequisites](#prerequisites)
  - [Local Development Setup](#local-development-setup)
  - [Environment Variables](#environment-variables)
- [Design Decisions & Assumptions](#design-decisions--assumptions)
  - [Trade-offs & Limitations](#trade-offs--limitations)
  - [Hosting Assumptions](#hosting-assumptions)
  - [RAG Assumptions](#rag-assumptions)
  - [LiveKit Agent Design](#livekit-agent-design)

---

## Design Document

### System Architecture

The system consists of three main components:

1. **Backend Agent** (`agent.py`): Python-based LiveKit agent that handles voice interactions, RAG queries, and LLM responses
2. **RAG Pipeline** (`setup_rag.py`): Knowledge base indexing and retrieval system using Pinecone, LlamaIndex, and hybrid search
3. **Frontend** (`frontend/`): Next.js React application providing the voice interface

```
┌─────────────┐
│   User      │
│  (Browser)  │
└──────┬──────┘
       │ WebRTC
       ▼
┌─────────────────────┐
│  LiveKit Server     │
│  (Real-time comms)  │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  Agent (Python)     │
│  - DeepGram STT/TTS │
│  - Cerebras LLM     │
│  - RAG Query Engine │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  RAG System         │
│  - Pinecone (Vector)│
│  - BM25 (Keyword)   │
│  - Cohere (Rerank)  │
└─────────────────────┘
```

### End-to-End Flow

1. **User Interaction**:
   - User opens the Next.js frontend in their browser
   - Clicks "Start call" to initiate a session
   - Frontend generates a LiveKit token and connects to the LiveKit server

2. **Agent Initialization**:
   - LiveKit server dispatches the agent to the room
   - Agent initializes with DeepGram STT/TTS, Cerebras LLM, and Silero VAD
   - RAG query engine is lazily initialized on first use

3. **Conversation Flow**:
   - User speaks → DeepGram STT converts speech to text
   - Silero VAD detects speech boundaries
   - Agent processes the query:
     - If product-related: Calls `search_knowledge_base` tool
     - If competitive analysis: Calls `competitive_analysis` tool
   - RAG retrieval happens:
     - Hybrid search (Vector + BM25) retrieves top 15 chunks
     - Cohere reranks to top 5 most relevant chunks
     - LLM synthesizes response with retrieved context
   - Cerebras LLM generates response
   - DeepGram TTS converts response to speech
   - Audio streamed back to user via LiveKit

4. **Knowledge Base Updates**:
   - Articles and transcripts combined into `context/all_content.md`
   - Semantically chunked using embeddings in `setup_rag.py`
   - Indexed in Pinecone with OpenAI embeddings
   - BM25 index built for keyword search

### RAG Integration

The RAG system combines semantic and keyword search for knowledge retrieval:

1. **Document Ingestion**:
   - Articles crawled via FireCrawl and saved as markdown
   - Podcast transcripts generated using `podcast_transcriber.py`
   - Famous literature file (`famous_literature.md`) with 4 key articles
   - All content combined into `context/all_content.md` using `combine_articles.py`

2. **Chunking Strategy**:
   - Semantic chunking using `SemanticSplitterNodeParser` (buffer: 1 sentence, breakpoint: 95th percentile)
   - Chunks split at semantic boundaries for better context preservation

3. **Indexing**:
   - Vector store: Pinecone serverless (AWS us-east-1) with OpenAI `text-embedding-3-small` embeddings
   - BM25 index: In-memory keyword-based index for exact matches

4. **Retrieval Pipeline**:
   - Hybrid retrieval: Vector + BM25 using Reciprocal Rank Fusion (RRF, k=60)
   - Retrieves top 15 chunks, then Cohere reranks to top 5
   - LlamaIndex query engine synthesizes responses with `COMPACT` mode

5. **Agent Integration**:
   - RAG exposed as function tool: `search_knowledge_base(query: str)`
   - Lazy initialization: Query engine created on first use

### Tools & Frameworks

#### Backend
- **LiveKit Agents**: Real-time agent framework
- **LlamaIndex**: RAG orchestration and query engine
- **Pinecone**: Managed vector database (serverless)
- **OpenAI**: Embeddings (`text-embedding-3-small`)
- **Cohere**: Reranking (`rerank-english-v3.0`)
- **DeepGram**: Speech-to-text and text-to-speech
- **Cerebras**: LLM inference (`llama-3.3-70b`)
- **Silero**: Voice activity detection (VAD)
- **FireCrawl**: Web scraping for article collection

#### Frontend
- **Next.js 15**: React framework with App Router
- **LiveKit Client SDK**: WebRTC connection management
- **TypeScript**: Type safety
- **Tailwind CSS**: Styling
- **React Hooks**: State management

#### Infrastructure
- **Docker**: Containerization for agent deployment
- **LiveKit Cloud**: Managed LiveKit server (or self-hosted)

---

## Setup Instructions

### Prerequisites

- Python 3.13+
- Node.js 18+ and pnpm
- Docker (optional, for containerized deployment)
- API keys for all services (see below)

### Local Development Setup

#### 1. Clone and Navigate

```bash
git clone <repository-url>
cd sales-agent-livekit
```

#### 2. Backend Setup

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

#### 3. Frontend Setup

```bash
cd frontend
pnpm install
```

#### 4. Set Up Knowledge Base

```bash
# Step 1: Crawl articles (requires FIRECRAWL_API_KEY)
python article_parser.py

# Step 2: Transcribe podcasts (requires DEEPGRAM_API_KEY)
# Note: Update RSS feed URLs in podcast_transcriber.py before running
# - One podcast RSS URL is active in the script
# - The other podcast RSS URL is saved as a comment (switch before running)
python podcast_transcriber.py
# Run again with the second RSS URL after updating it in the script

# Step 3: Combine all content (famous_literature.md + articles + transcripts)
python combine_articles.py

# Step 4: Set up RAG pipeline (requires all API keys)
python setup_rag.py --rebuild-index
```

**Knowledge Base Content**:
- `famous_literature.md`: 4 famous articles about Lenny
- `context/articles/`: 8 articles (crawled via FireCrawl)
- `context/*.txt`: 2 podcast transcripts (generated via `podcast_transcriber.py`)

#### 5. Run Backend Agent

```bash
# From project root
python agent.py start
```

#### 6. Run Frontend

```bash
# From frontend directory
cd frontend
pnpm dev
```

Open `http://localhost:3000` in your browser.

### Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# LiveKit (Required)
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# DeepGram (Required for STT/TTS)
DEEPGRAM_API_KEY=your_deepgram_api_key

# Cerebras (Required for LLM)
CEREBRAS_API_KEY=your_cerebras_api_key

# OpenAI (Required for embeddings)
OPENAI_API_KEY=your_openai_api_key

# Pinecone (Required for vector DB)
PINECONE_API_KEY=your_pinecone_api_key

# Cohere (Required for reranking)
COHERE_API_KEY=your_cohere_api_key

# FireCrawl (Required for article crawling)
FIRECRAWL_API_KEY=your_firecrawl_api_key
```

For the frontend, create `frontend/.env.local`:

```env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
```

### Docker Deployment

```bash
# Build image
docker build -t sales-agent .

# Run container
docker run --env-file .env sales-agent
```

---

## Design Decisions & Assumptions

### Trade-offs & Limitations

#### 1. Chunking Strategy

**Decision**: Semantic chunking over fixed-size chunking

**Rationale**: Respects meaning boundaries, preserving context better than fixed-size chunks.

**Trade-offs**:
- ✅ Better semantic coherence and contextually relevant chunks
- ❌ Requires embedding model (API costs) and variable chunk sizes

#### 2. Hybrid Retrieval (Vector + BM25)

**Decision**: Combine semantic and keyword search using RRF

**Rationale**: Vector search excels at semantic similarity, BM25 at exact keyword matches. RRF combines both effectively.

**Trade-offs**:
- ✅ Best of both worlds: semantic understanding + keyword precision
- ❌ More complex than single retriever, requires maintaining two indexes

#### 3. Reranking

**Decision**: Use Cohere reranker after hybrid retrieval

**Rationale**: Reranking models specialize in relevance scoring, significantly improving final result quality.

**Trade-offs**:
- ✅ Better relevance at top ranks, reduces noise
- ❌ Additional API call adds latency (~100-200ms) and cost

#### 4. Lazy RAG Initialization

**Decision**: Initialize query engine only when first needed

**Rationale**: Avoids expensive initialization during Docker build, reduces cold start time.

**Trade-offs**:
- ✅ Faster container startup, no API calls during build
- ❌ First query has initialization delay (~2-3 seconds)

#### 5. Function Tool Approach

**Decision**: RAG exposed as function tool rather than always-on context

**Rationale**: Gives LLM control over when to search, reduces unnecessary searches for simple queries.

**Trade-offs**:
- ✅ LLM decides when knowledge base is needed, lower token usage
- ❌ Requires LLM to recognize when to use tool, might miss opportunities

#### 6. Voice-First Design

**Decision**: Optimize for voice interaction over text

**Rationale**: More natural and engaging for product mentorship, better for real-time conversations.

**Trade-offs**:
- ✅ More engaging user experience, better for nuanced discussions
- ❌ No persistent chat history, requires good audio quality

### Hosting Assumptions

For this project, we deployed the following hosting stack:

1. **Agent Deployment**: LiveKit Cloud
   - Managed LiveKit server handles scaling automatically
   - Agent runs as a service on LiveKit Cloud infrastructure
   - Eliminates need for self-hosted LiveKit server or AWS deployment

2. **Frontend**: Vercel
   - Next.js platform optimized for Vercel deployment
   - Server-side API route for LiveKit token generation
   - Automatic deployments and scaling

3. **Vector Database**: Pinecone
   - Pinecone serverless for vector storage and retrieval
   - AWS us-east-1 region
   - Managed service with no infrastructure maintenance required

This hosting combination provides a fully managed, scalable solution without requiring AWS or other cloud infrastructure management.

### RAG Assumptions

#### Vector Database Choice: Pinecone

**Why Pinecone**: Managed service with no infrastructure maintenance, serverless option (free tier), fast query performance, good LlamaIndex integration.

**Assumption**: Using Pinecone serverless for simplicity. Production might benefit from dedicated instance.

#### Chunking Strategy

**Current**: Semantic chunking with `SemanticSplitterNodeParser` (buffer: 1 sentence, breakpoint: 95th percentile). Uses embeddings to find semantic boundaries.

**Assumption**: Works well for long-form articles. Different content types (structured data, code) might need different chunking.

#### Embedding Model

**Current**: OpenAI `text-embedding-3-small` (1536 dims)

**Why**: Good balance of quality and cost, fast embedding generation, widely used and well-tested.

#### Reranking Model

**Current**: Cohere `rerank-english-v3.0`

**Why**: State-of-the-art reranking performance, fast inference, good API integration.

### LiveKit Agent Design

#### Agent Architecture

**Pattern**: Function tool-based agent with RAG

**Key Decisions**:
1. **Tool-based RAG**: RAG is a tool, not always-on context. LLM decides when to search for more efficient token usage.
2. **Lazy Initialization**: Query engine initialized on first use for faster startup, no API calls during build.
3. **Two Tools**: `search_knowledge_base` (primary RAG tool) and `competitive_analysis` (specialized framework-based tool).
4. **Voice-Optimized Instructions**: Optimized for voice delivery - avoids markdown/formatting, conversational tone, natural pauses.

#### STT/TTS: DeepGram

**Why DeepGram**: High accuracy, low latency, good developer experience, supports streaming.

#### LLM: Cerebras (Llama-3.3-70b)

**Why Cerebras**: Fast inference, good cost-performance ratio, supports function calling, strong reasoning capabilities.

## Project Structure

```
sales-agent-livekit/
├── agent.py                 # Main LiveKit agent
├── setup_rag.py             # RAG pipeline setup
├── article_parser.py        # FireCrawl article crawler
├── podcast_transcriber.py   # Podcast transcription script
├── combine_articles.py      # Combine articles into single file
├── requirements.txt        # Python dependencies
├── Dockerfile              # Agent containerization
├── livekit.toml           # LiveKit configuration
├── context/                # Knowledge base
│   ├── all_content.md      # Combined content (famous_literature + articles + transcripts)
│   ├── famous_literature.md # 4 famous articles about Lenny
│   ├── articles/           # 8 individual article markdown files
│   └── *.txt               # Podcast transcripts (2 files)
└── frontend/               # Next.js frontend
    ├── app/                # Next.js app router
    ├── components/         # React components
    ├── hooks/              # React hooks
    └── package.json        # Frontend dependencies
```

