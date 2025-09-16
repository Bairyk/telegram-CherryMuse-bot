import asyncio
import time
import json
import re
from datetime import datetime
from typing import Optional

import requests
import base64
import io
from PIL import Image
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    ContextTypes, filters
)

from config import *
from database import db

class AIBot:
    def __init__(self):
        self.app = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup command and message handlers"""
        # Commands
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("feedback", self.feedback_command))
        self.app.add_handler(CommandHandler("stats", self.stats_command))
        
        # Message handlers
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        self.app.add_handler(MessageHandler(filters.PHOTO, self.handle_image))
        self.app.add_handler(MessageHandler(filters.VIDEO, self.handle_video))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_msg = """
🎭 Welcome to your Creative AI Companion!

I can help you with:
• 📝 Creative storytelling and roleplay
• 🎨 Image generation from descriptions  
• 🎬 Short video animations (30s clips)

Just send me your ideas and I'll bring them to life!

Use /help for detailed instructions.
        """
        await update.message.reply_text(welcome_msg)
        
        # Log interaction
        await db.log_interaction(
            user_id=update.effective_user.id,
            content_type='command',
            prompt='/start',
            success=True
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_msg = """
🔧 How to use your AI Companion:

**Text Generation:**
Send any message to generate creative stories, roleplay scenarios, or ideas.
Example: "Write a fantasy adventure about a dragon"

**Image Generation:**  
Send a photo with caption or just text describing what you want to see.
Example: "A magical forest with glowing mushrooms"

**Video Generation:**
Use keywords like "animate" or "video" with your description.
Example: "Animate a sunset over mountains"

**Commands:**
• /feedback <message> - Send feedback to developers
• /stats - View your usage statistics

✨ Tips: Be descriptive for better results!
        """
        await update.message.reply_text(help_msg)
    
    async def feedback_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /feedback command"""
        if not context.args:
            await update.message.reply_text("Please provide feedback: /feedback <your message>")
            return
        
        feedback_text = " ".join(context.args)
        
        # Log feedback
        await db.log_interaction(
            user_id=update.effective_user.id,
            content_type='feedback',
            prompt=feedback_text,
            success=True
        )
        
        await update.message.reply_text("Thank you for your feedback! 🙏")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user statistics"""
        try:
            themes = await db.get_popular_themes(days=7)
            errors = await db.get_error_stats(days=1)
            
            stats_msg = "📊 Weekly Popular Themes:\n"
            for theme, count in themes[:5]:
                stats_msg += f"• {theme}: {count} requests\n"
            
            if errors:
                stats_msg += "\n🔧 Recent Issues:\n"
                for content_type, error_count in errors:
                    stats_msg += f"• {content_type}: {error_count} errors\n"
            
            await update.message.reply_text(stats_msg or "No data available yet!")
            
        except Exception as e:
            await update.message.reply_text("Stats temporarily unavailable.")
    
    def extract_theme(self, text: str) -> Optional[str]:
        """Extract theme from user message"""
        themes = {
            r'fantasy|dragon|magic|wizard|elf': 'fantasy',
            r'sci-?fi|space|robot|alien|future': 'sci-fi',
            r'romance|love|relationship|date': 'romance',
            r'horror|scary|ghost|dark|fear': 'horror',
            r'adventure|quest|journey|explore': 'adventure',
            r'anime|manga|kawaii|japanese': 'anime'
        }
        
        text_lower = text.lower()
        for pattern, theme in themes.items():
            if re.search(pattern, text_lower):
                return theme
        return 'general'
    
    async def call_ai_api(self, endpoint: str, data: dict, retries: int = MAX_RETRIES):
        """Call Hugging Face Spaces API with retry logic"""
        for attempt in range(retries):
            try:
                start_time = time.time()
                
                # Updated API call to actual Hugging Face Space
                response = requests.post(
                    f"{HF_SPACES_URL}/api/{endpoint}",
                    json=data,
                    timeout=120,  # Longer timeout for AI generation
                    headers={"Content-Type": "application/json"}
                )
                
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    return response.json(), response_time
                else:
                    raise Exception(f"API returned {response.status_code}: {response.text}")
                    
            except requests.exceptions.Timeout:
                if attempt == retries - 1:
                    raise Exception("AI service is busy. Please try again in a moment.")
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
            except Exception as e:
                if attempt == retries - 1:
                    raise e
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages for story generation"""
        user_id = update.effective_user.id
        prompt = update.message.text
        theme = self.extract_theme(prompt)
        
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        try:
            # Call actual AI API
            api_data = {
                "prompt": prompt,
                "theme": theme
            }
            
            result, response_time = await self.call_ai_api("generate_text", api_data)
            
            if result.get("success"):
                response_text = f"🎭 **Creative Story:**\n\n{result['result']}\n\n✨ *Generated in {response_time:.1f}s*"
                
                # Split long messages
                if len(response_text) > 4000:
                    parts = [response_text[i:i+4000] for i in range(0, len(response_text), 4000)]
                    for part in parts:
                        await update.message.reply_text(part)
                else:
                    await update.message.reply_text(response_text)
                
                # Log successful interaction
                await db.log_interaction(
                    user_id=user_id,
                    content_type='text',
                    prompt=prompt,
                    theme=theme,
                    success=True,
                    response_time=response_time
                )
            else:
                raise Exception(result.get("error", "Unknown error"))
                
        except Exception as e:
            error_msg = str(e)
            if "busy" in error_msg.lower():
                await update.message.reply_text("🤖 AI is busy generating for other users. Please try again in a moment!")
            else:
                await update.message.reply_text("Sorry, I'm having trouble generating that story right now. Please try again!")
            
            # Log failed interaction
            await db.log_interaction(
                user_id=user_id,
                content_type='text',
                prompt=prompt,
                theme=theme,
                success=False,
                error_msg=error_msg
            )
    
    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle image generation requests"""
        user_id = update.effective_user.id
        
        # Get prompt from caption or use default
        prompt = update.message.caption or "Generate an artistic image"
        theme = self.extract_theme(prompt)
        
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
        
        try:
            # Call AI API for image generation
            api_data = {
                "prompt": prompt,
                "theme": theme
            }
            
            result, response_time = await self.call_ai_api("generate_image", api_data)
            
            if result.get("success"):
                # Decode base64 image
                image_data = base64.b64decode(result['result'])
                image = Image.open(io.BytesIO(image_data))
                
                # Save temporarily and send
                with io.BytesIO() as bio:
                    image.save(bio, 'PNG')
                    bio.seek(0)
                    
                    caption = f"🎨 **Generated Image**\n📝 Prompt: {prompt}\n⏱️ Generated in {response_time:.1f}s"
                    await update.message.reply_photo(
                        photo=bio,
                        caption=caption
                    )
                
                await db.log_interaction(
                    user_id=user_id,
                    content_type='image',
                    prompt=prompt,
                    theme=theme,
                    success=True,
                    response_time=response_time
                )
            else:
                raise Exception(result.get("error", "Unknown error"))
            
        except Exception as e:
            error_msg = str(e)
            if "busy" in error_msg.lower():
                await update.message.reply_text("🎨 Image AI is busy. Please try again in a moment!")
            else:
                await update.message.reply_text("Image generation failed. Please try again!")
            
            await db.log_interaction(
                user_id=user_id,
                content_type='image',
                prompt=prompt,
                theme=theme,
                success=False,
                error_msg=error_msg
            )
    
    async def handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle video generation requests"""
        user_id = update.effective_user.id
        prompt = update.message.caption or "Create a short animation"
        theme = self.extract_theme(prompt)
        
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_video")
        await update.message.reply_text("🎬 Creating your video animation... This may take up to 2 minutes.")
        
        try:
            # Call AI API for video generation
            api_data = {
                "prompt": prompt,
                "duration": 2  # 2 seconds for free tier
            }
            
            result, response_time = await self.call_ai_api("generate_video", api_data)
            
            if result.get("success"):
                # Decode base64 video
                video_data = base64.b64decode(result['result'])
                
                with io.BytesIO(video_data) as bio:
                    bio.name = 'generated_video.mp4'  # Required for Telegram
                    
                    caption = f"🎬 **Generated Animation**\n📝 Prompt: {prompt}\n⏱️ Generated in {response_time:.1f}s\n🎞️ {result.get('frames', 16)} frames at {result.get('fps', 8)} fps"
                    await update.message.reply_video(
                        video=bio,
                        caption=caption
                    )
                
                await db.log_interaction(
                    user_id=user_id,
                    content_type='video',
                    prompt=prompt,
                    theme=theme,
                    success=True,
                    response_time=response_time
                )
            else:
                raise Exception(result.get("error", "Unknown error"))
                
        except Exception as e:
            error_msg = str(e)
            if "busy" in error_msg.lower():
                await update.message.reply_text("🎬 Video AI is busy. Please try again in a moment!")
            else:
                await update.message.reply_text("Video generation failed. Please try again!")
            
            await db.log_interaction(
                user_id=user_id,
                content_type='video',
                prompt=prompt,
                theme=theme,
                success=False,
                error_msg=error_msg
            )
    
    async def run(self):
        """Initialize and run the bot with keep-alive"""
        # Initialize database
        await db.init_db()
        
        # Start bot
        await self.app.initialize()
        await self.app.start()
        
        print("🤖 Bot started successfully!")
        
        # Start polling with keep-alive
        async with self.app:
            await self.app.updater.start_polling()
            while True:
                await asyncio.sleep(60)  # Keep container alive

if __name__ == "__main__":
    bot = AIBot()
    try:
        asyncio.run(bot.run())
    except asyncio.CancelledError:
        print("Bot shutdown requested. Stopping gracefully...")
        asyncio.run_coroutine_threadsafe(bot.app.stop(), asyncio.get_event_loop())
    except Exception as e:
        print(f"Unexpected error during bot run: {e}")
