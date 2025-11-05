"""
Combine all context files into a single file for LlamaIndex.
Order: Famous Literature → Articles → Text Files
"""

import re
from pathlib import Path


def minimal_clean_markdown(content: str) -> str:
    """
    Minimal cleaning - just remove obvious noise.
    LlamaIndex will handle the rest perfectly.
    """
    # Remove subscription prompts (common patterns)
    subscription_patterns = [
        r"SubscribeSign in",
        r"Subscribe.*?account\? Sign in",
        r"Lenny's Newsletter is a reader-supported publication.*?subscriber\.",
        r"Already have an account\? Sign in",
        r"By subscribing.*?Privacy Policy\.",
        r"Discover more from.*?subscribers",
    ]
    
    for pattern in subscription_patterns:
        content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove excessive line breaks (but keep paragraph breaks)
    content = re.sub(r'\n{4,}', '\n\n\n', content)
    
    # Clean up whitespace
    content = re.sub(r'[ \t]+', ' ', content)
    content = re.sub(r' *\n *', '\n', content)
    
    return content.strip()


def combine_all_files(context_dir: Path, output_file: Path):
    """
    Combine all files in order: Famous → Articles → Text Files
    """
    print(f"📚 Combining all context files...")
    print("=" * 60)
    
    combined_content = []
    
    # Track counts
    famous_count = 0
    article_count = 0
    txt_count = 0
    
    # 1. Famous Literature (famous_literature.md)
    famous_file = context_dir / "famous_literature.md"
    if famous_file.exists():
        print(f"[1/1] Processing: {famous_file.name}")
        content = famous_file.read_text(encoding='utf-8')
        cleaned = minimal_clean_markdown(content)
        combined_content.append("# Famous Literature\n")
        combined_content.append(f"{'='*80}\n\n")
        combined_content.append(cleaned)
        combined_content.append("\n\n")
        famous_count = 1
    else:
        print(f"⚠️  {famous_file.name} not found, skipping...")
    
    # 2. Articles (from context/articles/)
    articles_dir = context_dir / "articles"
    article_files = []
    if articles_dir.exists():
        article_files = sorted(articles_dir.glob("*.md"))
        print(f"\n[2/2] Processing {len(article_files)} articles...")
        combined_content.append(f"\n{'='*80}\n")
        combined_content.append("# Articles\n")
        combined_content.append(f"{'='*80}\n\n")
        
        for idx, article_file in enumerate(article_files, 1):
            print(f"  [{idx}/{len(article_files)}] {article_file.name}")
            content = article_file.read_text(encoding='utf-8')
            cleaned = minimal_clean_markdown(content)
            
            combined_content.append(f"\n## Article {idx}: {article_file.stem}\n")
            combined_content.append(f"{'-'*80}\n\n")
            combined_content.append(cleaned)
            combined_content.append("\n\n")
        article_count = len(article_files)
    else:
        print(f"⚠️  Articles directory not found: {articles_dir}")
    
    # 3. Text Files (podcast transcripts, etc.)
    txt_files = sorted(context_dir.glob("*.txt"))
    if txt_files:
        print(f"\n[3/3] Processing {len(txt_files)} text files...")
        combined_content.append(f"\n{'='*80}\n")
        combined_content.append("# Text Files (Podcasts, etc.)\n")
        combined_content.append(f"{'='*80}\n\n")
        
        for idx, txt_file in enumerate(txt_files, 1):
            print(f"  [{idx}/{len(txt_files)}] {txt_file.name}")
            content = txt_file.read_text(encoding='utf-8')
            # Minimal cleaning for txt files (just whitespace)
            cleaned = re.sub(r'\n{4,}', '\n\n\n', content.strip())
            
            combined_content.append(f"\n## Text File {idx}: {txt_file.stem}\n")
            combined_content.append(f"{'-'*80}\n\n")
            combined_content.append(cleaned)
            combined_content.append("\n\n")
        txt_count = len(txt_files)
    else:
        print(f"⚠️  No text files found in {context_dir}")
    
    # Write combined file
    combined_text = '\n'.join(combined_content)
    output_file.write_text(combined_text, encoding='utf-8')
    
    total_files = famous_count + article_count + txt_count
    
    print(f"\n✅ Combined file created: {output_file}")
    print(f"   Size: {output_file.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"   Total files: {total_files}")
    print(f"     - Famous Literature: {famous_count}")
    print(f"     - Articles: {article_count}")
    print(f"     - Text Files: {txt_count}")
    print(f"\n💡 Ready for LlamaIndex!")


def main():
    """Main function"""
    context_dir = Path("context")
    output_file = Path("context/all_content.md")
    
    if not context_dir.exists():
        print(f"❌ Context directory not found: {context_dir}")
        return
    
    combine_all_files(context_dir, output_file)
    
    print(f"\n🎉 Ready for LlamaIndex!")
    print(f"   File location: {output_file.absolute()}")
    print(f"\n📖 Example LlamaIndex usage:")
    print(f"   from llama_index.core import SimpleDirectoryReader")
    print(f"   documents = SimpleDirectoryReader('context', filename_as_id=True).load_data()")
    print(f"   # Or load the combined file:")
    print(f"   documents = SimpleDirectoryReader(input_files=['context/all_content.md']).load_data()")


if __name__ == "__main__":
    main()

