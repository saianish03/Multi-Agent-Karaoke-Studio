import sys
from PIL import Image, ImageDraw, ImageFont, ImageOps
import json
import os

def format_string(line_length, input_string):
    words = input_string.split()
    lines = []
    current_line = ""

    for word in words:
        if len(current_line + word) <= line_length:
            current_line += word + " "
        else:
            lines.append(current_line.strip())
            current_line = word + " "

    if current_line:
        lines.append(current_line.strip())

    formatted_string = "\n".join(lines)
    return formatted_string

def add_blank_slots(json_data):
    blank_indexes = []
    for i in range(len(json_data['segments'])):
        if i+1<len(json_data['segments']):
            if not round(json_data['segments'][i]['end']) == round(json_data['segments'][i+1]['start']):
                blank_indexes.append((i+1, json_data['segments'][i]['end'], json_data['segments'][i+1]['start']))
    count = 0
    for i in range(len(blank_indexes)):
        dict = {}
        dict = dict.fromkeys(json_data['segments'][0].keys())
        dict['start'] = blank_indexes[i][1]
        dict['end'] = blank_indexes[i][2]
        dict['text'] = '...'
        dict['tokens'] = []
        json_data['segments'].insert(blank_indexes[i][0]+count, dict)
        count+=1

def create_image(text, font_size=75, width=1280, height=720, output_path='output', 
                 curr_dir=None, album_art_path=None):
    """
    Create image with text overlaid on blurred album art or solid color
    """
    if curr_dir == None:
        curr_dir = os.getcwd()
    
    # Load album art or create solid color fallback
    if album_art_path and os.path.exists(album_art_path):
        # Load blurred album art
        image = Image.open(album_art_path).convert('RGBA')
        if image.size != (width, height):
            image = image.resize((width, height), Image.Resampling.LANCZOS)
    else:
        # Fallback to solid color
        image = Image.new("RGBA", (width, height), color=(147, 64, 136, 255))
    
    # Add dark semi-transparent overlay for text readability
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 120))  # 47% opacity
    image = Image.alpha_composite(image, overlay)
    
    # Create drawing context
    draw = ImageDraw.Draw(image)
    
    # Load font
    font_path = os.path.join(curr_dir, r'utils/fonts/Dancing_Script', 'DancingScript-VariableFont_wght.ttf')
    font = ImageFont.truetype(font_path, font_size)
    
    # Format text
    ftext = format_string(40, text)
    
    # Draw text with outline for better readability
    x, y = width / 2, height / 2
    
    # Draw black outline
    outline_width = 3
    for adj_x in range(-outline_width, outline_width + 1):
        for adj_y in range(-outline_width, outline_width + 1):
            draw.text((x + adj_x, y + adj_y), text=ftext, fill='black', 
                     font=font, anchor="mm", align='center')
    
    # Draw white text on top
    draw.text((x, y), text=ftext, fill='white', font=font, anchor="mm", align='center')
    
    # Convert back to RGB and save
    final_image = image.convert('RGB')
    final_image.save(output_path + '.png')


def text_to_images(song_name):
    curr_dir = os.getcwd()
    
    # Check for blurred album art
    album_art_path = os.path.join(curr_dir, 'processed_songs', song_name, 'album_art_blurred.jpg')
    use_album_art = os.path.exists(album_art_path)
    
    if use_album_art:
        print(f"[Image Generation] Using blurred album art as background")
    else:
        print(f"[Image Generation] Album art not found, using solid color background")

    # reading the lyrics from the json file
    input_file_path = os.path.join(curr_dir, rf'processed_songs/{song_name}/lyrics/new_{song_name}_Vocals.json')
    with open(input_file_path, 'r') as file:
        json_data = json.load(file)

    song_title = input_file_path.split(sep=os.sep)[-1].replace(".json","").upper().split("_")[1]
    json_data['title'] = song_title

    add_blank_slots(json_data)  # adding blank dictionaries into the json file

    lines = [json_data['segments'][i]['text'] for i in range(len(json_data['segments']))]

    output_folder = os.path.join(curr_dir, rf'processed_songs/{song_name}/lyrics/lyric_images')
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Process title image with album art
    image_path = os.path.join(output_folder, "output_image_0")
    create_image(json_data['title'], output_path=image_path, curr_dir=curr_dir,
                 album_art_path=album_art_path if use_album_art else None)
    json_data['image_title_location'] = image_path

    # Process each lyric line with album art
    for i, line in enumerate(lines):
        image_path = os.path.join(output_folder, f"output_image_{i+1}")
        json_data['segments'][i]['image_location'] = f"lyrics/lyric_images/output_image_{i+1}.png"
        create_image(line.strip(), output_path=image_path, curr_dir=curr_dir,
                    album_art_path=album_art_path if use_album_art else None)
    
    for i in range(len(json_data["segments"])):
        if i == 0:
            json_data['title_duration'] = float(json_data["segments"][0]['start'])
        json_data["segments"][i]['duration'] = float(json_data["segments"][i]['end']) - float(json_data["segments"][i]['start'])
 
    input_text_path = os.path.join(curr_dir, rf'processed_songs/{song_name}/images_duration.txt')
    with open(input_text_path, "w") as f:
        title_slide = "file " + "lyrics/lyric_images/output_image_0.png" + "\n" + "duration " + str(json_data['title_duration']) + "\n"
        f.write(title_slide)
        for i in range(len(json_data["segments"])):
            buffer = "file " + json_data["segments"][i]['image_location'] + "\n" + "duration " + str(json_data["segments"][i]['duration']) + "\n"
            f.write(buffer)

    # saving the json file
    with open(input_file_path, 'w') as outfile:
        json.dump(json_data, outfile)
    
    print(f"[Image Generation] Generated {len(lines) + 1} images with {'blurred album art' if use_album_art else 'solid'} background")