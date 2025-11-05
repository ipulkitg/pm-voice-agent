import os
import re
from pathlib import Path
from firecrawl import Firecrawl
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

url_arr = ["https://www.lennysnewsletter.com/p/how-to-know-if-youve-got-productmarket",
           "https://www.theproductfolks.com/product-management-blog/lenny-rachitskys-product-strategy-essentials",
           "https://maven.com/articles/product-manager-habits",
           "https://uxdesign.cc/how-to-solve-problems-6bf14222e424",
           "https://medium.com/swlh/what-buddhism-taught-me-about-product-management-f05c7486649c",
           "https://www.producthunt.com/stories/what-it-feels-like-when-you-ve-found-product-market-fit-by-lenny-rachitsky",
           "https://review.firstround.com/the-secret-to-a-great-planning-process-lessons-from-airbnb-and-eventbrite/",
           "https://www.notion.com/blog/how-lenny-rachitsky-helps-teams-build-strategy-template"
           ]


def sanitize_filename(url):
    """Generate a safe filename from a URL"""
    # Extract the last meaningful part of the URL
    url = url.rstrip('/')
    parts = url.split('/')
    
    # Try to get the last non-empty part
    filename = parts[-1] if parts[-1] else parts[-2] if len(parts) > 1 else "article"
    
    # Remove query parameters if any
    filename = filename.split('?')[0]
    
    # Replace invalid filename characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Limit length
    if len(filename) > 100:
        filename = filename[:100]
    
    # If filename is empty or too short, use a hash of the URL
    if not filename or len(filename) < 3:
        import hashlib
        filename = hashlib.md5(url.encode()).hexdigest()[:10]
    
    return filename


def crawl_and_save_articles():
    """Crawl all articles using Firecrawl and save them as Markdown files"""
    
    # Get API key from environment
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise ValueError("FIRECRAWL_API_KEY not found in environment variables. Please set it in your .env file.")
    
    # Initialize Firecrawl
    app = Firecrawl(api_key=api_key)
    
    # Ensure context/articles directory exists
    context_dir = Path("context/articles")
    context_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🚀 Starting to crawl {len(url_arr)} articles...")
    print("=" * 60)
    
    success_count = 0
    error_count = 0
    
    for idx, url in enumerate(url_arr, 1):
        try:
            print(f"\n[{idx}/{len(url_arr)}] Crawling: {url}")
            
            # Scrape the URL and get markdown content
            # Try different possible API signatures
            try:
                result = app.scrape(url, params={"formats": ["markdown"], "onlyMainContent": True})
            except TypeError:
                # If params doesn't work, try without params or with different signature
                try:
                    result = app.scrape(url, {"formats": ["markdown"], "onlyMainContent": True})
                except TypeError:
                    result = app.scrape(url)
            
            # Extract markdown content - handle different response formats
            if isinstance(result, dict):
                # Try different possible keys in the response
                markdown_content = (
                    result.get("markdown", "") or 
                    result.get("content", "") or
                    result.get("data", {}).get("markdown", "") or
                    result.get("data", {}).get("content", "")
                )
            elif hasattr(result, "markdown"):
                markdown_content = result.markdown
            elif hasattr(result, "content"):
                markdown_content = result.content
            elif hasattr(result, "data"):
                data = result.data if hasattr(result.data, "__getitem__") else {}
                markdown_content = data.get("markdown", "") if isinstance(data, dict) else str(result)
            else:
                markdown_content = str(result)
            
            if not markdown_content:
                print(f"⚠️  Warning: No content extracted from {url}")
                error_count += 1
                continue
            
            # Generate filename
            base_filename = sanitize_filename(url)
            filename = f"{base_filename}.md"
            filepath = context_dir / filename
            
            # Save to file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            
            print(f"✅ Saved: {filepath} ({len(markdown_content)} characters)")
            success_count += 1
            
        except Exception as e:
            print(f"❌ Error processing {url}: {e}")
            error_count += 1
    
    print("\n" + "=" * 60)
    print(f"🎉 Complete! Successfully saved {success_count} articles")
    if error_count > 0:
        print(f"⚠️  {error_count} articles failed to process")
    print(f"📁 All files saved in: {context_dir.absolute()}")


if __name__ == "__main__":
    crawl_and_save_articles()
