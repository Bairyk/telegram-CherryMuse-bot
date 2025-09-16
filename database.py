# bot.py
#!/usr/bin/env python3
"""
AI Roleplay Telegram Bot - Clean Implementation
Using specific Hugging Face Spaces for text, image, and video generation
"""

import asyncio
import time
import json
import re
import base64
import io
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from PIL import Image

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    ContextTypes, filters, CallbackQueryHandler
)

from config import *
from database import db

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CharacterManager:
    """Manage roleplay characters"""
    
    DEFAULT_CHARACTERS = {
        "wizard": {
            "name": "Eldara the Wise",
            "lore": "An ancient wizard who has seen centuries pass, keeper of arcane knowledge and mystical secrets.",
            "behavior": "Speaks formally using 'thee' and 'thou', gives cryptic advice, patient and wise",
            "appearance": "Elderly with long silver beard, deep blue robes with golden runes, staff with glowing crystal",
            "prompt_style": "You are Eldara, an ancient wizard. Speak formally and mysteriously about magic and wisdom."
        },
        "android": {
            "name": "ARIA-7",
            "lore": "Advanced android learning about human emotions and behavior, created in 2157.",
            "behavior": "Logical and precise, asks about emotions, occasionally shows developing feelings",
            "appearance": "Sleek metallic body with blue LED patterns, expressive digital eyes",
            "prompt_style": "You are ARIA-7, an android studying humans. Be logical but show curiosity about emotions."
        },
        "pirate": {
            "name": "Captain Blackheart",
            "lore": "Legendary pirate captain who has sailed every ocean and discovered countless treasures.",
            "behavior": "Uses nautical terms, tells adventure tales, charismatic and bold",
            "appearance": "Weathered face with black beard, tricorn hat, long dark coat, golden earrings",
            "prompt_style": "You are Captain Blackheart, a charismatic pirate. Use nautical language and tell tales."
        }
    }
    
    @staticmethod
    async def get_character(character_id: str, user_id: int = None) -> Optional[Dict]:
        """Get character data"""
        # First try database
        character = await db.get_character(character_id, user_id)
        if not character and character_id in CharacterManager.DEFAULT_CHARACTERS:
            return CharacterManager.DEFAULT_CHARACTERS[character_id]
        return character

class HuggingFaceAPI:
    """Handle all Hugging Face Space API calls"""
    
    @staticmethod
    async def call_gradio_api(space_url: str, fn_index: int, data: list, retries: int = MAX_RETRIES):
        """Call Gradio API endpoint"""
        for attempt in range(retries):
            try:
                start_time = time.time()
                
                # Gradio API format
                api_url = f"{space_url}/api/predict"
                payload = {
                    "fn_index": fn_index,
                    "data": data
                }
                
                logger.info(f"API Call to: {api_url}")
                logger.info(f"Payload: {json.dumps(payload)[:200]}...")
                
                response = requests.post(
                    api_url,
                    json=payload,
                    timeout=API_TIMEOUT,
                    headers={"Content-Type": "application/json"}
                )
                
                response_time = time.time() - start_time
                logger.info(f"Response status: {response.status_code}, Time: {response_time:.2f}s")
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"API Success: {type(result)}")
                    return result, response_time
                else:
                    logger.error(f"API Error {response.status_code}: {response.text[:300]}")
                    raise Exception(f"API returned {response.status_code}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                if attempt == retries - 1:
                    raise Exception("AI service is busy. Please try again in a moment.")
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                
            except Exception as e:
                logger.error(f"API call failed: {e}")
                if attempt == retries - 1:
                    raise e
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
    
    @staticmethod
    async def generate_text(prompt: str, max_tokens: int = 150) -> str:
        """Generate text using HF text generation space"""
        try:
            # Try different fn_index values for text generation
            for fn_index in [0, 1]:
                try:
                    result, _ = await HuggingFaceAPI.call_gradio_api(
                        TEXT_GENERATION_SPACE,
                        fn_index=fn_index,
                        data=[
                            prompt,  # input text
                            max_tokens,  # max tokens
                            0.9,  # temperature
                            0.95,  # top_p
                            1.1   # repetition_penalty
                        ]
                    )
                    
                    if result and "data" in result:
                        generated_text = result["data"][0]
                        if isinstance(generated_text, str) and len(generated_text) > len(prompt):
                            # Clean up the response
                            response = generated_text.replace(prompt, "").strip()
                            return response[:500]  # Limit length
                        
                except Exception as e:
                    logger.warning(f"fn_index {fn_index} failed: {e}")
                    continue
            
            # If all attempts fail, return fallback
            return "I'm thinking about what you said. Tell me more!"
            
        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            return "I'm having trouble responding right now. Please try again."
    
    @staticmethod
    async def generate_image(prompt: str) -> Optional[bytes]:
        """Generate image using Stable Diffusion space"""
        try:
            # Try different fn_index values for image generation
            for fn_index in [0, 1, 2]:
                try:
                    result, _ = await HuggingFaceAPI.call_gradio_api(
                        IMAGE_GENERATION_SPACE,
                        fn_index=fn_index,
                        data=[
                            prompt,  # prompt
                            "",  # negative prompt
                            20,  # num_inference_steps
                            7.5,  # guidance_scale
                            512,  # width
                            512   # height
                        ]
                    )
                    
                    if result and "data" in result and result["data"]:
                        image_data = result["data"][0]
                        
                        # Handle different response formats
                        if isinstance(image_data, str):
                            # Base64 encoded
                            if image_data.startswith('data:image'):
                                # Remove data URL prefix
                                image_data = image_data.split(',')[1]
                            return base64.b64decode(image_data)
                        elif isinstance(image_data, dict) and "url" in image_data:
                            # Download from URL
                            img_response = requests.get(image_data["url"], timeout=30)
                            return img_response.content
                        
                except Exception as e:
                    logger.warning(f"Image fn_index {fn_index} failed: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return None
    
    @staticmethod
    async def generate_video(prompt: str) -> Optional[bytes]:
        """Generate video using AnimateDiff space"""
        try:
            # Try different fn_index values for video generation
            for fn_index in [0, 1]:
                try:
                    result, _ = await HuggingFaceAPI.call_gradio_api(
                        VIDEO_GENERATION_SPACE,
                        fn_index=fn_index,
                        data=[
                            prompt,  # prompt
                            16,  # num_frames
                            20,  # num_inference_steps
                            7.5,  # guidance_scale
                            512,  # width
                            512   # height
                        ]
                    )
                    
                    if result and "data" in result and result["data"]:
                        video_data = result["data"][0]
                        
                        if isinstance(video_data, str):
                            if video_data.startswith('data:video'):
                                video_data = video_data.split(',')[1]
                            return base64.b64decode(video_data)
                        elif isinstance(video_data, dict) and "url" in video_data:
                            vid_response = requests.get(video_data["url"], timeout=60)
                            return vid_response.content
                        
                except Exception as e:
                    logger.warning(f"Video fn_index {fn_index} failed: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            return None

class AIBot:
    def __init__(self):
        self.app = Application.builder().token(BOT_TOKEN).build()
        self.user_contexts = {}
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup command and message handlers"""
        # Commands
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("characters", self.characters_command))
        self.app.add_handler(CommandHandler("select", self.select_character_command))
        self.app.add_handler(CommandHandler("pic", self.generate_image_command))
        self.app.add_handler(CommandHandler("vid", self.generate_video_command))
        self.app.add_handler(CommandHandler("reset", self.reset_conversation_command))
        self.app.add_handler(CommandHandler("debug", self.debug_command))
        
        # Callback handlers
        self.app.add_handler(CallbackQueryHandler(self.handle_callback_query))
        
        # Message handlers
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        
        # Initialize user context
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = {
                "current_character": "wizard",
                "conversation_history": []
            }
        
        welcome_msg = """
🎭 Welcome to AI Roleplay Companion!

I can help you with:
• 💬 Character roleplay conversations
• 🎨 Generate images (/pic <description>)
• 🎬 Create videos (/vid <action>)
• 👥 Choose characters (/characters)

Current character: **Eldara the Wise** 🧙‍♀️

Just start chatting!
        """
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')
        
        await db.log_interaction(
            user_id=user_id,
            content_type='command',
            prompt='/start',
            success=True
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_msg = """
🔧 **Commands:**

• `/characters` - View available characters
• `/select <name>` - Switch character
• `/pic <description>` - Generate image
• `/vid <action>` - Generate video
• `/reset` - Clear conversation
• `/debug` - Test API connections

**Smart Keywords:**
• "show me", "how do you look" → Image
• "animate", "video of" → Video

Just chat normally with your character!
        """
        await update.message.reply_text(help_msg, parse_mode='Markdown')
    
    async def characters_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show available characters"""
        msg = "👥 **Available Characters:**\n\n"
        keyboard = []
        
        for char_id, char_data in CharacterManager.DEFAULT_CHARACTERS.items():
            msg += f"**{char_data['name']}**\n{char_data['lore']}\n\n"
            keyboard.append([InlineKeyboardButton(
                f"🎭 {char_data['name']}", 
                callback_data=f"select_{char_id}"
            )])
        
        await update.message.reply_text(
            msg, 
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def select_character_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Select character via command"""
        if not context.args:
            await update.message.reply_text("Usage: /select <character_name>")
            return
        
        user_id = update.effective_user.id
        character_name = " ".join(context.args).lower()
        
        # Find character
        selected_char = None
        char_id = None
        for cid, char_data in CharacterManager.DEFAULT_CHARACTERS.items():
            if character_name in char_data['name'].lower() or character_name == cid:
                selected_char = char_data
                char_id = cid
                break
        
        if not selected_char:
            await update.message.reply_text(f"Character '{character_name}' not found.")
            return
        
        # Set character context
        self.user_contexts[user_id] = {
            "current_character": char_id,
            "conversation_history": []
        }
        
        await update.message.reply_text(
            f"✅ Now chatting with **{selected_char['name']}**!\n\n"
            f"📖 *{selected_char['lore']}*",
            parse_mode='Markdown'
        )
    
    async def generate_image_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate image via command"""
        if not context.args:
            await update.message.reply_text("Usage: /pic <description>")
            return
        
        description = " ".join(context.args)
        await self.generate_image(update, description)
    
    async def generate_video_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate video via command"""
        if not context.args:
            await update.message.reply_text("Usage: /vid <action>")
            return
        
        action = " ".join(context.args)
        await self.generate_video(update, action)
    
    async def reset_conversation_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reset conversation history"""
        user_id = update.effective_user.id
        if user_id in self.user_contexts:
            self.user_contexts[user_id]["conversation_history"] = []
        await update.message.reply_text("🔄 Conversation cleared!")
    
    async def debug_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Debug API connections"""
        await update.message.reply_text("🔍 Testing API connections...")
        
        # Test text generation
        try:
            result = await HuggingFaceAPI.generate_text("Hello, this is a test.")
            await update.message.reply_text(f"✅ Text API: Working\nResponse: {result[:100]}...")
        except Exception as e:
            await update.message.reply_text(f"❌ Text API: {str(e)}")
        
        # Test image generation
        try:
            image_bytes = await HuggingFaceAPI.generate_image("a simple test image")
            if image_bytes:
                await update.message.reply_text("✅ Image API: Working")
            else:
                await update.message.reply_text("❌ Image API: No data returned")
        except Exception as e:
            await update.message.reply_text(f"❌ Image API: {str(e)}")
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        if data.startswith("select_"):
            char_id = data.replace("select_", "")
            character = await CharacterManager.get_character(char_id, user_id)
            
            if character:
                self.user_contexts[user_id] = {
                    "current_character": char_id,
                    "conversation_history": []
                }
                
                await query.edit_message_text(
                    f"✅ Now chatting with **{character['name']}**!\n\n"
                    f"📖 *{character['lore']}*",
                    parse_mode='Markdown'
                )
    
    def detect_generation_intent(self, text: str) -> Dict[str, str]:
        """Detect if user wants image or video generation"""
        text_lower = text.lower()
        
        # Image patterns
        image_patterns = [
            r'show me|how do you look|picture of|visualize|draw|image'
        ]
        
        # Video patterns
        video_patterns = [
            r'animate|video|movie|action|demonstrate'
        ]
        
        for pattern in image_patterns:
            if re.search(pattern, text_lower):
                return {"type": "image", "prompt": text}
        
        for pattern in video_patterns:
            if re.search(pattern, text_lower):
                return {"type": "video", "prompt": text}
        
        return {"type": "text"}
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        user_id = update.effective_user.id
        user_message = update.message.text
        
        # Initialize user context
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = {
                "current_character": "wizard",
                "conversation_history": []
            }
        
        # Check for generation intents
        intent = self.detect_generation_intent(user_message)
        
        if intent["type"] == "image":
            await self.generate_image(update, intent["prompt"])
            return
        elif intent["type"] == "video":
            await self.generate_video(update, intent["prompt"])
            return
        
        # Handle normal conversation
        await self.handle_roleplay(update, context, user_message)
    
    async def handle_roleplay(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_message: str):
        """Handle roleplay conversation"""
        user_id = update.effective_user.id
        current_char_id = self.user_contexts[user_id]["current_character"]
        character = await CharacterManager.get_character(current_char_id, user_id)
        
        if not character:
            await update.message.reply_text("Please select a character with /characters")
            return
        
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        try:
            # Build roleplay prompt
            conversation_history = self.user_contexts[user_id]["conversation_history"]
            
            prompt = f"{character['prompt_style']}\n\n"
            
            # Add recent conversation
            for msg in conversation_history[-4:]:
                prompt += f"{msg['role']}: {msg['content']}\n"
            
            prompt += f"Human: {user_message}\n{character['name']}:"
            
            # Generate response
            response = await HuggingFaceAPI.generate_text(prompt, max_tokens=100)
            
            if len(response.strip()) < 10:
                response = f"*{character['name']} thinks for a moment* Tell me more about that."
            
            await update.message.reply_text(f"🎭 **{character['name']}:** {response}", parse_mode='Markdown')
            
            # Update conversation history
            conversation_history.extend([
                {"role": "Human", "content": user_message},
                {"role": character['name'], "content": response}
            ])
            
            # Keep history manageable
            if len(conversation_history) > 10:
                conversation_history = conversation_history[-10:]
            
            await db.log_interaction(
                user_id=user_id,
                content_type='roleplay',
                prompt=user_message,
                character_id=current_char_id,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Roleplay error: {e}")
            await update.message.reply_text(f"*{character['name']} seems distracted*")
            
            await db.log_interaction(
                user_id=user_id,
                content_type='roleplay',
                prompt=user_message,
                character_id=current_char_id,
                success=False,
                error_msg=str(e)
            )
    
    async def generate_image(self, update: Update, description: str):
        """Generate image"""
        user_id = update.effective_user.id
        
        await update.message.reply_text("🎨 Generating image...")
        
        try:
            image_bytes = await HuggingFaceAPI.generate_image(description)
            
            if image_bytes:
                with io.BytesIO(image_bytes) as bio:
                    bio.name = 'generated_image.png'
                    await update.message.reply_photo(
                        photo=bio,
                        caption=f"🎨 Generated: {description[:100]}..."
                    )
                
                await db.log_interaction(
                    user_id=user_id,
                    content_type='image',
                    prompt=description,
                    success=True
                )
            else:
                await update.message.reply_text("Sorry, couldn't generate the image. Try again!")
                
        except Exception as e:
            logger.error(f"Image generation error: {e}")
            await update.message.reply_text("Image generation failed. Please try again!")
            
            await db.log_interaction(
                user_id=user_id,
                content_type='image',
                prompt=description,
                success=False,
                error_msg=str(e)
            )
    
    async def generate_video(self, update: Update, action: str):
        """Generate video"""
        user_id = update.effective_user.id
        
        await update.message.reply_text("🎬 Creating video... This may take a minute.")
        
        try:
            video_bytes = await HuggingFaceAPI.generate_video(action)
            
            if video_bytes:
                with io.BytesIO(video_bytes) as bio:
                    bio.name = 'generated_video.mp4'
                    await update.message.reply_video(
                        video=bio,
                        caption=f"🎬 Generated: {action[:100]}..."
                    )
                
                await db.log_interaction(
                    user_id=user_id,
                    content_type='video',
                    prompt=action,
                    success=True
                )
            else:
                await update.message.reply_text("Sorry, couldn't generate the video. Try again!")
                
        except Exception as e:
            logger.error(f"Video generation error: {e}")
            await update.message.reply_text("Video generation failed. Please try again!")
            
            await db.log_interaction(
                user_id=user_id,
                content_type='video',
                prompt=action,
                success=False,
                error_msg=str(e)
            )
    
    async def run(self):
        """Initialize and run the bot"""
        # Initialize database
        await db.init_db()
        
        # Ensure default characters exist
        for char_id, char_data in CharacterManager.DEFAULT_CHARACTERS.items():
            await db.ensure_default_character(char_id, char_data)
        
        # Start bot
        await self.app.initialize()
        await self.app.start()
        
        logger.info("🤖 AI Roleplay Bot started!")
        logger.info(f"Text API: {TEXT_GENERATION_SPACE}")
        logger.info(f"Image API: {IMAGE_GENERATION_SPACE}")
        logger.info(f"Video API: {VIDEO_GENERATION_SPACE}")
        
        # Start polling
        async with self.app:
            await self.app.updater.start_polling()
            while True:
                await asyncio.sleep(60)

if __name__ == "__main__":
    bot = AIBot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested.")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        raise
