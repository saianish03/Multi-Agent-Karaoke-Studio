import streamlit as st
import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from graph import karaoke_graph

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="Karaoke Video Generator",
    page_icon="🎤",
    layout="wide"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "video_path" not in st.session_state:
    st.session_state.video_path = None
if "processing" not in st.session_state:
    st.session_state.processing = False

# Title and description
st.title("🎤 Karaoke Video Generator")
st.markdown("Create karaoke videos with **blurred album art backgrounds**!")

# Sidebar with info
with st.sidebar:
    st.header("ℹ️ How it works")
    st.markdown("""
    1. **Enter a song request** (e.g., "Create karaoke for Shape of You")
    2. **Download Agent** finds and downloads the song
    3. **Album Art Agent** fetches and blurs the thumbnail
    4. **Pipeline Agent** processes the audio and creates lyric images
    5. **Video is generated** and ready to play!
    
    ---
    
    ### Pipeline Steps:
    - 🎵 Vocal separation
    - 📝 Lyrics transcription
    - 🖼️ Album art background
    - 🎬 Video compilation
    """)

    # Add this after the Pipeline Steps markdown and before the Clear Chat button
    st.markdown("---")
    st.header("⚙️ Settings")
    vocal_volume = st.slider(
        "Vocal Volume",
        min_value=0.0,
        max_value=1.0,
        value=0.0,
        step=0.1,
        help="0 = No vocals (pure instrumental), 1 = Full vocals"
    )
    st.session_state.vocal_volume = vocal_volume
    
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.video_path = None
        st.rerun()
    # Footer
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: gray; font-size: 16px;'>Made by Anish and Anup</div>", unsafe_allow_html=True)


# Chat interface
chat_container = st.container()

with chat_container:
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Enter a song name (e.g., 'Shape of You' or 'Bohemian Rhapsody')"):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Process the request
    with st.chat_message("assistant"):
        status_placeholder = st.empty()
        progress_bar = st.progress(0)
        steps_placeholder = st.empty()
        
        # Track completed steps for display
        completed_steps = []
        
        try:
            # Initialize the state
            initial_state = {
                "messages": [HumanMessage(content=prompt)],
                "song_query": "",
                "song_name": "",
                "artist_name": "",
                "download_status": "",
                "pipeline_status": "",
                "pipeline_step": "",
                "video_path": "",
                "current_step": "starting",
                "vocal_volume": st.session_state.vocal_volume
            }
            
            # Run the graph with streaming
            final_state = None
            
            status_placeholder.markdown("🔄 Starting karaoke generation...")
            
            for event in karaoke_graph.stream(initial_state):
                # Update status based on current step
                for node_name, node_state in event.items():
                    current_step = node_state.get("current_step", "")
                    
                    # Map steps to progress (11 steps now)
                    step_mapping = {
                        "extracted": (1, "🎵 Song identified", node_state.get('song_query', '')),
                        "downloaded": (2, "📥 Song downloaded", ""),
                        "album_art_fetched": (3, "🖼️ Album art fetched", ""),
                        "vocal_separated": (4, "🎤 Vocals separated", ""),
                        "transcribed": (5, "📝 Lyrics transcribed", ""),
                        "timestamps_adjusted": (6, "⏱️ Timestamps adjusted", ""),
                        "timestamps_validated": (7, "✅ Timestamps validated", ""),
                        "images_created": (8, "🖼️ Images created", ""),
                        "audio_merged": (9, "🔊 Audio merged", ""),
                        "video_created": (10, "🎬 Video generated", ""),
                        "completed": (11, "✅ Video ready!", "")
                    }
                    
                    if current_step in step_mapping:
                        step_num, display_text, extra = step_mapping[current_step]
                        progress = step_num / 11
                        progress_bar.progress(progress)
                        
                        # Format status message
                        if current_step == "extracted" and extra:
                            artist = node_state.get('artist_name', '')
                            if artist and artist != "Unknown":
                                status_msg = f"✅ Identified song: **{extra}** by **{artist}**"
                                display_text = f"🎵 Song identified: {extra} by {artist}"
                            else:
                                status_msg = f"✅ Identified song: **{extra}**"
                                display_text = f"🎵 Song identified: {extra}"
                        else:
                            status_msg = f"✅ {display_text.split(' ', 1)[1]}"  # Remove emoji for status
                        
                        status_placeholder.markdown(status_msg)
                        
                        # Add to completed steps if not already there
                        if display_text not in completed_steps:
                            completed_steps.append(display_text)
                            
                            # Update steps display (using st.empty() to replace content)
                            steps_text = "**Progress:**\n\n" + "\n".join([f"- {step}" for step in completed_steps])
                            steps_placeholder.markdown(steps_text)
                        
                        # Save final state
                        if current_step == "completed":
                            final_state = node_state
            
            progress_bar.progress(1.0)
            
            # Extract final messages and video path
            if final_state:
                # Add assistant messages to chat
                for msg in final_state["messages"][1:]:  # Skip the initial user message
                    if msg.content not in [m["content"] for m in st.session_state.messages]:
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": msg.content
                        })
                
                # Store video path
                if final_state.get("video_path"):
                    st.session_state.video_path = final_state["video_path"]
            
            st.success("🎉 Karaoke video generation complete!")
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Sorry, I encountered an error: {str(e)}"
            })
    
    st.rerun()

# Display video if available
if st.session_state.video_path and os.path.exists(st.session_state.video_path):
    st.markdown("---")
    st.subheader("🎬 Your Karaoke Video")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Display the video
        video_file = open(st.session_state.video_path, 'rb')
        video_bytes = video_file.read()
        st.video(video_bytes)
    
    with col2:
        st.markdown("### Video Details")
        st.markdown(f"**Path:** `{st.session_state.video_path}`")
        
        # Check if album art was used
        song_name = os.path.basename(os.path.dirname(st.session_state.video_path))
        album_art_path = os.path.join(os.path.dirname(st.session_state.video_path), 'album_art_blurred.jpg')
        
        if os.path.exists(album_art_path):
            st.markdown("**Background:** Blurred Album Art ✨")
        else:
            st.markdown("**Background:** Solid Color")
        
        # Add download button
        with open(st.session_state.video_path, 'rb') as f:
            st.download_button(
                label="📥 Download Video",
                data=f,
                file_name=os.path.basename(st.session_state.video_path),
                mime="video/mp4",
                use_container_width=True
            )