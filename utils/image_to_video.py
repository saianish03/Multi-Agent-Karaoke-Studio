import os
import shutil
import subprocess

def move_video(song_name):
    curr_path = os.getcwd()
    dest_path = os.path.join(curr_path, "processed_songs", f"{song_name}")
    files = os.listdir(curr_path)
    for file in files:
        if file.endswith('.mp4'):
            source_file = os.path.join(curr_path, file)
            dest_file = os.path.join(dest_path, file)
            shutil.move(source_file, dest_file)

def image_to_video(song_name):
    curr_path = os.getcwd()
    text_file = os.path.join(curr_path, 'processed_songs', f'{song_name}', 'images_duration.txt')
    audio_file = os.path.join(curr_path, 'processed_songs', f'{song_name}',f'{song_name}_Merged.wav')
    command = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", f"{text_file}", "-i", f"{audio_file}", "-c:v", "libx264","-r", "30", "-pix_fmt", "yuv420p", f"{song_name}_karaoke.mp4"]
    try:
        subprocess.run(command, shell=False)
        print("Video Generated Successfully")
    except subprocess.CalledProcessError as e:
        print("Error while generating the video: ", e)
    
    move_video(song_name)