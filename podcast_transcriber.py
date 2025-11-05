"""
Podcast Transcription Script
Downloads audio from podcast RSS feeds and transcribes it using Deepgram API.
The transcript is saved to the context directory for use by the sales agent.
"""

import os
import feedparser
import requests
from pathlib import Path
from dotenv import load_dotenv
import tempfile
import json

load_dotenv()

# Configuration
CONTEXT_DIR = Path("context")
CONTEXT_DIR.mkdir(exist_ok=True)


def get_podcast_rss_url(spotify_url):
    """
    For Spotify podcast URLs, you'll need to find the RSS feed.
    Many podcasts have their RSS feed listed on their website or podcast platforms.
    
    Alternatively, you can use services like:
    - https://podcastaddict.com/ (to find RSS feeds)
    - https://www.listennotes.com/api/ (API to convert Spotify URLs to RSS)
    """
    # This is a placeholder - you'll need to manually find or use an API
    # to convert Spotify URLs to RSS feeds
    print(f"⚠️  Note: Spotify URLs need to be converted to RSS feeds.")
    print(f"   You can find RSS feeds at: https://www.listennotes.com/")
    return None


def download_audio(audio_url, output_path):
    """Download audio file from URL"""
    print(f"📥 Downloading audio from {audio_url}...")
    response = requests.get(audio_url, stream=True)
    response.raise_for_status()
    
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"✅ Downloaded to {output_path}")


def transcribe_audio(audio_path):
    """
    Transcribe audio using Deepgram REST API.
    No ffmpeg or local models required!
    """
    print(f"🎤 Transcribing audio with Deepgram...")
    
    # Get API key from environment
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        raise ValueError("DEEPGRAM_API_KEY not found in environment variables")
    
    # Deepgram API endpoint
    url = "https://api.deepgram.com/v1/listen"
    
    # Read audio file
    with open(audio_path, "rb") as audio_file:
        audio_data = audio_file.read()
    
    # Get file extension for content type
    file_ext = Path(audio_path).suffix.lower()
    content_type_map = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
    }
    content_type = content_type_map.get(file_ext, "audio/mpeg")
    
    # Headers
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": content_type,
    }
    
    # Parameters
    params = {
        "model": "nova-2",
        "smart_format": "true",
        "punctuate": "true",
    }
    
    # Make request with proper file upload
    response = requests.post(
        url,
        headers=headers,
        params=params,
        data=audio_data
    )
    
    response.raise_for_status()
    result = response.json()
    
    # Extract transcript text
    transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]
    
    return transcript


def get_podcast_episodes(rss_url, limit=1):
    """Parse RSS feed and get episode information"""
    print(f"📡 Fetching podcast feed from {rss_url}...")
    
    feed = feedparser.parse(rss_url)
    
    if not feed.entries:
        raise ValueError("No episodes found in RSS feed")
    
    episodes = []
    for entry in feed.entries[:limit]:
        # Get audio URL (usually in enclosures)
        audio_url = None
        if entry.enclosures:
            for enc in entry.enclosures:
                if enc.get('type', '').startswith('audio'):
                    audio_url = enc.get('href')
                    break
        
        if not audio_url:
            # Try alternate location
            audio_url = entry.get('link')
        
        episodes.append({
            'title': entry.get('title', 'Unknown'),
            'audio_url': audio_url,
            'description': entry.get('summary', ''),
            'published': entry.get('published', '')
        })
    
    return episodes


def process_podcast_episode(rss_url, episode_index=0):
    """
    Main function to download and transcribe a podcast episode.
    
    Args:
        rss_url: RSS feed URL for the podcast
        episode_index: Which episode to transcribe (0 = latest)
    """
    # Get episode information
    episodes = get_podcast_episodes(rss_url, limit=episode_index + 1)
    episode = episodes[episode_index]
    
    print(f"\n📻 Processing: {episode['title']}")
    print(f"   Published: {episode['published']}")
    
    if not episode['audio_url']:
        raise ValueError("No audio URL found for this episode")
    
    # Download audio to temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
        temp_audio_path = tmp_file.name
    
    try:
        # Download audio
        download_audio(episode['audio_url'], temp_audio_path)
        
        # Transcribe
        transcript = transcribe_audio(temp_audio_path)
        
        # Save transcript to context directory
        safe_title = "".join(c for c in episode['title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')[:50]  # Limit filename length
        output_file = CONTEXT_DIR / f"podcast_{safe_title}.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Podcast Episode: {episode['title']}\n")
            f.write(f"Published: {episode['published']}\n")
            f.write(f"Description: {episode['description']}\n")
            f.write(f"\n{'='*60}\n")
            f.write(f"TRANSCRIPT\n")
            f.write(f"{'='*60}\n\n")
            f.write(transcript)
        
        print(f"\n✅ Transcript saved to: {output_file}")
        print(f"   Transcript length: {len(transcript)} characters")
        
        return output_file, transcript
        
    finally:
        # Clean up temporary file
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)


if __name__ == "__main__":
    # Example usage:
    # Replace with actual RSS feed URL
    # You can find RSS feeds at: https://www.listennotes.com/ or podcast websites
    #https://rss.libsyn.com/shows/61840/destinations/240976.xml
    RSS_FEED_URL = "https://api.substack.com/feed/podcast/10845.rss"
    
    # For Spotify: You'll need to find the RSS feed first
    # Many podcasts list their RSS feed on their website
    # Or use: https://www.listennotes.com/api/docs/ to convert Spotify URLs
    
    print("🎙️  Podcast Transcriber")
    print("=" * 60)
    
    try:
        # Process the latest episode (index 0)
        output_file, transcript = process_podcast_episode(
            rss_url=RSS_FEED_URL,
            episode_index=0  # 0 = latest episode, 1 = second latest, etc.
        )
        
        print(f"\n🎉 Success! Your sales agent will now have access to this transcript.")
        print(f"   The file is in: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("- Make sure DEEPGRAM_API_KEY is set in your .env file")
        print("- Check that the RSS feed URL is correct")
        print("- Ensure you have internet connection")

