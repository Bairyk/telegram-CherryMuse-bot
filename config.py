import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set. Please add it in Railway environment variables or a local .env file.")

# Public HuggingFace Spaces (no API token required)
HF_SPACES = {
    'text': 'https://huggingface.co/spaces/microsoft/DialoGPT-medium',
    'image': 'https://huggingface.co/spaces/runwayml/stable-diffusion-v1-5',
    'video': 'https://huggingface.co/spaces/damo-vilab/modelscope-text-to-video-synthesis'
}

print("[OK] Using public HuggingFace Spaces (no API token required)")

# Database and limits
DATABASE_PATH = 'bot_data.db'
MAX_RETRIES = 3
RETRY_DELAY = 2
RATE_LIMIT_TEXT = 10
RATE_LIMIT_IMAGE = 5
RATE_LIMIT_VIDEO = 2

# Content type mapping
CONTENT_TYPES = {
    'text': 'story',
    'image': 'visual',
    'video': 'animation'
}

# Debug mode
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Logging configuration
def setup_logging():
    """Setup comprehensive logging for the bot"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler('bot.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    # Set specific loggers
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.INFO)

    return logging.getLogger(__name__)