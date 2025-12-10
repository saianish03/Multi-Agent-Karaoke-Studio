import subprocess
import sys
import os
import shutil
import requests
import zipfile

def install_system_dependencies():
    """Install required system dependencies for Streamlit Cloud"""
    dependencies = {
        'ffmpeg': 'ffmpeg',
        'libsndfile1': 'libsndfile1'
    }
    
    for dep_name, apt_package in dependencies.items():
        try:
            # Check if dependency is installed
            subprocess.run(['pip', 'install', 'librosa'], capture_output=True, check=True)
            if dep_name == 'ffmpeg':
                subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            elif dep_name == 'libsndfile1':
                subprocess.run(['pkg-config', '--exists', 'sndfile'], capture_output=True, check=True)
            print(f"✓ {dep_name} is already installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"Installing {dep_name}...")
            try:
                subprocess.run(['apt-get', 'update'], capture_output=True, check=True)
                subprocess.run(['apt-get', 'install', '-y', apt_package], capture_output=True, check=True)

                print(f"{dep_name} installed successfully")
            except subprocess.CalledProcessError as e:
                print(f"Warning: Could not install {dep_name}. Error: {e}")


def setup_vocal_remover():
    """Download and setup vocal-remover with model checkpoint"""
    utils_dir = os.path.join(os.path.dirname(__file__), 'utils')
    vocal_remover_dir = os.path.join(utils_dir, 'vocal-remover')
    
    # Create utils directory if it doesn't exist
    os.makedirs(utils_dir, exist_ok=True)
    
    # Remove existing vocal-remover directory if it exists
    if os.path.exists(vocal_remover_dir):
        print(f"Removing existing vocal-remover directory...")
        shutil.rmtree(vocal_remover_dir)
        print(f"✓ Removed old vocal-remover directory")
    
    # Download vocal-remover zip
    print("Downloading vocal-remover with model checkpoint...")
    download_url = "https://github.com/tsurumeso/vocal-remover/releases/download/v6.0.0b4/vocal-remover-v6.0.0b4.zip"
    zip_path = os.path.join(utils_dir, 'vocal-remover-v6.0.0b4.zip')
    
    try:
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        
        # Download with progress
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if total_size > 0:
                        progress = (downloaded_size / total_size) * 100
                        print(f"Download progress: {progress:.1f}%", end='\r')
        
        print("\n✓ Downloaded vocal-remover successfully")
        
        # Extract zip file
        print("Extracting vocal-remover...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(utils_dir)
        
        print("✓ Extracted vocal-remover successfully")
        
        # Delete zip file
        os.remove(zip_path)
        print("✓ Removed zip file")
        
        print(f"✓ Vocal-remover is ready at {vocal_remover_dir}")
        
    except requests.RequestException as e:
        print(f"Warning: Could not download vocal-remover. Error: {e}")
    except zipfile.BadZipFile as e:
        print(f"Warning: Could not extract vocal-remover zip. Error: {e}")
    except Exception as e:
        print(f"Warning: Error setting up vocal-remover. Error: {e}")