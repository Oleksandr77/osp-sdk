import logging
from youtube_transcript_api import YouTubeTranscriptApi
from typing import Dict, Any, Optional
import urllib.parse

logger = logging.getLogger(__name__)

def get_video_id(url: str) -> Optional[str]:
    """Extracts video ID from a YouTube URL."""
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname in ('youtu.be', 'www.youtu.be'):
        return parsed.path[1:]
    if parsed.hostname in ('youtube.com', 'www.youtube.com'):
        if parsed.path == '/watch':
            p = urllib.parse.parse_qs(parsed.query)
            return p.get('v', [None])[0]
    return None

def get_transcript(video_id: str) -> str:
    """Fetches the transcript for a given video ID."""
    try:
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id)
        # Combine text from snippets
        full_text = " ".join([snippet.text for snippet in transcript])
        return full_text
    except Exception as e:
        logger.error(f"Failed to get transcript for {video_id}: {e}")
        return f"Error reading transcript: {str(e)}"

def execute(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for the skill.
    Expected arguments: 'url' or 'video_id'.
    """
    video_id = arguments.get("video_id")
    url = arguments.get("url")

    if not video_id and url:
        video_id = get_video_id(url)
    
    if not video_id:
        return {"error": "Missing video_id or valid execution URL."}

    logger.info(f"Executing YouTube Analysis for Video ID: {video_id}")
    
    transcript = get_transcript(video_id)
    
    # In a full agentic loop, we might summarize here using an LLM.
    # For now, we return the transcript length and a preview.
    
    return {
        "video_id": video_id,
        "transcript_preview": transcript[:500] + "..." if len(transcript) > 500 else transcript,
        "transcript_length": len(transcript),
        "full_transcript_available": True
    }
