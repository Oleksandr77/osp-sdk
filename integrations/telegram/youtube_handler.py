import yt_dlp
import os
import glob
import logging

logger = logging.getLogger(__name__)

DOWNLOAD_DIR = "../../../10_Business_Admin/Telegram_Export/YouTube_Analysis"

class YouTubeHandler:
    def __init__(self):
        if not os.path.exists(DOWNLOAD_DIR):
            os.makedirs(DOWNLOAD_DIR)

    async def download_audio(self, url):
        """Downloads audio from YouTube video."""
        logger.info(f"Downloading Audio for: {url}")
        
        # Output template: downloads/Title [id].mp3
        out_tmpl = f'{DOWNLOAD_DIR}/%(title)s [%(id)s].%(ext)s'
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_tmpl,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'noplaylist': True
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                # FFmpeg changes ext to mp3
                final_filename = filename.rsplit('.', 1)[0] + ".mp3"
                
                logger.info(f"Audio downloaded: {final_filename}")
                return final_filename
                
        except Exception as e:
            logger.error(f"Audio Download Error: {e}")
            return None

    async def analyze_video(self, url):
        """Downloads audio/subs and returns a summary (or text for now)."""
        logger.info(f"Processing YouTube URL: {url}")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'writeissuett': True,
            'writesubtitles': True,
            'subtitleslangs': ['uk', 'ru', 'en'],  # Prioritize UA/RU/EN
            'skip_download': True, # For now, just get metadata and subs
            'quiet': True
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False) # Get metadata first
                title = info.get('title', 'Unknown Video')
                duration = info.get('duration', 0)
                description = info.get('description', '')
                
                # Check for subtitles
                subtitles = info.get('subtitles', {})
                has_subs = any(lang in subtitles for lang in ['uk', 'ru', 'en'])
                
                logger.info(f"Video Found: {title} ({duration}s). Subs: {has_subs}")
                
                # If we were to download fully:
                # ydl.download([url])
                
                return {
                    "title": title,
                    "description": description[:500] + "...", # Truncate
                    "duration": f"{duration // 60}m {duration % 60}s",
                    "has_subs": has_subs,
                    "url": url
                }

        except Exception as e:
            logger.error(f"YouTube Error: {e}")
            return {"error": str(e)}

    async def search_videos(self, query, limit=10, period=None, sort_by="relevance"):
        """
        Searches YouTube OR parses a direct URL.
        """
        is_url = query.strip().startswith(("http://", "https://", "www.youtube.com", "youtu.be"))
        
        ydl_opts = {
            'quiet': True,
            'extract_flat': True, # Faster, but might need full info for direct URL
            'noplaylist': True,
        }

        if is_url:
            logger.info(f"Direct URL detected: {query}")
            # For direct URL, we might want full info to get duration/title accurately without 'extract_flat' sometimes
            # But let's try with consistent opts first, or adjust if needed.
            ydl_opts['extract_flat'] = False 
        else:
             logger.info(f"Searching YouTube: '{query}'")

        try:
            results = []
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if is_url:
                    # Direct Link Analysis
                    info = ydl.extract_info(query, download=False)
                    # Support playlists if user pasted one, or single video
                    if 'entries' in info:
                         entries = info['entries']
                    else:
                         entries = [info]
                else:
                    # Search Mode
                    search_query = query
                    if period == "today": search_query += " today"
                    elif period == "week": search_query += " this week"
                    elif period == "month": search_query += " this month"
                    
                    raw_query = f"ytsearch{limit*2}:{search_query}"
                    info = ydl.extract_info(raw_query, download=False)
                    entries = info.get('entries', [])

                for entry in entries:
                    if not entry: continue
                    
                    # Handle different yt-dlp structures
                    t = entry.get('title')
                    if not t: continue
                    
                    dur = entry.get('duration') or 0
                    
                    results.append({
                        "title": t,
                        "url": entry.get('webpage_url') or entry.get('url') or query,
                        "duration": dur,
                        "duration_str": f"{int(dur//60)}:{int(dur%60):02d}" if dur else "N/A",
                        "view_count": entry.get('view_count', 0),
                        "uploader": entry.get('uploader', 'Unknown'),
                        "upload_date": entry.get('upload_date', '00000000')
                    })

            # Sort only if it was a search (preserving URL order usually better/irrelevant for single)
            if not is_url:
                if sort_by == "date":
                    results.sort(key=lambda x: x['upload_date'] or "", reverse=True)
                elif sort_by == "views":
                    results.sort(key=lambda x: x['view_count'] or 0, reverse=True)

            return results[:limit]
                
        except Exception as e:
            logger.error(f"Search/URL Error: {e}")
            return []
