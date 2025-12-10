import subprocess
import os
import shutil
import sys
import librosa
import numpy as np
import math
import json
import soundfile as sf

def merge_audio(song_name, volume_factor=0):
    curr_dir = os.getcwd()
    dest_dir = os.path.join(curr_dir, 'processed_songs', f'{song_name}', f'{song_name}_Merged.wav')
    
    # Load as stereo (mono=False) to preserve channel info
    vocals, sr_vocals = librosa.load(f'./processed_songs/{song_name}/{song_name}_Vocals.wav', mono=False)
    instrumentals, sr_inst = librosa.load(f'./processed_songs/{song_name}/{song_name}_Instruments.wav', mono=False)
    
    # If either is mono (shape is 1D), reshape to (1, samples)
    if vocals.ndim == 1:
        vocals = vocals.reshape(1, -1)
    if instrumentals.ndim == 1:
        instrumentals = instrumentals.reshape(1, -1)
    
    # Ensure same number of samples
    min_samples = min(vocals.shape[1], instrumentals.shape[1])
    vocals = vocals[:, :min_samples]
    instrumentals = instrumentals[:, :min_samples]
    
    # Adjust volume and mix
    vocals_adjusted = vocals * volume_factor
    merged_audio = vocals_adjusted + instrumentals
    
    # Save as stereo
    sf.write(dest_dir, merged_audio.T, sr_vocals)  # .T transposes to (samples, channels)

def move_vocals(song_name):
    source_dir = os.getcwd()
    dest_dir = os.path.join(source_dir, 'processed_songs', f'{song_name}')
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    files = os.listdir(source_dir)
    for file in files:
        if (file.endswith('.wav') or file.endswith('.mp3')) and song_name in file.lower():
            source_file = os.path.join(source_dir, file)
            dest_file = os.path.join(dest_dir, file)
            shutil.move(source_file, dest_file)

def move_transcriptions(song_name):
    curr_path = os.getcwd()
    lyrics_path = os.path.join(curr_path, 'processed_songs', f'{song_name}', 'lyrics')
    if not os.path.exists(lyrics_path):
        os.makedirs(lyrics_path)
    files = os.listdir(curr_path)
    for file in files:
        if file.split('.')[-1] in ['json', 'srt', 'tsv', 'txt', 'vtt'] and song_name in file.lower():
            source_file = os.path.join(curr_path, file)
            dest_file = os.path.join(lyrics_path, file)
            shutil.move(source_file, dest_file)

def vocal_separation(song_name):
    curr_path = str(os.getcwd())
    file_path = os.path.join(curr_path,r"utils/vocal-remover")
    v_s_cmd = ["python", os.path.join(file_path,"inference.py"), "--input", f"songs/{song_name}.mp3"]
    try:
        subprocess.run(v_s_cmd, shell=False)
        print("Vocal separated successfully")
    except subprocess.CalledProcessError as e:
        print("error: ", e)
    move_vocals(song_name=song_name)
 
def whisper_transcription(song_name):
    curr_path = str(os.getcwd())
    file_path = os.path.join(curr_path,rf"processed_songs/{song_name}", f"{song_name}_Vocals.wav")
    w_t_cmd = ["whisper", file_path, "--model", "medium"]
    try:
        subprocess.run(w_t_cmd, shell=False)
        print("Lyrics extracted successfully")
    except subprocess.CalledProcessError as e:
        print("Error Occured while extracting Lyrics: ",e)
    move_transcriptions(song_name)

def get_correct_timestamp(song_name):
    songs_folder = os.path.join(os.getcwd(), 'processed_songs', f'{song_name}')
    song_file = os.path.join(songs_folder, f'{song_name}_Vocals.wav')
    signal, sr = librosa.load(song_file)
    with open(os.path.join(songs_folder,'lyrics', f'{song_name}_Vocals.json'), 'r') as f:
        json_data = json.load(f)
    chunk_seconds = math.ceil(json_data['segments'][0]['end']) # max chunk length-different for each song
    chunk_length = chunk_seconds * sr
    # taking the first chunk:
    chunk_0 = signal[0:chunk_length]
    # check the number of samples in chunk:
    # print(f"Chunk 0: {len(chunk_0)} samples")
    db_chunk_0 = librosa.amplitude_to_db(chunk_0)
    y = [i for i,e in list(enumerate(db_chunk_0))]
    min_db = np.abs(min(db_chunk_0))
    norm_db_chunk_0 = [num + min_db for num in db_chunk_0]
    # assuming a minimum of 65 db for vocals
    target_db = 65
    start_db = np.argmax(np.array(norm_db_chunk_0) >= target_db)
    start_timestamp = start_db/sr - 1 # subtracting 1 second to display the text a second before the vocals start.
    json_data['segments'][0]['start'] = start_timestamp
    with open(os.path.join(songs_folder,'lyrics', f'new_{song_name}_Vocals.json'), 'w') as f:
        json.dump(json_data, f)


if __name__=="__main__":
    # get_correct_timestamp("shapeofyou")
    merge_audio("shapeofyou")