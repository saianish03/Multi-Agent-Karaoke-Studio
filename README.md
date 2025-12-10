# Multi-Agent Karaoke Video Generator

A production-ready karaoke video generation system built with LangGraph and orchestrated through intelligent agents. The system automatically downloads songs, extracts vocals, transcribes lyrics, generates synchronized lyric overlays with album art backgrounds, and compiles everything into professional karaoke videos.

## System Architecture

The application implements a multi-agent workflow using LangGraph v1, where specialized agents handle distinct phases of the video generation pipeline. Each agent operates independently while maintaining state continuity through a centralized state graph.

### Agent Workflow

```
User Input → Song Extraction → Download → Album Art → Vocal Separation → 
Transcription → Timestamp Validation → Image Generation → Audio Merge → 
Video Compilation → Output
```

### Core Agents

1. **Extraction Agent**: Parses user queries using GPT-4 to identify song titles and artist names with high accuracy
2. **Download Agent**: Retrieves audio files from YouTube using yt-dlp with artist-specific search queries
3. **Album Art Agent**: Fetches and processes video thumbnails, applying Gaussian blur for aesthetic backgrounds
4. **Pipeline Agents**: Execute vocal separation, transcription, and synchronization tasks sequentially
5. **Finalization Agent**: Validates output and provides video delivery

## Technical Stack

**Framework & Orchestration**
- LangGraph for agent workflow management
- LangChain for LLM integration and tool binding
- Streamlit for real-time UI with progress tracking

**Machine Learning & Audio Processing**
- OpenAI Whisper (medium model) for speech-to-text transcription
- [Open source Vocal Remover](https://github.com/tsurumeso/vocal-remover) for source separation
- librosa for audio analysis and timestamp correction
- soundfile for audio I/O operations

**Media Processing**
- FFmpeg for video compilation with concat demuxer
- PIL/Pillow for image processing and composition
- yt-dlp for YouTube content retrieval

**Language Models**
- OpenAI GPT-4o for natural language understanding, chat and extraction

## Key Features

### Intelligent Song Resolution
The system extracts both song titles and artist names from natural language queries, using the artist information to disambiguate songs with identical titles. GPT-4 infers artist names when not explicitly provided, leveraging its training data for music metadata.

### Adaptive Background Generation
Album art is automatically retrieved from YouTube thumbnails and processed with Gaussian blur (radius=15) to create visually appealing backgrounds. A semi-transparent overlay (47% opacity) ensures optimal text contrast across varying image compositions.

### Precision Timestamp Synchronization
The system analyzes audio waveforms to detect vocal onset, adjusting Whisper's initial timestamp predictions using amplitude-to-decibel conversion and threshold detection. This ensures text appears one second before vocals begin.

### Configurable Vocal Mix
Users can adjust vocal volume from 0.0 (pure instrumental) to 1.0 (full vocals) through a real-time slider, with the merge operation performed using numpy array manipulation for precise amplitude control.

## Installation

### Prerequisites
- Python 3.9 or higher
- FFmpeg installed and available in system PATH
- CUDA-compatible GPU (optional, for faster vocal separation)

### Dependency Installation

```bash
# Clone the repository
git clone <repository-url>
cd karaoke-app

# Install Python dependencies
pip install -r requirements.txt

# Install system dependencies (macOS)
brew install ffmpeg yt-dlp

# Install system dependencies (Ubuntu/Debian)
sudo apt-get install ffmpeg
pip install yt-dlp
```

### Environment Configuration

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

The system requires valid OpenAI API credentials for GPT-4 access. Whisper runs locally and does not require API authentication.

## Usage

### Starting the Application

```bash
streamlit run app.py
```

The interface will be accessible at `http://localhost:8501`

### Command Syntax

The system accepts natural language input with flexible phrasing:

```
"Create karaoke for Shape of You by Ed Sheeran"
"Make a karaoke video for Bohemian Rhapsody"
"I want Yesterday by The Beatles"
```

### Vocal Volume Configuration

Use the sidebar slider to adjust vocal presence:
- 0.0: Pure instrumental (no vocals)
- 0.5: Balanced mix (50% vocal amplitude)
- 1.0: Full vocals (100% vocal amplitude)

## Project Structure

```
karaoke-app/
├── app.py                      # Streamlit interface with real-time progress
├── graph.py                    # LangGraph workflow definition
├── agents.py                   # Tool definitions for agent actions
├── utils/
│   ├── utils.py               # Audio processing utilities
│   ├── text_to_images.py     # Image generation with album art
│   ├── image_to_video.py     # FFmpeg video compilation
│   ├── vocal-remover/        # Source separation model
│   └── fonts/                # Typography assets
├── songs/                     # Downloaded MP3 files
└── processed_songs/           # Generated outputs
    └── [song_name]/
        ├── album_art_blurred.jpg
        ├── [song_name]_Vocals.wav
        ├── [song_name]_Instruments.wav
        ├── [song_name]_Merged.wav
        ├── [song_name]_karaoke.mp4
        ├── images_duration.txt
        └── lyrics/
            ├── new_[song_name]_Vocals.json
            └── lyric_images/
```

## Pipeline Details

### Vocal Separation
Utilizes a pre-trained U-Net architecture to decompose stereo audio into vocal and instrumental stems. The model processes spectrograms through encoder-decoder layers with skip connections for high-quality separation.

### Transcription
Whisper's medium model (769M parameters) provides robust speech recognition with timestamp precision. The model outputs segments with start/end times, text content, and confidence scores in JSON format.

### Timestamp Correction
Analyzes the first audio chunk using librosa's amplitude-to-decibel conversion. Identifies vocal onset by detecting when normalized decibel values exceed a 65dB threshold, then adjusts the initial timestamp by -1 second for preemptive text display.

### Image Composition
Each lyric segment generates a 1280x720 PNG with:
- Blurred album art background (GaussianBlur radius=15)
- Semi-transparent dark overlay (RGBA: 0,0,0,120)
- White text with 3-pixel black outline for contrast
- Dancing Script font at 75pt for aesthetic appeal

### Video Assembly
FFmpeg's concat demuxer reads the `images_duration.txt` file, which maps each image to its precise display duration. The H.264 codec (libx264) encodes at 30fps with yuv420p pixel format for broad compatibility.

## Performance Characteristics

**Processing Time** (approximate, for 3-minute song):
- Song download: 30 seconds
- Album art fetch: 2 seconds
- Vocal separation: 45 seconds
- Transcription (medium model): 60 seconds
- Timestamp correction: 5 seconds
- Image generation: 10 seconds
- Audio merge: 5 seconds
- Video compilation: 20 seconds
- **Total**: ~3 minutes

**Resource Requirements**:
- RAM: 4GB minimum (8GB recommended)
- Disk: 200MB per song (including intermediates)
- GPU: Optional (reduces vocal separation time by 50%)

## Troubleshooting

### Issue: "OPENAI_API_KEY not found"
Ensure the `.env` file exists in the project root and contains valid credentials.

### Issue: "FFmpeg not found"
Verify FFmpeg installation: `ffmpeg -version`
Add FFmpeg to system PATH if installed but not recognized.

### Issue: "Negative timestamp validation failed"
This occurs when vocals start within the first second. The system automatically corrects this to 0.0, but some songs may require manual JSON adjustment.

### Issue: "Album art fetch timeout"
Network latency or YouTube API rate limits may cause failures. The system gracefully falls back to solid color backgrounds.

### Issue: "Whisper model not found"
On first run, Whisper automatically downloads the medium model (~1.5GB). Ensure stable internet connection during initial setup.

## Configuration

### Adjusting Blur Intensity
In `agents.py`, modify the `ImageFilter.GaussianBlur` radius parameter:

```python
img_blurred = img.filter(ImageFilter.GaussianBlur(radius=15))  # Default: 15
```

### Changing Font Style
Replace the font file in `utils/fonts/` and update the path in `text_to_images.py`:

```python
font_path = os.path.join(curr_dir, r'utils/fonts/YourFont/YourFont.ttf')
```

### Adjusting Video Resolution
Modify dimensions in `text_to_images.py` and `image_to_video.py` consistently:

```python
width = 1920  # Default: 1280
height = 1080  # Default: 720
```

## Dependencies

**Core Libraries**:
- streamlit>=1.32.0
- langchain>=0.1.0
- langchain-openai>=0.1.0
- langgraph>=0.1.0
- python-dotenv>=1.0.0

**Audio Processing**:
- openai-whisper>=20231117
- librosa>=0.10.1
- soundfile>=0.12.1
- numpy>=1.24.0

**Media Handling**:
- yt-dlp>=2024.3.10
- pillow>=10.0.0
- requests>=2.31.0
- ffmpeg-python>=0.2.0

## Limitations

1. **Language Support**: Whisper transcription optimized for English. Other languages may exhibit reduced accuracy.
2. **Song Length**: Processing time scales linearly. Songs exceeding 5 minutes may require 5+ minutes to process.
3. **Network Dependency**: Requires internet connectivity for YouTube access and OpenAI API calls.
4. **Copyright**: Users are responsible for ensuring proper licensing for downloaded content.

## Future Enhancements

- Multi-language transcription support with language detection
- Real-time preview of generated segments
- Batch processing for multiple songs
- Custom background image upload option
- Advanced typography controls (font size, color, positioning)
- Export format options (MP4, WebM, AVI)

## License

MIT License - See LICENSE file for details.
