import os
from dotenv import load_dotenv
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from agents import download_song_tool, fetch_album_art_tool, check_video_status_tool

# Load environment variables from .env file
load_dotenv()

# Define the state
class KaraokeState(TypedDict):
    messages: Annotated[list, add_messages]
    song_query: str
    song_name: str
    artist_name: str  # NEW: Artist name for better search accuracy
    download_status: str
    pipeline_status: str
    pipeline_step: str  # Track which pipeline step is executing
    video_path: str
    current_step: str
    vocal_volume: float 


# Initialize the LLM
llm = ChatOpenAI(model="gpt-4o", temperature=0)


def extract_song_info(state: KaraokeState) -> KaraokeState:
    """Extract song information AND artist name from user query"""
    messages = state["messages"]
    last_message = messages[-1].content
    
    # Use LLM to extract both song name and artist
    prompt = f"""The user wants to create a karaoke video. Extract the song name AND artist name from their request.

User request: {last_message}

Respond ONLY with a JSON object in this format:
{{
  "song": "Shape of You",
  "artist": "Ed Sheeran"
}}

If artist is not mentioned, try to infer it from your knowledge. If you cannot determine the artist, use "Unknown".
Do not include any other text, only the JSON.
"""
    
    response = llm.invoke([HumanMessage(content=prompt)])
    
    # Parse the response
    import json
    try:
        content = response.content.strip()
        # Remove markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        
        info = json.loads(content)
        song_query = info.get("song", last_message)
        artist_name = info.get("artist", "Unknown")
    except:
        # Fallback if JSON parsing fails
        song_query = last_message
        artist_name = "Unknown"
    
    # song_name = song_query.lower().replace(" ", "").replace("-", "").replace("'", "")
    
    # Build display message
    if artist_name and artist_name != "Unknown":
        song_name = f"{song_query}_{artist_name}".lower().replace(" ", "").replace("-", "").replace("'", "")
        display_message = f"I'll create a karaoke video for: {song_query} by {artist_name}"
    else:
        song_name = song_query.lower().replace(" ", "").replace("-", "").replace("'", "")
        display_message = f"I'll create a karaoke video for: {song_query}"
    
    return {
        **state,
        "song_query": song_query,
        "song_name": song_name,
        "artist_name": artist_name,
        "current_step": "extracted",
        "messages": state["messages"] + [AIMessage(content=display_message)]
    }


def download_agent(state: KaraokeState) -> KaraokeState:
    """Agent responsible for downloading the song with artist name for accuracy"""
    song_query = state["song_query"]
    artist_name = state.get("artist_name", "Unknown")
    
    # Create LLM with tool binding
    llm_with_tools = llm.bind_tools([download_song_tool])
    
    prompt = f"Download the song: {song_query} by {artist_name}"
    response = llm_with_tools.invoke([HumanMessage(content=prompt)])
    
    # Execute the tool if requested
    if response.tool_calls:
        tool_call = response.tool_calls[0]
        # Add artist_name to the args
        args = tool_call["args"]
        args["artist_name"] = artist_name
        result = download_song_tool.invoke(args)
        download_status = result
    else:
        download_status = "No download performed"
    
    return {
        **state,
        "download_status": download_status,
        "current_step": "downloaded",
        "messages": state["messages"] + [AIMessage(content=f"Download Status: {download_status}")]
    }


def fetch_album_art(state: KaraokeState) -> KaraokeState:
    """Fetch and blur album art from YouTube thumbnail with artist name for accuracy"""
    song_query = state["song_query"]
    song_name = state["song_name"]
    artist_name = state.get("artist_name", "Unknown")
    
    try:
        print(f"[Album Art] Fetching album art for '{song_query}' by '{artist_name}'...")
        result = fetch_album_art_tool.invoke({
            "song_query": song_query,
            "song_name": song_name,
            "artist_name": artist_name
        })
        print(f"[Album Art] ✓ {result}")
        
        return {
            **state,
            "current_step": "album_art_fetched",
            "messages": state["messages"] + [AIMessage(content="✓ Album art fetched")]
        }
    except Exception as e:
        # Non-critical - continue with solid background
        print(f"[Album Art] Warning: {str(e)}")
        return {
            **state,
            "current_step": "album_art_fetched",
            "messages": state["messages"]
        }


def pipeline_vocal_separation(state: KaraokeState) -> KaraokeState:
    """Step 1: Separate vocals from instrumentals"""
    import sys
    sys.path.append('./utils/')
    from utils.utils import vocal_separation
    
    song_name = state["song_name"]
    try:
        print(f"[Pipeline] Separating vocals for '{song_name}'...")
        vocal_separation(song_name)
        print(f"[Pipeline] ✓ Vocal separation completed")
        
        return {
            **state,
            "current_step": "vocal_separated",
            "messages": state["messages"] + [AIMessage(content="✓ Separating vocals completed")]
        }
    except Exception as e:
        return {
            **state,
            "current_step": "error",
            "messages": state["messages"] + [AIMessage(content=f"✗ Error in vocal separation: {str(e)}")]
        }


def pipeline_transcription(state: KaraokeState) -> KaraokeState:
    """Step 2: Transcribe lyrics using Whisper"""
    import sys
    sys.path.append('./utils/')
    from utils.utils import whisper_transcription
    
    song_name = state["song_name"]
    try:
        print(f"[Pipeline] Transcribing lyrics for '{song_name}'...")
        whisper_transcription(song_name)
        print(f"[Pipeline] ✓ Transcription completed")
        
        return {
            **state,
            "current_step": "transcribed",
            "messages": state["messages"] + [AIMessage(content="✓ Transcribing lyrics completed")]
        }
    except Exception as e:
        return {
            **state,
            "current_step": "error",
            "messages": state["messages"] + [AIMessage(content=f"✗ Error in transcription: {str(e)}")]
        }


def pipeline_timestamp_correction(state: KaraokeState) -> KaraokeState:
    """Step 3: Adjust timestamps for accurate timing"""
    import sys
    sys.path.append('./utils/')
    from utils.utils import get_correct_timestamp
    
    song_name = state["song_name"]
    try:
        print(f"[Pipeline] Adjusting timestamps for '{song_name}'...")
        get_correct_timestamp(song_name)
        print(f"[Pipeline] ✓ Timestamp correction completed")
        
        return {
            **state,
            "current_step": "timestamps_adjusted",
            "messages": state["messages"] + [AIMessage(content="✓ Adjusting timestamps completed")]
        }
    except Exception as e:
        return {
            **state,
            "current_step": "error",
            "messages": state["messages"] + [AIMessage(content=f"✗ Error in timestamp correction: {str(e)}")]
        }


def validate_timestamps(state: KaraokeState) -> KaraokeState:
    """Validation step: Fix negative timestamps that can cause FFmpeg errors"""
    import json
    import os
    
    song_name = state["song_name"]
    try:
        json_path = os.path.join(os.getcwd(), 'processed_songs', song_name, 'lyrics', f'new_{song_name}_Vocals.json')
        
        # Read the JSON file
        with open(json_path, 'r') as f:
            json_data = json.load(f)
        
        # Fix negative start timestamp in first segment
        if json_data['segments'][0]['start'] < 0:
            print(f"[Validation] Fixing negative timestamp: {json_data['segments'][0]['start']} -> 0.0")
            json_data['segments'][0]['start'] = 0.0
        
        # Save the corrected JSON
        with open(json_path, 'w') as f:
            json.dump(json_data, f)
        
        return {
            **state,
            "current_step": "timestamps_validated",
            "messages": state["messages"] + [AIMessage(content="✓ Timestamps validated")]
        }
    except Exception as e:
        # If validation fails, just continue (non-critical)
        print(f"[Validation] Warning: {str(e)}")
        return {
            **state,
            "current_step": "timestamps_validated",
            "messages": state["messages"]
        }


def pipeline_image_generation(state: KaraokeState) -> KaraokeState:
    """Step 4: Create lyric images"""
    import sys
    sys.path.append('./utils/')
    from utils.text_to_images import text_to_images
    
    song_name = state["song_name"]
    try:
        print(f"[Pipeline] Creating lyric images for '{song_name}'...")
        text_to_images(song_name)
        print(f"[Pipeline] ✓ Image generation completed")
        
        return {
            **state,
            "current_step": "images_created",
            "messages": state["messages"] + [AIMessage(content="✓ Creating lyric images completed")]
        }
    except Exception as e:
        return {
            **state,
            "current_step": "error",
            "messages": state["messages"] + [AIMessage(content=f"✗ Error in image generation: {str(e)}")]
        }


def pipeline_audio_merging(state: KaraokeState) -> KaraokeState:
    """Step 5: Merge audio tracks"""
    import sys
    sys.path.append('./utils/')
    from utils.utils import merge_audio
    
    song_name = state["song_name"]
    vocal_volume = state.get("vocal_volume", 0.0)
    try:
        print(f"[Pipeline] Merging audio for '{song_name}'...")
        merge_audio(song_name=song_name, volume_factor=vocal_volume)
        print(f"[Pipeline] ✓ Audio merging completed")
        
        return {
            **state,
            "current_step": "audio_merged",
            "messages": state["messages"] + [AIMessage(content="✓ Merging audio completed")]
        }
    except Exception as e:
        return {
            **state,
            "current_step": "error",
            "messages": state["messages"] + [AIMessage(content=f"✗ Error in audio merging: {str(e)}")]
        }


def pipeline_video_creation(state: KaraokeState) -> KaraokeState:
    """Step 6: Generate final video"""
    import sys
    sys.path.append('./utils/')
    from utils.image_to_video import image_to_video
    
    song_name = state["song_name"]
    try:
        print(f"[Pipeline] Generating final video for '{song_name}'...")
        image_to_video(song_name)
        print(f"[Pipeline] ✓ Video creation completed")
        
        import os
        video_path = os.path.join(os.getcwd(), 'processed_songs', song_name, f'{song_name}_karaoke.mp4')
        
        return {
            **state,
            "current_step": "video_created",
            "pipeline_status": f"Video created at: {video_path}",
            "messages": state["messages"] + [AIMessage(content="✓ Generating final video completed")]
        }
    except Exception as e:
        return {
            **state,
            "current_step": "error",
            "messages": state["messages"] + [AIMessage(content=f"✗ Error in video creation: {str(e)}")]
        }


def finalize_agent(state: KaraokeState) -> KaraokeState:
    """Agent that checks and finalizes the video"""
    song_name = state["song_name"]
    
    # Create LLM with tool binding
    llm_with_tools = llm.bind_tools([check_video_status_tool])
    
    prompt = f"Check if the karaoke video exists for: {song_name}"
    response = llm_with_tools.invoke([HumanMessage(content=prompt)])
    
    # Execute the tool if requested
    video_status = "Unknown"
    if response.tool_calls:
        tool_call = response.tool_calls[0]
        result = check_video_status_tool.invoke(tool_call["args"])
        video_status = result
        
        # Extract video path if it exists
        if "Video exists at:" in result:
            video_path = result.split("Video exists at:")[1].strip()
        else:
            video_path = ""
    else:
        video_path = ""
    
    return {
        **state,
        "video_path": video_path,
        "current_step": "completed",
        "messages": state["messages"] + [AIMessage(content=f"✅ Karaoke video ready! {video_status}")]
    }


# Build the graph
def create_karaoke_graph():
    """Create the LangGraph workflow for karaoke generation"""
    workflow = StateGraph(KaraokeState)
    
    # Add nodes
    workflow.add_node("extract", extract_song_info)
    workflow.add_node("download", download_agent)
    workflow.add_node("fetch_album_art", fetch_album_art)
    workflow.add_node("vocal_separation", pipeline_vocal_separation)
    workflow.add_node("transcription", pipeline_transcription)
    workflow.add_node("timestamp_correction", pipeline_timestamp_correction)
    workflow.add_node("validate_timestamps", validate_timestamps)
    workflow.add_node("image_generation", pipeline_image_generation)
    workflow.add_node("audio_merging", pipeline_audio_merging)
    workflow.add_node("video_creation", pipeline_video_creation)
    workflow.add_node("finalize", finalize_agent)
    
    # Define the flow
    workflow.set_entry_point("extract")
    workflow.add_edge("extract", "download")
    workflow.add_edge("download", "fetch_album_art")
    workflow.add_edge("fetch_album_art", "vocal_separation")
    workflow.add_edge("vocal_separation", "transcription")
    workflow.add_edge("transcription", "timestamp_correction")
    workflow.add_edge("timestamp_correction", "validate_timestamps")
    workflow.add_edge("validate_timestamps", "image_generation")
    workflow.add_edge("image_generation", "audio_merging")
    workflow.add_edge("audio_merging", "video_creation")
    workflow.add_edge("video_creation", "finalize")
    workflow.add_edge("finalize", END)
    
    return workflow.compile()


# Create the compiled graph
karaoke_graph = create_karaoke_graph()