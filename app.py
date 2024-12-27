from google.generativeai.types import HarmCategory, HarmBlockThreshold
import google.generativeai as genai
from flask import Flask, request, jsonify, send_from_directory
try:
    from urllib.parse import unquote  # PY3
except ImportError:
    from urllib import unquote  # PY2
from pprint import pprint
import os
import sys
import json
import pygame


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'static'))

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    print(f"Directory created: {UPLOAD_FOLDER}")
else:
    print(f"Directory already exists: {UPLOAD_FOLDER}")

config_path = os.path.join(BASE_DIR, 'config.json')

if not os.path.exists(config_path):
    GEMINI_KEY = input("Please provide GEMINI KEY: ")
    json_config = {"GEMINI_KEY": GEMINI_KEY}
    with open(config_path, "w") as json_file:
        json.dump(json_config, json_file, indent=4)

with open(config_path, 'r') as config_file:
    json_config = json.load(config_file)
    genai.configure(api_key=json_config["GEMINI_KEY"])
    model = genai.GenerativeModel(model_name='gemini-1.5-pro')
    flask_port = json_config.get("FLASK_PORT", 7070)

def convert_to_jpg(input_path, quality=85):
    """
    Convert any image file supported by Pygame to a compressed JPG.

    Args:
        input_path (str): Path to the input image file.
        quality (int): Compression quality (1-100). Default is 85.

    Returns:
        str: Path to the output JPG file on success.
        None: If the conversion fails.
    """
    # Initialize pygame
    pygame.init()

    # Check if the input file exists
    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        return None

    # Generate the output file path with a .jpg extension
    output_path = os.path.splitext(input_path)[0] + ".jpg"

    # Try to load the image using pygame
    try:
        image = pygame.image.load(input_path)
    except pygame.error as e:
        print(f"Error loading image: {e}")
        return None

    # Convert the image to RGB (JPG doesn't support transparency)
    image_rgb = pygame.Surface(image.get_size(), flags=0, depth=24)
    image_rgb.blit(image, (0, 0))

    # Save the image as a JPG
    try:
        pygame.image.save(image_rgb, output_path)
        print(f"Image successfully saved as JPG: {output_path}")
        return output_path
    except Exception as e:
        print(f"Error saving image: {e}")
        return None

# Route to serve index.html from the static folder
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/send', methods=['POST'])
def send_to_api():
    json_request = request.get_json()
    messages = []
    for message in json_request:
        parts = [message["text"]]
        if len(message["files"]):
            for file in message["files"]:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unquote(file))
                google_file = genai.upload_file(file_path)
                parts.append(google_file)
        if message["type"] == "user":
            messages.append({'role': 'user', 'parts': parts})
        else:
            messages.append({'role': 'model', 'parts': parts})

    pprint(messages)

    try:
        response = model.generate_content(
            messages,
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )
        pprint(response.text)
        return jsonify({'success': True, 'response': response.text}), 200
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"success": False, "error": str(e)}), 500



@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'}), 400

    if file:
        # Save the file to the upload folder
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        jpg_file = convert_to_jpg(file_path)
        return jsonify({'success': True, 'jpg_file': os.path.basename(jpg_file)}), 200

if __name__ == '__main__':
    app.run(debug=True, port=flask_port)
