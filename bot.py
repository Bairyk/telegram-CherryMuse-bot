import asyncio
import time
import json
import re
from datetime import datetime
from typing import Optional

import requests
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    ContextTypes, filters
)

from config import *

from database import db

# ... (rest of bot.py remains unchanged, including class AIBot and run method)
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
                
                # Placeholder API call - will be implemented in Part 2
                response = requests.post(
                    f"{HF_SPACES_URL}/{endpoint}",
                    json=data,
                    timeout=30
                )
                
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    return response.json(), response_time
                else:
                    raise Exception(f"API returned {response.status_code}")
                    
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
            # For now, return a placeholder response
            # In Part 2, this will call the actual AI API
            response_text = f"🎭 Creative Response for: '{prompt[:50]}...'\n\n[AI model will generate story here in Part 2]"
            
            await update.message.reply_text(response_text)
            
            # Log successful interaction
            await db.log_interaction(
                user_id=user_id,
                content_type='text',
                prompt=prompt,
                theme=theme,
                success=True,
                response_time=1.5  # placeholder
            )
            
        except Exception as e:
            await update.message.reply_text("Sorry, I'm having trouble generating that story right now. Please try again!")
            
            # Log failed interaction
            await db.log_interaction(
                user_id=user_id,
                content_type='text',
                prompt=prompt,
                theme=theme,
                success=False,
                error_msg=str(e)
            )
    
    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle image generation requests"""
        user_id = update.effective_user.id
        
        # Get prompt from caption or use default
        prompt = update.message.caption or "Generate an image based on the uploaded photo"
        theme = self.extract_theme(prompt)
        
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
        
        try:
            # Placeholder for image generation
            await update.message.reply_text(f"🎨 Image generation for: '{prompt}'\n\n[Stable Diffusion will generate image here in Part 2]")
            
            await db.log_interaction(
                user_id=user_id,
                content_type='image',
                prompt=prompt,
                theme=theme,
                success=True,
                response_time=3.2  # placeholder
            )
            
        except Exception as e:
            await update.message.reply_text("Image generation failed. Please try again!")
            
            await db.log_interaction(
                user_id=user_id,
                content_type='image',
                prompt=prompt,
                theme=theme,
                success=False,
                error_msg=str(e)
            )
    
    async def handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle video generation requests"""
        user_id = update.effective_user.id
        prompt = update.message.caption or "Animate the uploaded video"
        theme = self.extract_theme(prompt)
        
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_video")
        
        try:
            # Placeholder for video generation
            await update.message.reply_text(f"🎬 Video animation for: '{prompt}'\n\n[AnimateDiff will generate video here in Part 2]")
            
            await db.log_interaction(
                user_id=user_id,
                content_type='video',
                prompt=prompt,
                theme=theme,
                success=True,
                response_time=15.5  # placeholder
            )
            
        except Exception as e:
            await update.message.reply_text("Video generation failed. Please try again!")
            
            await db.log_interaction(
                user_id=user_id,
                content_type='video',
                prompt=prompt,
                theme=theme,
                success=False,
                error_msg=str(e)
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
