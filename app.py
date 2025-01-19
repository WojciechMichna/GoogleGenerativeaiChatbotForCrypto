from google.generativeai.types import GenerationConfig, HarmCategory, HarmBlockThreshold
import google.generativeai as genai
from flask import Flask, request, jsonify, send_from_directory, render_template
try:
    from urllib.parse import unquote  # PY3
except ImportError:
    from urllib import unquote  # PY2
from pprint import pprint
import os
import json
import pygame
import requests
import matplotlib.pyplot as plt
from datetime import datetime
import time


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'static'), template_folder=os.path.join(BASE_DIR, 'templates'))

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


# Fetch historical data with retry on 429 errors
def fetch_crypto_data(coin_id, vs_currency, days, retries=3):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": vs_currency, "days": days}

    for attempt in range(retries):
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()  # Raise an error for bad HTTP responses
            return response.json()["prices"]
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:  # Too Many Requests
                print(f"Rate limit hit for {coin_id}. Waiting 5 seconds before retrying... ({attempt + 1}/{retries})")
                time.sleep(35)  # Wait before retrying
            else:
                raise e  # Raise other HTTP errors
    raise Exception(f"Failed to fetch data for {coin_id} after {retries} retries.")

# Plot the data and save it
def plot_crypto_data(coin_id, prices, output_file):
    timestamps, values = zip(*prices)  # Unpack timestamps and prices
    dates = [datetime.fromtimestamp(ts / 1000) for ts in timestamps]  # Convert to datetime
    plt.figure(figsize=(12, 8))
    plt.plot(dates, values, label=f"{coin_id.capitalize()} Price (USD)", linewidth=2)

    # Add a large, bold description at the top
    plt.suptitle(f"{coin_id.capitalize()} 30-Day Price Trend", fontsize=24, fontweight="bold", y=0.95)

    # Add standard title, labels, and legend
    plt.title(f"Based on data from CoinGecko API", fontsize=14)
    plt.xlabel("Date", fontsize=12)
    plt.ylabel("Price (USD)", fontsize=12)
    plt.legend(fontsize=12)
    plt.grid()
    plt.tight_layout(rect=[0, 0, 1, 0.92])  # Leave space for the suptitle
    plt.savefig(output_file)
    plt.close()
    print(f"Saved plot to {output_file}")

def generate_crypto_data():
    # Coins to plot
    coins = [
        "dogecoin",  # The original meme coin
        "shiba-inu",  # Inspired by Dogecoin
        "pepe",  # Based on the Pepe the Frog meme
        "dogelon-mars",  # Space-themed meme coin
        "floki",  # Inspired by Elon Musk's dog
        "akita-inu",  # Another dog-themed coin
        "kishu-inu",  # Inspired by the Kishu dog breed
    ]

    # Plot each coin
    for coin in coins:
        try:
            print(f"Fetching data for {coin}...")
            prices = fetch_crypto_data(coin, vs_currency="usd", days=30)
            output_file = os.path.join(UPLOAD_FOLDER, f"{coin}_30days_plot.jpg")
            plot_crypto_data(coin, prices, output_file)
        except Exception as e:
            print(f"Failed for {coin}: {e}")

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
    json_string = json.dumps(app.config.get('DEFAULT_JSON', '{}')).replace('\\', '\\\\').replace('"', '\\"')
    print(json_string)
    return render_template('index.html', default_json=json_string)

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

    generation_config = GenerationConfig(
        temperature=0.9,  # Set the temperature for creativity
        max_output_tokens=9000  # Adjust output token limit as needed
    )

    try:
        response = model.generate_content(
            messages,
            generation_config=generation_config,
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )
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
    default_bubble_path = os.path.join(BASE_DIR, "default.json")
    if os.path.exists(default_bubble_path):
        with open(default_bubble_path, 'r') as file:
            file_content = file.read()
        try:
            app.config['DEFAULT_JSON'] = json.loads(file_content)
            generate_crypto_data()
        except json.JSONDecodeError:
            print("Invalid JSON")
    app.run(host="0.0.0.0", debug=True, port=flask_port)
