import requests
import base64
from PIL import Image
import io
import json
import os
import discord
import logging
from discord.ext import commands

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration handling with validation
try:
    config = eval(os.environ.get('OPTIONS', '{}'))
    logger.info("Loaded configuration: %s", config)
    
    DISCORD_TOKEN = config.get('discord_token')
    if not DISCORD_TOKEN:
        raise ValueError("Discord token is missing")
        
    USER_ID = config.get('user_id')
    if not USER_ID:
        raise ValueError("User ID is missing")
    USER_ID = int(USER_ID)
    
    API_KEY = config.get('api_key')
    if not API_KEY:
        raise ValueError("API key is missing")
        
    OLLAMA_SERVER = config.get('ollama_server')
    if not OLLAMA_SERVER:
        raise ValueError("Ollama server URL is missing")
        
    CAMERA_SERVER = config.get('camera_server')
    if not CAMERA_SERVER:
        raise ValueError("Camera server URL is missing")
        
    CAMERA_ENDPOINTS = config.get('camera_endpoints')
    if not CAMERA_ENDPOINTS:
        raise ValueError("Camera endpoints are missing")
    
    logger.info("Configuration validated successfully")
    
except Exception as e:
    logger.error("Configuration error: %s", str(e))
    raise

# Camera groups
FRONT_CAMERAS = ['front', 'road']
BACK_CAMERAS = ['back', 'shed']
ALL_CAMERAS = ['front', 'back', 'shed', 'road']

# Rest of your code...

def download_image(camera_name):
    try:
        url = f"{CAMERA_SERVER}{CAMERA_ENDPOINTS[camera_name]}"
        logger.info(f"Downloading image from: {url}")
        response = requests.get(url)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content))
        
        os.makedirs('images', exist_ok=True)
        image_path = f'images/{camera_name}_snapshot.jpg'
        image.save(image_path)
        logger.info(f"Image saved to: {image_path}")
        
        return image, image_path
    except Exception as e:
        logger.error(f"Error downloading image for {camera_name}: {str(e)}")
        raise

async def analyze_camera(camera_name):
    try:
        image, _ = download_image(camera_name)
        base64_image = encode_image_base64(image)
        
        headers = {
            'Content-Type': 'application/json',
        }
        
        payload = {
            "model": "llava",
            "prompt": f"ONLY mention if you see any people, vehicles, or animals. Keep it under 10 words. If empty just say 'Clear'.",
            "stream": False,
            "messages": [
                {
                    "role": "user",
                    "content": f"ONLY mention if you see any people, vehicles, or animals. Keep it under 10 words. If empty just say 'Clear'.",
                    "images": [base64_image]
                }
            ]
        }
        
        logger.info(f"Analyzing camera: {camera_name}")
        response = requests.post(
            f'{OLLAMA_SERVER}/api/chat',
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f"Analysis complete for {camera_name}")
        return result['message']['content']
    except Exception as e:
        logger.error(f"Error analyzing {camera_name} camera: {str(e)}")
        return f"Error checking {camera_name} camera"

@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')

def run_discord_bot():
    try:
        logger.info("Starting Discord bot...")
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Failed to start Discord bot: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        run_discord_bot()
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        raise
