import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set. Please add it in Railway environment variables or a local .env file.")
HF_SPACES_URL = os.getenv("HF_SPACES_URL", "https://your-username-your-space.hf.space")  # Replace with your Space URL
DATABASE_PATH = 'bot_data.db'
MAX_RETRIES = 3
RETRY_DELAY = 2
RATE_LIMIT_TEXT = 10
RATE_LIMIT_IMAGE = 5
RATE_LIMIT_VIDEO = 2
CONTENT_TYPES = {
    'text': 'story',
    'image': 'visual',
    'video': 'animation'
}
