import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
HF_SPACES_URL = os.getenv('HF_SPACES_URL', 'https://your-space.hf.space')

# Database Configuration
DATABASE_PATH = 'bot_data.db'

# API Configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Rate Limiting (requests per minute)
RATE_LIMIT_TEXT = 10
RATE_LIMIT_IMAGE = 5
RATE_LIMIT_VIDEO = 2

# Content Types
CONTENT_TYPES = {
    'text': 'story',
    'image': 'visual',
    'video': 'animation'
}
