import os
import sys
import subprocess
from typing import Annotated
from langchain_core.tools import tool
sys.path.append('./utils/')
from utils.utils import vocal_separation, whisper_transcription, get_correct_timestamp, merge_audio
from utils.text_to_images import text_to_images 
from utils.image_to_video import image_to_video


@tool
def download_song_tool(song_query: str, artist_name: str = "") -> str:
    """
    Downloads a song from YouTube based on the search query with artist name.
    Returns the song name (sanitized, lowercase, no spaces) if successful.
    """
    try:
        # Sanitize song name
        if artist_name and artist_name.lower() != "unknown":
            song_name = f"{song_query}_{artist_name}".lower().replace(" ", "").replace("-", "").replace("'", "")
        else:
            song_name = song_query.lower().replace(" ", "").replace("-", "").replace("'", "")
        
        # Create songs directory if it doesn't exist
        songs_dir = os.path.join(os.getcwd(), 'songs')
        if not os.path.exists(songs_dir):
            os.makedirs(songs_dir)
        
        output_path = os.path.join(songs_dir, f"{song_name}.mp3")
        
        # Check if song already exists
        if os.path.exists(output_path):
            return f"Song '{song_name}' already exists. Using existing file."
        
        # Build search query with artist name for better accuracy
        if artist_name and artist_name.lower() != "unknown":
            search_query = f"{song_query} {artist_name}"
        else:
            search_query = song_query
        
        print(f"[Download] Searching YouTube for: {search_query}")
        
        # Download using yt-dlp
        cmd = [
            "yt-dlp",
            "-x",  # Extract audio
            "--audio-format", "mp3",
            "--audio-quality", "0",  # Best quality
            f"ytsearch1:{search_query}",  # Search YouTube with artist
            "-o", output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
        
        if result.returncode == 0:
            return f"Successfully downloaded '{song_name}'"
        else:
            return f"Failed to download song. Error: {result.stderr}"
            
    except Exception as e:
        return f"Error downloading song: {str(e)}"


@tool
def fetch_album_art_tool(song_query: str, song_name: str, artist_name: str = "") -> str:
    """
    Fetches the album art/thumbnail for the song from YouTube and applies blur.
    Uses artist name for more accurate search results.
    Saves it as album_art_blurred.jpg in the processed_songs folder.
    """
    try:
        import yt_dlp
        from PIL import Image, ImageFilter
        import requests
        from io import BytesIO
        
        # Build search query with artist name for better accuracy
        if artist_name and artist_name.lower() != "unknown":
            search_query = f"{song_query} {artist_name}"
        else:
            search_query = song_query
        
        print(f"[Album Art] Fetching thumbnail for: {search_query}")
        
        # Extract thumbnail URL using yt-dlp
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        # Search for the video to get thumbnail
        youtube_search = f"ytsearch1:{search_query}"
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_search, download=False)
            if 'entries' in info:
                video_info = info['entries'][0]
            else:
                video_info = info
            
            thumbnail_url = video_info.get('thumbnail')
            
            if not thumbnail_url:
                return "No thumbnail found for this song"
        
        # Download the thumbnail
        response = requests.get(thumbnail_url, timeout=10)
        img = Image.open(BytesIO(response.content))
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize to 1280x720
        if img.size != (1280, 720):
            img = img.resize((1280, 720), Image.Resampling.LANCZOS)
        
        # Apply Gaussian blur
        img_blurred = img.filter(ImageFilter.GaussianBlur(radius=15))
        
        # Save blurred album art
        dest_dir = os.path.join(os.getcwd(), 'processed_songs', song_name)
        os.makedirs(dest_dir, exist_ok=True)
        album_art_path = os.path.join(dest_dir, 'album_art_blurred.jpg')
        img_blurred.save(album_art_path, quality=95)
        
        return f"Successfully fetched and blurred album art"
        
    except Exception as e:
        return f"Error fetching album art: {str(e)}"


@tool
def execute_karaoke_pipeline_tool(song_name: str, progress_callback=None) -> str:
    """
    Executes the complete karaoke video generation pipeline for a given song.
    This includes vocal separation, transcription, image generation, and video creation.
    """
    try:
        steps = [
            ("Separating vocals", vocal_separation),
            ("Transcribing lyrics", whisper_transcription),
            ("Adjusting timestamps", get_correct_timestamp),
            ("Creating lyric images", text_to_images),
            ("Merging audio", merge_audio),
            ("Generating video", image_to_video)
        ]
        
        for i, (step_name, step_func) in enumerate(steps, 1):
            print(f"[Pipeline] Step {i}/6: {step_name} for '{song_name}'...")
            step_func(song_name)
            print(f"[Pipeline] ✓ {step_name} completed")
        
        # Verify video was created
        video_path = os.path.join(os.getcwd(), 'processed_songs', song_name, f'{song_name}_karaoke.mp4')
        if os.path.exists(video_path):
            return f"Successfully created karaoke video at: {video_path}"
        else:
            return "Pipeline completed but video file not found."
            
    except Exception as e:
        return f"Error in pipeline execution: {str(e)}"


@tool
def check_video_status_tool(song_name: str) -> str:
    """
    Checks if the karaoke video exists for the given song.
    Returns the path if it exists, otherwise returns status message.
    """
    try:
        video_path = os.path.join(os.getcwd(), 'processed_songs', song_name, f'{song_name}_karaoke.mp4')
        if os.path.exists(video_path):
            return f"Video exists at: {video_path}"
        else:
            return "Video does not exist yet."
    except Exception as e:
        return f"Error checking video status: {str(e)}"