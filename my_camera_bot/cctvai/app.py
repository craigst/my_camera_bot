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
config_path = '/data/options.json'

try:
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
    
    logger.info("Loaded configuration: %s", config)
    
    DISCORD_TOKEN = config['discord_token']
    USER_ID = int(str(config['user_id']))
    API_KEY = config['api_key']
    OLLAMA_SERVER = config['ollama_server']
    CAMERA_SERVER = config['camera_server']
    CAMERA_ENDPOINTS = config['camera_endpoints']
    
    logger.info("Configuration validated successfully")
    
except Exception as e:
    logger.error("Configuration error: %s", str(e))
    raise

# Camera groups
FRONT_CAMERAS = ['front', 'road']
BACK_CAMERAS = ['back', 'shed']
ALL_CAMERAS = ['front', 'back', 'shed', 'road']

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
        return image_path
    except Exception as e:
        logger.error(f"Error downloading image from {camera_name}: {str(e)}")
        raise

def analyze_image(image_path):
    try:
        with open(image_path, 'rb') as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        headers = {'Content-Type': 'application/json'}
        payload = {
            'image': image_data,
            'api_key': API_KEY
        }
        
        response = requests.post(f"{OLLAMA_SERVER}/analyze", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error analyzing image: {str(e)}")
        raise

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')

@bot.command(name='snapshot')
async def snapshot(ctx, camera_name: str = None):
    if ctx.author.id != USER_ID:
        await ctx.send("You are not authorized to use this bot.")
        return

    try:
        if camera_name:
            if camera_name.lower() not in ALL_CAMERAS:
                await ctx.send(f"Invalid camera name. Available cameras: {', '.join(ALL_CAMERAS)}")
                return
            
            cameras = [camera_name.lower()]
        else:
            cameras = ALL_CAMERAS

        for cam in cameras:
            image_path = download_image(cam)
            analysis = analyze_image(image_path)
            
            with open(image_path, 'rb') as f:
                picture = discord.File(f)
                await ctx.send(f"Camera: {cam}\nAnalysis: {analysis['description']}", file=picture)
                
    except Exception as e:
        logger.error(f"Error in snapshot command: {str(e)}")
        await ctx.send(f"Error processing snapshot: {str(e)}")

@bot.command(name='front')
async def front(ctx):
    if ctx.author.id != USER_ID:
        await ctx.send("You are not authorized to use this bot.")
        return

    try:
        for camera in FRONT_CAMERAS:
            image_path = download_image(camera)
            analysis = analyze_image(image_path)
            
            with open(image_path, 'rb') as f:
                picture = discord.File(f)
                await ctx.send(f"Camera: {camera}\nAnalysis: {analysis['description']}", file=picture)
    except Exception as e:
        logger.error(f"Error in front command: {str(e)}")
        await ctx.send(f"Error processing front cameras: {str(e)}")

@bot.command(name='back')
async def back(ctx):
    if ctx.author.id != USER_ID:
        await ctx.send("You are not authorized to use this bot.")
        return

    try:
        for camera in BACK_CAMERAS:
            image_path = download_image(camera)
            analysis = analyze_image(image_path)
            
            with open(image_path, 'rb') as f:
                picture = discord.File(f)
                await ctx.send(f"Camera: {camera}\nAnalysis: {analysis['description']}", file=picture)
    except Exception as e:
        logger.error(f"Error in back command: {str(e)}")
        await ctx.send(f"Error processing back cameras: {str(e)}")

def main():
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    main()
