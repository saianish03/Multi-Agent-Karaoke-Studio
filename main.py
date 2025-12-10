import sys
import os
import shutil
sys.path.append('./utils/')
from utils.utils import vocal_separation, whisper_transcription, get_correct_timestamp, merge_audio
from utils.text_to_images import text_to_images 
from utils.image_to_video import image_to_video

if __name__ == "__main__":
    # vocal separation:
    # song_name = input("Enter song name without spaces and in lower case: ")
    song_name = 'shapeofyou'
    vocal_separation(song_name) # done

    whisper_transcription(song_name) # done

    get_correct_timestamp(song_name) # done

    text_to_images(song_name) # done

    merge_audio(song_name) # done
    
    image_to_video(song_name) # done