import requests
import base64
from PIL import Image
import io
import json
import os
import discord
from discord.ext import commands

# Get config from Home Assistant
config = eval(os.environ.get('OPTIONS', '{}'))

# Configuration from Home Assistant options
DISCORD_TOKEN = config.get('discord_token')
USER_ID = int(config.get('user_id'))
API_KEY = config.get('api_key')
OLLAMA_SERVER = config.get('ollama_server')
CAMERA_SERVER = config.get('camera_server')
CAMERA_ENDPOINTS = config.get('camera_endpoints')

# Camera groups
FRONT_CAMERAS = ['front', 'road']
BACK_CAMERAS = ['back', 'shed']
ALL_CAMERAS = ['front', 'back', 'shed', 'road']

# Rest of your existing code...


intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

def download_image(camera_name):
    url = f"{CAMERA_SERVER}{CAMERA_ENDPOINTS[camera_name]}"
    response = requests.get(url)
    image = Image.open(io.BytesIO(response.content))
    
    os.makedirs('images', exist_ok=True)
    image_path = f'images/{camera_name}_snapshot.jpg'
    image.save(image_path)
    print(f"Image saved to: {image_path}")
    
    return image, image_path

def encode_image_base64(image):
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

async def analyze_camera(camera_name):
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
    
    try:
        response = requests.post(
            f'{OLLAMA_SERVER}/api/chat',
            headers=headers,
            json=payload,
            timeout=30  # Reduced timeout
        )
        result = response.json()
        return result['message']['content']
    except Exception as e:
        return "Error checking camera"

async def send_camera_alert(descriptions, cameras, channel, title="Camera Alert"):
    embed = discord.Embed(title=title, color=0x00ff00)
    files = []
    
    # Create summary of all cameras
    summary = "\n".join([f"{camera.upper()}: {descriptions[camera]}" for camera in cameras])
    embed.description = summary
    
    # Add all images as separate embeds
    embeds = [embed]
    
    for camera in cameras:
        image_path = f'images/{camera}_snapshot.jpg'
        file = discord.File(image_path, filename=f"{camera}.jpg")
        files.append(file)
        
        # Create new embed for each image
        img_embed = discord.Embed(title=f"{camera.upper()} Camera", color=0x00ff00)
        img_embed.set_image(url=f"attachment://{camera}.jpg")
        embeds.append(img_embed)
    
    await channel.send(files=files, embeds=embeds)
DOOR_CHECK_PHRASES = [
    "who's at the door", "whos at the door", "!door", "check door",
    "check the door", "door check", "anyone there", "anyone at door",
    "anyone at the door", "is someone there", "is anyone there",
    "door camera", "front door", "check camera", "doorbell",
    "door bell", "visitor", "visitors", "who is it", "who's there"
]

CAMERA_COMMANDS = {
    "check all": ALL_CAMERAS,
    "check front": FRONT_CAMERAS,
    "check back": BACK_CAMERAS,
    "check shed": ["shed"],
    "check road": ["road"]
}

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.event
async def on_message(message):
    if message.author == bot.user or message.author.id != USER_ID:
        return

    content = message.content.lower()

    if content == "help":
        await send_help_message(message.channel)
        return

    if content in DOOR_CHECK_PHRASES:
        description = await analyze_camera('front')
        await send_camera_alert({'front': description}, ['front'], message.channel, "Door Alert")
    
    for command, cameras in CAMERA_COMMANDS.items():
        if content.startswith(command):
            descriptions = {}
            for camera in cameras:
                descriptions[camera] = await analyze_camera(camera)
            await send_camera_alert(
                descriptions, 
                cameras, 
                message.channel, 
                f"Camera Alert - {command.title()}"
            )
            break

    await bot.process_commands(message)

async def send_help_message(channel):
    help_embed = discord.Embed(
        title="Camera Bot Commands",
        description="Here are all available commands:",
        color=0x00ff00
    )
    
    # Door commands
    door_commands = "\n".join(DOOR_CHECK_PHRASES[:5]) + "\n*(and similar phrases)*"
    help_embed.add_field(
        name="🚪 Door Check Commands", 
        value=door_commands, 
        inline=False
    )
    
    # Camera section commands
    camera_sections = """
    `check all` - View all cameras
    `check front` - View front door and road cameras
    `check back` - View back yard and shed cameras
    `check shed` - View shed camera only
    `check road` - View road camera only
    """
    help_embed.add_field(
        name="📷 Camera Section Commands", 
        value=camera_sections, 
        inline=False
    )
    
    await channel.send(embed=help_embed)
from aiohttp import web
import asyncio

# Add these with your existing imports and bot setup
routes = web.RouteTableDef()

@routes.post('/check-door')
async def handle_door_check(request):
    # Verify API key if sent from Home Assistant
    api_key = request.headers.get('X-Api-Key')
    if api_key != API_KEY:
        return web.Response(status=401)
        
    description = await analyze_camera('front')
    user = await bot.fetch_user(USER_ID)
    await send_camera_alert({'front': description}, ['front'], user, "Door Alert - Motion Detected")
    
    return web.Response(text='Alert sent')

async def start_server():
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    print("HTTP server started on http://localhost:8080")

def run_bot_with_server():
    async def start():
        await start_server()
        await bot.start(DISCORD_TOKEN)

    asyncio.run(start())

if __name__ == "__main__":
    run_bot_with_server()
