# telegram-candyai-bot

PeachMuse AI
Welcome to PeachMuse AI, your vibrant companion for unrestricted storytelling and idea generation! This AI-powered platform brings bold, imaginative role-playing to life through a Telegram bot (@PeachMuse), crafting stories, images, and short videos (up to 30s) based on your prompts. Built for creativity on a budget, PeachMuse AI uses free-tier hosting and open-source models, with analytics to track what sparks your imagination most.
Features

Role-Playing Chats: Engage in dynamic, creative conversations with @PeachMuse via Telegram.
Text, Image, and Video Generation: Create stories (Llama-based), vibrant images (Stable Diffusion), and short animations (AnimateDiff).
Analytics: Track popular prompts, images, and videos to discover trends and improve the experience.
Scalable Design: Ready for future user auth, price tiers, crypto payments, and multi-user support.
Low-Cost: Runs on Hugging Face Spaces and Railway free tiers (under $5/mo).

Architecture
PeachMuse AI connects:

@PeachMuse Bot: Python-based, hosted on Railway, processes user inputs and logs interactions.
AI Server: Hugging Face Spaces (free tier, ZeroGPU) runs Llama, Stable Diffusion, and AnimateDiff models.
Storage/Logging: SQLite for chat metadata, free cloud for media (auto-deletes non-key items after 24h). Logs anonymized usage for insights.

Setup Instructions
Follow these steps to set up PeachMuse AI. Assumes intermediate Python knowledge and accounts for GitHub, Telegram, Hugging Face, and Railway.
Prerequisites

Python 3.9+
Git
Accounts: GitHub, Telegram (for bot token), Hugging Face, Railway
Install: pip install python-telegram-bot huggingface_hub torch diffusers sqlite3

Part 1: Telegram Bot Setup

Clone Repo: git clone https://github.com/yourusername/peachmuse-ai.git
Set Up Bot:
Create a Telegram bot via @BotFather to get a token.
Create .env with TELEGRAM_TOKEN=your_token.
Write bot script (see /bot/main.py for commands like /start, /feedback).


Deploy to Railway:
Push to GitHub.
Link Railway to repo for CI/CD (free tier, 500 hours/mo).
Set env vars in Railway dashboard.


Test Locally: Run python bot/main.py to verify commands.

Details in /docs/part1_bot_setup.md.
Part 2: AI Server on Hugging Face Spaces

Create Space: Sign up at Hugging Face, create a new Space (free tier).
Add Models:
Clone meta-llama/Llama-3-8B, runwayml/stable-diffusion-v1-5, guoyww/animatediff.
Use Gradio in app.py for API endpoints (/text, /image, /video).


Deploy: Push to Space, handle ZeroGPU limits with retries.
Test: Curl endpoints (e.g., curl http://your-space.hf.space/api/text).

Details in /docs/part2_ai_server.md.
Part 3: Storage, Logging, and Future Hooks

Set Up SQLite: Initialize DB for chat metadata (/storage/db.sql).
Logging: Log prompts/themes (e.g., JSON in /logs/), anonymized.
Media Storage: Sync media to GitHub or free cloud, delete non-key after 24h.
Hooks: Add placeholders for auth (Telegram IDs), payments, scalability.
Analytics: Query logs for trends (e.g., SELECT theme, COUNT(*) FROM logs).

Details in /docs/part3_storage_logging.md.
Usage

Start chatting: /start with @PeachMuse on Telegram.
Try prompts:
Text: “Craft a bold sci-fi story!”
Image: “Draw a vibrant fantasy character.”
Video: “Make a 30s adventure clip.”


Feedback: Use /feedback to share ideas or issues.

Analytics
Check /logs/analytics.json or SQLite DB for:

Popular prompts (e.g., fantasy vs. romance).
Error rates (e.g., API timeouts).
Suggestions (e.g., add new video styles).

Run /scripts/analyze.py to generate summaries.
Contributing
We welcome contributions! Fork the repo, make changes, and submit a PR. Follow our Contributing Guidelines.
License
MIT License. See LICENSE for details.
Contact/Support

Chat with @PeachMuse for live testing.
File issues on GitHub or message for support.

Unleash your juiciest ideas with PeachMuse AI!
