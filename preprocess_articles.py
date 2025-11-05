"""
Preprocess articles for vector database ingestion.
Cleans markdown, extracts metadata, and chunks content appropriately.
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class ArticleChunk:
    """Represents a chunk of an article with metadata"""
    content: str
    chunk_index: int
    source_url: str
    title: str
    total_chunks: int
    metadata: Dict


class ArticlePreprocessor:
    """Preprocesses markdown articles for vector DB ingestion"""
    
    # Patterns to remove from markdown
    SUBSCRIPTION_PATTERNS = [
        r"SubscribeSign in",
        r"Subscribe.*?account\? Sign in",
        r"Lenny's Newsletter is a reader-supported publication.*?subscriber\.",
        r"Subscribe.*?new posts and support",
        r"Already have an account\? Sign in",
        r"By subscribing.*?Privacy Policy\.",
        r"Discover more from.*?subscribers",
    ]
    
    NAVIGATION_PATTERNS = [
        r"^\[!\[.*?\]\(.*?\)\]\(.*?\)$",  # Image links
        r"^Stories$",  # Navigation headers
        r"^Subscribe$",
        r"^Share$",
    ]
    
    # Patterns to extract metadata
    IMAGE_PATTERN = re.compile(r'!\[.*?\]\([^\)]+\)')
    EXCESSIVE_BREAKS = re.compile(r'\n{3,}')
    URL_PATTERN = re.compile(r'https?://[^\s\)]+')
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Args:
            chunk_size: Target size for each chunk (in characters)
            chunk_overlap: Overlap between chunks (in characters)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def extract_title(self, content: str) -> Optional[str]:
        """Extract article title from markdown"""
        # Look for first # heading
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
            # Clean up title (remove markdown links, etc.)
            title = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', title)
            return title
        
        # Fallback: look for second-level heading
        title_match = re.search(r'^##\s+(.+)$', content, re.MULTILINE)
        if title_match:
            return title_match.group(1).strip()
        
        return None
    
    def extract_url_from_filename(self, filename: str) -> Optional[str]:
        """Try to reconstruct URL from filename"""
        # Map known filenames to URLs
        url_map = {
            "how-to-know-if-youve-got-productmarket.md": "https://www.lennysnewsletter.com/p/how-to-know-if-youve-got-productmarket",
            "lenny-rachitskys-product-strategy-essentials.md": "https://www.theproductfolks.com/product-management-blog/lenny-rachitskys-product-strategy-essentials",
            "product-manager-habits.md": "https://maven.com/articles/product-manager-habits",
            "how-to-solve-problems-6bf14222e424.md": "https://uxdesign.cc/how-to-solve-problems-6bf14222e424",
            "what-buddhism-taught-me-about-product-management-f05c7486649c.md": "https://medium.com/swlh/what-buddhism-taught-me-about-product-management-f05c7486649c",
            "what-it-feels-like-when-you-ve-found-product-market-fit-by-lenny-rachitsky.md": "https://www.producthunt.com/stories/what-it-feels-like-when-you-ve-found-product-market-fit-by-lenny-rachitsky",
            "the-secret-to-a-great-planning-process-lessons-from-airbnb-and-eventbrite.md": "https://review.firstround.com/the-secret-to-a-great-planning-process-lessons-from-airbnb-and-eventbrite/",
            "how-lenny-rachitsky-helps-teams-build-strategy-template.md": "https://www.notion.com/blog/how-lenny-rachitsky-helps-teams-build-strategy-template",
        }
        return url_map.get(filename)
    
    def clean_markdown(self, content: str) -> str:
        """Remove noise from markdown content"""
        # Remove subscription prompts
        for pattern in self.SUBSCRIPTION_PATTERNS:
            content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove standalone image links (keep images in context)
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            # Skip navigation lines
            if any(re.match(pattern, line.strip()) for pattern in self.NAVIGATION_PATTERNS):
                continue
            # Skip standalone image markdown (but keep images that are part of content)
            if re.match(r'^!\[.*?\]\(.*?\)$', line.strip()):
                # Only skip if it's a standalone line (not part of a paragraph)
                if len(line.strip()) < 200:  # Short lines are likely navigation images
                    continue
            cleaned_lines.append(line)
        
        content = '\n'.join(cleaned_lines)
        
        # Remove excessive line breaks
        content = self.EXCESSIVE_BREAKS.sub('\n\n', content)
        
        # Remove image URLs that are just markdown (but keep alt text context)
        # This is more nuanced - we'll keep images that have meaningful alt text
        content = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', content)
        
        # Clean up whitespace
        content = re.sub(r'[ \t]+', ' ', content)  # Multiple spaces to single
        content = re.sub(r' *\n *', '\n', content)  # Clean line breaks
        
        return content.strip()
    
    def chunk_content(self, content: str) -> List[str]:
        """Split content into overlapping chunks"""
        chunks = []
        
        # First, try to split by sections (## headings)
        sections = re.split(r'\n(##\s+)', content)
        if len(sections) > 1:
            # Reconstruct sections
            current_section = sections[0]
            for i in range(1, len(sections), 2):
                if i + 1 < len(sections):
                    current_section += '\n' + sections[i] + sections[i + 1]
            
            # Split by paragraphs within sections
            paragraphs = re.split(r'\n\n+', content)
        else:
            # Fallback: split by paragraphs
            paragraphs = re.split(r'\n\n+', content)
        
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If adding this paragraph would exceed chunk size
            if len(current_chunk) + len(para) + 2 > self.chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # Start new chunk with overlap
                if self.chunk_overlap > 0:
                    # Take last part of current chunk for overlap
                    overlap_text = current_chunk[-self.chunk_overlap:]
                    current_chunk = overlap_text + '\n\n' + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    current_chunk += '\n\n' + para
                else:
                    current_chunk = para
        
        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # If content is short, return as single chunk
        if len(chunks) == 0:
            chunks = [content]
        
        return chunks
    
    def process_article(self, filepath: Path) -> List[ArticleChunk]:
        """Process a single article file"""
        print(f"📄 Processing: {filepath.name}")
        
        # Read content
        content = filepath.read_text(encoding='utf-8')
        
        # Extract metadata
        title = self.extract_title(content) or filepath.stem.replace('-', ' ').title()
        source_url = self.extract_url_from_filename(filepath.name) or "unknown"
        
        # Clean content
        cleaned_content = self.clean_markdown(content)
        
        if not cleaned_content or len(cleaned_content.strip()) < 100:
            print(f"⚠️  Warning: {filepath.name} has very little content after cleaning")
            return []
        
        # Chunk content
        chunks = self.chunk_content(cleaned_content)
        
        print(f"   ✅ Created {len(chunks)} chunks ({len(cleaned_content)} chars)")
        
        # Create ArticleChunk objects
        article_chunks = []
        for idx, chunk_content in enumerate(chunks):
            chunk = ArticleChunk(
                content=chunk_content,
                chunk_index=idx,
                source_url=source_url,
                title=title,
                total_chunks=len(chunks),
                metadata={
                    "source_file": filepath.name,
                    "chunk_size": len(chunk_content),
                }
            )
            article_chunks.append(chunk)
        
        return article_chunks
    
    def process_all_articles(self, articles_dir: Path, output_dir: Path) -> List[ArticleChunk]:
        """Process all articles in a directory"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        all_chunks = []
        article_files = list(articles_dir.glob("*.md"))
        
        print(f"🚀 Processing {len(article_files)} articles...")
        print("=" * 60)
        
        for article_file in article_files:
            try:
                chunks = self.process_article(article_file)
                all_chunks.extend(chunks)
                
                # Save cleaned version
                cleaned_file = output_dir / f"cleaned_{article_file.name}"
                if chunks:
                    # Reconstruct cleaned content
                    cleaned_content = '\n\n---\n\n'.join([chunk.content for chunk in chunks])
                    cleaned_file.write_text(cleaned_content, encoding='utf-8')
                    
            except Exception as e:
                print(f"❌ Error processing {article_file.name}: {e}")
        
        # Save metadata
        metadata_file = output_dir / "chunks_metadata.json"
        metadata = {
            "total_chunks": len(all_chunks),
            "total_articles": len(article_files),
            "chunks": [asdict(chunk) for chunk in all_chunks]
        }
        metadata_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        
        print("\n" + "=" * 60)
        print(f"✅ Processed {len(all_chunks)} chunks from {len(article_files)} articles")
        print(f"📁 Cleaned articles saved to: {output_dir}")
        print(f"📊 Metadata saved to: {metadata_file}")
        
        return all_chunks


def main():
    """Main function"""
    articles_dir = Path("context/articles")
    output_dir = Path("context/processed_articles")
    
    if not articles_dir.exists():
        print(f"❌ Articles directory not found: {articles_dir}")
        return
    
    preprocessor = ArticlePreprocessor(
        chunk_size=1000,  # ~1000 characters per chunk
        chunk_overlap=200  # 200 character overlap
    )
    
    chunks = preprocessor.process_all_articles(articles_dir, output_dir)
    
    print(f"\n🎉 Ready for vector DB ingestion!")
    print(f"   Total chunks: {len(chunks)}")
    print(f"\n💡 Next steps:")
    print(f"   1. Review cleaned articles in: {output_dir}")
    print(f"   2. Use chunks from metadata.json for vector DB")
    print(f"   3. Each chunk has: content, title, source_url, metadata")


if __name__ == "__main__":
    main()

