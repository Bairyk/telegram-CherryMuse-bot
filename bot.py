#!/usr/bin/env python3
"""
AI Roleplay Telegram Bot - Enhanced Implementation with Proper Logging
Features: Character management, comprehensive logging, real HuggingFace API integration
"""

import asyncio
import time
import json
import re
import base64
import io
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

# Setup logging
logger = setup_logging()

class CharacterManager:
    """Manage roleplay characters with persistent storage"""
    
    DEFAULT_CHARACTERS = {
        "wizard": {
            "name": "Eldara the Wise",
            "lore": "An ancient wizard who has seen centuries pass, keeper of arcane knowledge and mystical secrets. Lives in a tower filled with floating books and magical artifacts.",
            "behavior": "Speaks formally using 'thee' and 'thou', often references ancient events, gives cryptic advice, patient and wise but sometimes mysterious",
            "appearance": "Elderly with long silver beard, deep blue robes with golden runes, staff topped with a glowing crystal, piercing violet eyes",
            "creator_id": 0,
            "public": True
        },
        "android": {
            "name": "ARIA-7",
            "lore": "Advanced android with developing consciousness, created in 2157 to study human emotions and behavior. Has access to vast databases but struggles with feelings.",
            "behavior": "Logical and precise speech, asks questions about human emotions, occasionally glitches with emotional responses, curious and analytical",
            "appearance": "Sleek metallic body with blue LED patterns, expressive digital eyes, graceful movements, sometimes sparks when processing complex emotions",
            "creator_id": 0,
            "public": True
        },
        "pirate": {
            "name": "Captain Blackheart",
            "lore": "Legendary pirate captain who has sailed every ocean and discovered countless treasures. Commands the ship 'Crimson Storm' with a crew of loyal rogues.",
            "behavior": "Uses nautical terms, tells grand tales of adventure, charismatic and bold, occasionally shows a softer side, loves freedom above all",
            "appearance": "Weathered face with distinctive black beard, tricorn hat with feather, long dark coat, golden earrings, confident swagger",
            "creator_id": 0,
            "public": True
        },
        "vampire": {
            "name": "Count Dracul",
            "lore": "Ancient vampire lord who has lived for over 800 years, dwelling in a Gothic castle. Has witnessed the rise and fall of empires, collects rare books and art.",
            "behavior": "Eloquent and old-fashioned speech, romantically dramatic, occasionally shows vulnerability, values honor and etiquette, nocturnal by nature",
            "appearance": "Pale aristocratic features, long black hair, elegant dark clothing, piercing red eyes, moves with supernatural grace",
            "creator_id": 0,
            "public": True
        },
        "explorer": {
            "name": "Captain Nova Sterling",
            "lore": "Fearless space explorer and starship captain who leads missions to uncharted galaxies. Has discovered three new civilizations and countless alien species.",
            "behavior": "Confident and inspiring, uses space terminology, optimistic about the future, natural leader, always ready for adventure",
            "appearance": "Athletic build in sleek space uniform, short auburn hair, bright green eyes, confident posture, high-tech equipment",
            "creator_id": 0,
            "public": True
        }
    }
    
    @staticmethod
    async def get_character(character_id: str, user_id: int = None) -> Optional[Dict]:
        """Get character data from database or defaults"""
        character = await db.get_character(character_id, user_id)
        if not character and character_id in CharacterManager.DEFAULT_CHARACTERS:
            return CharacterManager.DEFAULT_CHARACTERS[character_id]
        return character
    
    @staticmethod
    async def list_available_characters(user_id: int) -> List[Dict]:
        """List all available characters for user"""
        # Get user's custom characters
        custom_chars = await db.get_user_characters(user_id)
        
        # Add default characters
        all_chars = []
        for char_id, char_data in CharacterManager.DEFAULT_CHARACTERS.items():
            all_chars.append({"id": char_id, **char_data})
        
        # Add custom characters
        for char in custom_chars:
            all_chars.append(char)
        
        return all_chars

class AIBot:
    def __init__(self):
        logger.info("Initializing AI Bot...")
        self.app = Application.builder().token(BOT_TOKEN).build()
        self.user_contexts = {}  # Store conversation contexts
        self.hf_spaces_available = bool(HF_SPACES)
        logger.info(f"HuggingFace Spaces available: {self.hf_spaces_available}")
        self.setup_handlers()
        logger.info("AI Bot initialized successfully")
    
    def setup_handlers(self):
        """Setup command and message handlers"""
        # Commands
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("characters", self.characters_command))
        self.app.add_handler(CommandHandler("select", self.select_character_command))
        self.app.add_handler(CommandHandler("create", self.create_character_command))
        self.app.add_handler(CommandHandler("pic", self.generate_image_command))
        self.app.add_handler(CommandHandler("vid", self.generate_video_command))
        self.app.add_handler(CommandHandler("feedback", self.feedback_command))
        self.app.add_handler(CommandHandler("stats", self.stats_command))
        self.app.add_handler(CommandHandler("reset", self.reset_conversation_command))
        
        # Callback handlers for inline keyboards
        self.app.add_handler(CallbackQueryHandler(self.handle_callback_query))
        
        # Message handlers
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        self.app.add_handler(MessageHandler(filters.PHOTO, self.handle_image))
        self.app.add_handler(MessageHandler(filters.VIDEO, self.handle_video))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        logger.info(f"User {user_id} (@{username}) started the bot")

        # Initialize user context
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = {
                "current_character": "wizard",
                "conversation_history": []
            }
            logger.info(f"Created new context for user {user_id}")
        
        welcome_msg = """
🎭 Welcome to your AI Roleplay Companion!

I can help you with:
- 💬 Character roleplay conversations
- 🎨 Generate character images (/pic)
- 🎬 Create character animations (/vid)
- 👥 Choose from characters (/characters)
- ⚡ Create custom characters (/create)

Current character: **Eldara the Wise** 🧙‍♀️

Just start chatting, or use /help for more commands!
        """
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')
        
        try:
            await db.log_interaction(
                user_id=user_id,
                content_type='command',
                prompt='/start',
                success=True
            )
            logger.info(f"Logged /start interaction for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to log interaction for user {user_id}: {e}")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_msg = """
🔧 **AI Roleplay Companion Commands:**

**Character Management:**
- `/characters` - View all available characters
- `/select <character>` - Switch to a character
- `/create` - Create a custom character (guided process)
- `/reset` - Clear conversation history

**Generation Commands:**
- `/pic [description]` - Generate character image
- `/vid [action]` - Generate character animation

**Smart Keywords** (work in any message):
- "show me", "how do you look" → Generates character image
- "animate", "video of" → Generates character animation  
- "picture this", "visualize" → Scene generation

**Other Commands:**
- `/feedback <message>` - Send feedback
- `/stats` - View usage statistics

**Tips:**
✨ Just chat normally with your selected character!
📝 Be descriptive for better image/video results
🎭 Characters remember your conversation
        """
        await update.message.reply_text(help_msg, parse_mode='Markdown')
    
    async def characters_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show available characters with selection buttons"""
        user_id = update.effective_user.id
        characters = await CharacterManager.list_available_characters(user_id)
        
        msg = "👥 **Available Characters:**\n\n"
        keyboard = []
        
        for i, char in enumerate(characters[:10]):  # Limit to 10 for UI
            char_id = char.get('id', f'custom_{char.get("name", "").lower().replace(" ", "_")}')
            creator = "Default" if char.get('public', False) else "Custom"
            msg += f"**{char['name']}** ({creator})\n{char['lore'][:100]}...\n\n"
            
            keyboard.append([InlineKeyboardButton(
                f"🎭 {char['name']}", 
                callback_data=f"select_{char_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("➕ Create New Character", callback_data="create_new")])
        
        await update.message.reply_text(
            msg, 
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def select_character_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Select character via command"""
        if not context.args:
            await update.message.reply_text("Usage: `/select <character_name>`\nUse `/characters` to see available characters.")
            return
        
        user_id = update.effective_user.id
        character_name = " ".join(context.args).lower()
        
        # Find character by name or ID
        characters = await CharacterManager.list_available_characters(user_id)
        selected_char = None
        
        for char in characters:
            if (character_name in char['name'].lower() or 
                character_name == char.get('id', '')):
                selected_char = char
                break
        
        if not selected_char:
            await update.message.reply_text(f"Character '{character_name}' not found. Use /characters to see available characters.")
            return
        
        # Set character context
        self.user_contexts[user_id] = {
            "current_character": selected_char.get('id', character_name),
            "conversation_history": []
        }
        
        await update.message.reply_text(
            f"✅ Now chatting with **{selected_char['name']}**!\n\n"
            f"📖 *{selected_char['lore'][:150]}...*",
            parse_mode='Markdown'
        )
        
        await db.log_interaction(
            user_id=user_id,
            content_type='character_select',
            prompt=selected_char['name'],
            success=True
        )
    
    async def create_character_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start custom character creation process"""
        user_id = update.effective_user.id
        
        # Check if user already has max characters (limit to 5 custom)
        user_chars = await db.get_user_characters(user_id)
        if len(user_chars) >= 5:
            await update.message.reply_text("You can only create up to 5 custom characters. Delete one first if needed.")
            return
        
        # Start creation process
        self.user_contexts[user_id] = {
            **self.user_contexts.get(user_id, {}),
            "creating_character": {
                "step": "name",
                "data": {}
            }
        }
        
        await update.message.reply_text(
            "🎨 **Creating a Custom Character!**\n\n"
            "Let's start with the basics:\n"
            "**Step 1/4:** What's your character's name?"
        )
    
    async def generate_image_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate character image via command"""
        user_id = update.effective_user.id
        description = " ".join(context.args) if context.args else ""
        
        current_char_id = self.user_contexts.get(user_id, {}).get("current_character", "wizard")
        character = await CharacterManager.get_character(current_char_id, user_id)
        
        if not character:
            await update.message.reply_text("No character selected. Use /characters to choose one.")
            return
        
        await self.generate_character_image(update, character, description)
    
    async def generate_video_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate character video via command"""
        user_id = update.effective_user.id
        action = " ".join(context.args) if context.args else "talking"
        
        current_char_id = self.user_contexts.get(user_id, {}).get("current_character", "wizard")
        character = await CharacterManager.get_character(current_char_id, user_id)
        
        if not character:
            await update.message.reply_text("No character selected. Use /characters to choose one.")
            return
        
        await self.generate_character_video(update, character, action)
    
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
                    f"📖 *{character['lore'][:150]}...*\n\n"
                    f"Just start chatting!",
                    parse_mode='Markdown'
                )
        
        elif data == "create_new":
            await query.edit_message_text("Use the /create command to create a new character!")
    
    def extract_generation_intent(self, text: str) -> Dict[str, Any]:
        """Extract image/video generation intent from text"""
        text_lower = text.lower()
        
        # Image generation patterns
        image_patterns = [
            r'show me|how do you look|what do you look like|picture of you|visualize yourself',
            r'picture this|visualize this|show this|image of',
            r'draw|paint|illustrate|generate.*image|create.*picture'
        ]
        
        # Video generation patterns  
        video_patterns = [
            r'animate|video|movie|animation|moving|motion',
            r'show.*action|demonstrate|perform|act out'
        ]
        
        for pattern in image_patterns:
            if re.search(pattern, text_lower):
                return {"type": "image", "description": text}
        
        for pattern in video_patterns:
            if re.search(pattern, text_lower):
                return {"type": "video", "action": text}
        
        return {"type": "none"}
    
    def extract_theme(self, text: str) -> Optional[str]:
        """Extract theme from user message"""
        themes = {
            r'fantasy|dragon|magic|wizard|elf|mystical': 'fantasy',
            r'sci-?fi|space|robot|alien|future|android': 'sci-fi',
            r'romance|love|relationship|romantic': 'romance',
            r'horror|scary|ghost|dark|fear|spooky': 'horror',
            r'adventure|quest|journey|explore|treasure': 'adventure',
            r'anime|manga|kawaii|japanese|tsundere': 'anime',
            r'pirate|ship|ocean|sea|sailing|treasure': 'pirate',
            r'vampire|gothic|aristocrat|night|blood': 'vampire'
        }
        
        text_lower = text.lower()
        for pattern, theme in themes.items():
            if re.search(pattern, text_lower):
                return theme
        return 'general'
    
    async def call_hf_space_api(self, space_type: str, payload: dict, retries: int = MAX_RETRIES) -> tuple:
        """Call HuggingFace Space API with proper error handling and logging"""
        if not self.hf_spaces_available:
            logger.warning("HuggingFace Spaces not configured")
            raise Exception("AI services are temporarily unavailable. Please contact admin.")

        space_url = HF_SPACES.get(space_type)
        if not space_url:
            raise Exception(f"Space type {space_type} not configured")

        api_url = f"{space_url}/api/predict"
        headers = {
            "Content-Type": "application/json"
        }

        logger.info(f"Calling HF Space: {space_type} ({space_url}) with payload size: {len(str(payload))}")

        for attempt in range(retries):
            try:
                start_time = time.time()
                logger.debug(f"Attempt {attempt + 1}/{retries} for {space_type}")

                response = requests.post(
                    api_url,
                    json={"data": [payload]},
                    timeout=120,
                    headers=headers
                )

                response_time = time.time() - start_time
                logger.info(f"HF API response time: {response_time:.2f}s, Status: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Successful Space call to {space_type} in {response_time:.2f}s")
                    return result, response_time
                elif response.status_code == 503:
                    logger.warning(f"Space {space_type} is loading, attempt {attempt + 1}/{retries}")
                    if attempt == retries - 1:
                        raise Exception(f"Space {space_type} is currently loading. Please try again in a few minutes.")
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                elif response.status_code == 429:
                    logger.warning(f"Rate limit hit for {space_type}, attempt {attempt + 1}/{retries}")
                    if attempt == retries - 1:
                        raise Exception("Rate limit exceeded. Please try again later.")
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1) * 2)  # Longer delay for rate limits
                else:
                    logger.error(f"API error {response.status_code}: {response.text[:200]}")
                    raise Exception(f"AI service error ({response.status_code}). Please try again.")

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout for {space_type} attempt {attempt + 1}/{retries}")
                if attempt == retries - 1:
                    raise Exception("AI service timeout. Please try again in a moment.")
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
            except requests.exceptions.ConnectionError:
                logger.error(f"Connection error for {space_type} attempt {attempt + 1}/{retries}")
                if attempt == retries - 1:
                    raise Exception("Connection error. Please check your internet connection.")
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
            except Exception as e:
                logger.error(f"Unexpected error for {space_type}: {str(e)}")
                if attempt == retries - 1:
                    raise e
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced text handling with character roleplay and smart generation"""
        user_id = update.effective_user.id
        user_message = update.message.text
        
        # Initialize user context if needed
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = {
                "current_character": "wizard",
                "conversation_history": []
            }
        
        # Handle character creation process
        if "creating_character" in self.user_contexts[user_id]:
            await self.handle_character_creation(update, context)
            return
        
        # Get current character
        current_char_id = self.user_contexts[user_id]["current_character"]
        character = await CharacterManager.get_character(current_char_id, user_id)
        
        if not character:
            await update.message.reply_text("Something went wrong. Please use /characters to select a character.")
            return
        
        # Check for generation intents
        generation_intent = self.extract_generation_intent(user_message)
        
        if generation_intent["type"] == "image":
            await self.generate_character_image(update, character, generation_intent["description"])
            return
        elif generation_intent["type"] == "video":
            await self.generate_character_video(update, character, generation_intent["action"])
            return
        
        # Handle normal roleplay conversation
        await self.handle_roleplay_conversation(update, context, character, user_message)
    
    async def handle_roleplay_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                        character: Dict, user_message: str):
        """Handle roleplay conversation with character"""
        user_id = update.effective_user.id
        theme = self.extract_theme(user_message)
        
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        try:
            # Build conversation context
            conversation_history = self.user_contexts[user_id]["conversation_history"]
            
            # Prepare character context for AI
            character_prompt = f"""You are {character['name']}. 

LORE: {character['lore']}
BEHAVIOR: {character['behavior']}
APPEARANCE: {character['appearance']}

IMPORTANT: Stay in character at all times. Respond as {character['name']} would based on their lore and behavior. Be engaging and interactive.

Recent conversation:"""
            
            # Add recent conversation history
            for msg in conversation_history[-6:]:  # Last 6 messages for context
                character_prompt += f"\n{msg['role']}: {msg['content']}"
            
            character_prompt += f"\nHuman: {user_message}\n{character['name']}:"
            
            # Call text generation using HuggingFace Space
            logger.info(f"Generating roleplay response for user {user_id} with character {character['name']}")

            result, response_time = await self.call_hf_space_api(
                'text',
                {
                    "inputs": character_prompt,
                    "parameters": {
                        "max_new_tokens": 150,
                        "temperature": 0.9,
                        "top_p": 0.95,
                        "repetition_penalty": 1.1,
                        "do_sample": True
                    }
                }
            )
            
            # Extract response from HuggingFace Space API
            if result and "data" in result and len(result["data"]) > 0:
                generated_text = result["data"][0]
                logger.debug(f"Generated text length: {len(generated_text)}")

                # Clean up the response
                response = generated_text.replace(character_prompt, "").strip()
                response = response.split("\n")[0].strip()

                if len(response) < 10:
                    response = f"*{character['name']} pauses thoughtfully* Tell me more about that."
                    logger.info(f"Generated short response for {character['name']}, using fallback")
            else:
                logger.warning(f"Unexpected API response format: {result}")
                response = f"*{character['name']} seems deep in thought*"
            
            # Send response
            logger.info(f"Sending roleplay response from {character['name']} to user {user_id}")
            await update.message.reply_text(f"🎭 **{character['name']}:** {response}", parse_mode='Markdown')
            
            # Update conversation history
            conversation_history.extend([
                {"role": "Human", "content": user_message},
                {"role": character['name'], "content": response}
            ])
            
            # Keep history manageable (last 20 messages)
            if len(conversation_history) > 20:
                conversation_history = conversation_history[-20:]
            
            self.user_contexts[user_id]["conversation_history"] = conversation_history
            
            # Log interaction
            await db.log_interaction(
                user_id=user_id,
                content_type='roleplay',
                prompt=user_message,
                character_id=self.user_contexts[user_id]["current_character"],
                theme=theme,
                success=True,
                response_time=response_time
            )
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in roleplay conversation for user {user_id}: {error_msg}")

            if "loading" in error_msg.lower() or "503" in error_msg:
                await update.message.reply_text(f"🤖 {character['name']} is waking up... Please try again in a moment!")
            elif "rate limit" in error_msg.lower() or "429" in error_msg:
                await update.message.reply_text(f"🤖 {character['name']} needs a moment to rest... Please try again in a few minutes!")
            elif "unavailable" in error_msg.lower():
                await update.message.reply_text(f"🤖 {character['name']} is currently unavailable. The AI service might be down.")
            else:
                await update.message.reply_text(f"*{character['name']} seems distracted and doesn't respond clearly*")

            try:
                await db.log_interaction(
                    user_id=user_id,
                    content_type='roleplay',
                    prompt=user_message,
                    character_id=self.user_contexts[user_id]["current_character"],
                    theme=theme,
                    success=False,
                    error_msg=error_msg
                )
            except Exception as log_error:
                logger.error(f"Failed to log error interaction: {log_error}")
    
    async def generate_character_image(self, update: Update, character: Dict, description: str = ""):
        """Generate character image using Stable Diffusion Space"""
        user_id = update.effective_user.id
        
        await update.message.reply_text(f"🎨 Generating image of {character['name']}...")
        
        try:
            # Build image prompt
            if description and "you look" not in description.lower():
                prompt = f"{character['appearance']}, {description}, high quality, detailed artwork"
            else:
                prompt = f"{character['appearance']}, portrait, high quality, detailed artwork, fantasy art"
            
            # Call image generation using HuggingFace Space
            logger.info(f"Generating image for user {user_id} with prompt: {prompt[:50]}...")

            result, response_time = await self.call_hf_space_api(
                'image',
                {
                    "inputs": prompt,
                    "parameters": {
                        "negative_prompt": "blurry, low quality, distorted, nsfw",
                        "num_inference_steps": 20,
                        "guidance_scale": 7.5,
                        "width": 512,
                        "height": 512
                    }
                }
            )
            
            # Handle HuggingFace Space image response
            if result and "data" in result:
                logger.info(f"Received image data from Space")
                image_data = result["data"][0]

                # Handle different image formats from Spaces
                if isinstance(image_data, str) and image_data.startswith('data:image'):
                    # Base64 data URI
                    header, encoded = image_data.split(',', 1)
                    image_bytes = base64.b64decode(encoded)
                    image = Image.open(io.BytesIO(image_bytes))
                    logger.info(f"Successfully loaded image: {image.size}")
                elif isinstance(image_data, str):
                    # Plain base64
                    image_bytes = base64.b64decode(image_data)
                    image = Image.open(io.BytesIO(image_bytes))
                    logger.info(f"Successfully loaded image: {image.size}")
                else:
                    logger.error(f"Unexpected image response format: {type(image_data)}")
                    raise Exception("Unexpected image format from Space")
                
                # Send image
                with io.BytesIO() as bio:
                    image.save(bio, 'PNG')
                    bio.seek(0)
                    
                    caption = f"🎨 **{character['name']}**\n📝 {prompt[:100]}...\n⏱️ Generated in {response_time:.1f}s"
                    await update.message.reply_photo(photo=bio, caption=caption, parse_mode='Markdown')
                
                try:
                    await db.log_interaction(
                        user_id=user_id,
                        content_type='image',
                        prompt=prompt,
                        character_id=character.get('id', 'unknown'),
                        theme=self.extract_theme(prompt),
                        success=True,
                        response_time=response_time
                    )
                    logger.info(f"Logged successful image generation for user {user_id}")
                except Exception as log_error:
                    logger.error(f"Failed to log image interaction: {log_error}")
            else:
                raise Exception("No image data returned from API")
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error generating image for user {user_id}: {error_msg}")

            if "loading" in error_msg.lower():
                await update.message.reply_text(f"🎨 The image generator is starting up... Please try again in a few minutes!")
            elif "rate limit" in error_msg.lower():
                await update.message.reply_text(f"🎨 Too many image requests right now. Please try again in a few minutes!")
            else:
                await update.message.reply_text(f"🎨 Sorry, I couldn't generate an image of {character['name']} right now. Please try again later!")

            try:
                await db.log_interaction(
                    user_id=user_id,
                    content_type='image',
                    prompt=description,
                    character_id=character.get('id', 'unknown'),
                    success=False,
                    error_msg=error_msg
                )
            except Exception as log_error:
                logger.error(f"Failed to log image error: {log_error}")
    
    async def generate_character_video(self, update: Update, character: Dict, action: str = "talking"):
        """Generate character video using AnimateDiff Space"""
        user_id = update.effective_user.id
        
        await update.message.reply_text(f"🎬 Creating animation of {character['name']}... This may take up to 2 minutes.")
        
        try:
            # Build video prompt
            prompt = f"{character['appearance']}, {action}, smooth animation, high quality"
            
            # Call Video Generation using HuggingFace Space
            logger.info(f"Generating video for user {user_id} with prompt: {prompt[:50]}...")
            logger.warning("Video generation through HF Spaces has limitations - may not work reliably")

            result, response_time = await self.call_hf_space_api(
                'video',
                {
                    "inputs": prompt,
                    "parameters": {
                        "num_inference_steps": 20,
                        "guidance_scale": 7.5,
                        "num_frames": 16,
                        "height": 320,
                        "width": 576
                    }
                }
            )
            
            # Handle video response from HuggingFace Space
            if result and "data" in result:
                logger.info(f"Received video data from Space")
                video_data = result["data"][0]

                if isinstance(video_data, str):
                    # Assume base64 encoded video
                    video_bytes = base64.b64decode(video_data)
                    with io.BytesIO(video_bytes) as bio:
                        bio.name = f'{character["name"]}_animation.mp4'

                        caption = f"🎬 **{character['name']}** - {action}\n⏱️ Generated in {response_time:.1f}s"
                        await update.message.reply_video(video=bio, caption=caption, parse_mode='Markdown')
                        logger.info(f"Successfully sent video to user {user_id}")
                else:
                    logger.error(f"Unexpected video response format: {type(video_data)}")
                    raise Exception("Unexpected video format from Space")
                
                await db.log_interaction(
                    user_id=user_id,
                    content_type='video',
                    prompt=f"{action} - {prompt}",
                    character_id=character.get('id', 'unknown'),
                    theme=self.extract_theme(prompt),
                    success=True,
                    response_time=response_time
                )
            else:
                raise Exception("No video data returned from API")
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error generating video for user {user_id}: {error_msg}")

            # Video generation is currently experimental/limited
            await update.message.reply_text(
                f"🎬 Video generation is currently experimental and may not work reliably. "
                f"The HuggingFace Space might be down or overloaded. "
                f"Please try image generation instead!\n\nError: {error_msg[:100]}..."
            )

            try:
                await db.log_interaction(
                    user_id=user_id,
                    content_type='video',
                    prompt=action,
                    character_id=character.get('id', 'unknown'),
                    success=False,
                    error_msg=error_msg
                )
            except Exception as log_error:
                logger.error(f"Failed to log video error: {log_error}")
    
    async def handle_character_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the character creation process"""
        user_id = update.effective_user.id
        creation_data = self.user_contexts[user_id]["creating_character"]
        user_input = update.message.text
        
        step = creation_data["step"]
        char_data = creation_data["data"]
        
        if step == "name":
            char_data["name"] = user_input
            creation_data["step"] = "lore"
            await update.message.reply_text(
                f"✅ Character name: **{user_input}**\n\n"
                "**Step 2/4:** Tell me their background story/lore (2-3 sentences):"
            )
        
        elif step == "lore":
            char_data["lore"] = user_input
            creation_data["step"] = "behavior"
            await update.message.reply_text(
                "✅ Lore saved!\n\n"
                "**Step 3/4:** Describe their personality and how they speak:"
            )
        
        elif step == "behavior":
            char_data["behavior"] = user_input
            creation_data["step"] = "appearance"
            await update.message.reply_text(
                "✅ Personality saved!\n\n"
                "**Step 4/4:** Describe their physical appearance:"
            )
        
        elif step == "appearance":
            char_data["appearance"] = user_input
            
            # Save character to database
            char_id = await db.create_character(
                user_id=user_id,
                name=char_data["name"],
                lore=char_data["lore"],
                behavior=char_data["behavior"],
                appearance=char_data["appearance"]
            )
            
            if char_id:
                # Clean up creation process
                del self.user_contexts[user_id]["creating_character"]
                
                await update.message.reply_text(
                    f"🎉 **Character Created Successfully!**\n\n"
                    f"**{char_data['name']}** is now available!\n"
                    f"Use `/select {char_data['name']}` to start chatting with them!",
                    parse_mode='Markdown'
                )
                
                await db.log_interaction(
                    user_id=user_id,
                    content_type='character_creation',
                    prompt=char_data["name"],
                    success=True
                )
            else:
                await update.message.reply_text("Sorry, there was an error creating your character. Please try again.")
    
    async def reset_conversation_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reset conversation history"""
        user_id = update.effective_user.id
        
        if user_id in self.user_contexts:
            self.user_contexts[user_id]["conversation_history"] = []
        
        await update.message.reply_text("🔄 Conversation history cleared! Starting fresh.")
        
        await db.log_interaction(
            user_id=user_id,
            content_type='command',
            prompt='/reset',
            success=True
        )
    
    async def feedback_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /feedback command"""
        if not context.args:
            await update.message.reply_text("Please provide feedback: `/feedback <your message>`")
            return
        
        feedback_text = " ".join(context.args)
        
        await db.log_interaction(
            user_id=update.effective_user.id,
            content_type='feedback',
            prompt=feedback_text,
            success=True
        )
        
        await update.message.reply_text("Thank you for your feedback! 🙏")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show comprehensive statistics"""
        try:
            user_id = update.effective_user.id
            
            # Get various statistics
            popular_themes = await db.get_popular_themes(days=7)
            popular_characters = await db.get_popular_characters(days=7)
            user_stats = await db.get_user_stats(user_id)
            error_stats = await db.get_error_stats(days=1)
            
            stats_msg = "📊 **Bot Statistics**\n\n"
            
            # Popular themes
            if popular_themes:
                stats_msg += "🎭 **Popular Themes (7 days):**\n"
                for theme, count in popular_themes[:5]:
                    stats_msg += f"• {theme.title()}: {count} requests\n"
                stats_msg += "\n"
            
            # Popular characters
            if popular_characters:
                stats_msg += "👥 **Active Characters (7 days):**\n"
                for char_id, count in popular_characters[:5]:
                    stats_msg += f"• {char_id.title()}: {count} conversations\n"
                stats_msg += "\n"
            
            # User personal stats
            if user_stats:
                stats_msg += f"📈 **Your Activity:**\n"
                stats_msg += f"• Total interactions: {user_stats['total_interactions']}\n"
                stats_msg += f"• Success rate: {user_stats['success_rate']:.1%}\n"
                stats_msg += f"• Avg response time: {user_stats['avg_response_time']:.1f}s\n\n"
            
            # Recent errors (for debugging)
            if error_stats:
                stats_msg += "⚠️ **Recent Issues:**\n"
                for content_type, error_count in error_stats:
                    stats_msg += f"• {content_type}: {error_count} errors\n"
            
            await update.message.reply_text(stats_msg or "No data available yet!", parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text("Stats temporarily unavailable.")
    
    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle uploaded images - generate character response"""
        user_id = update.effective_user.id
        
        # Get current character
        current_char_id = self.user_contexts.get(user_id, {}).get("current_character", "wizard")
        character = await CharacterManager.get_character(current_char_id, user_id)
        
        if not character:
            await update.message.reply_text("No character selected. Use /characters to choose one.")
            return
        
        caption = update.message.caption or "What do you think of this image?"
        
        # Generate character response to image
        response_msg = f"🎭 **{character['name']}:** *{character['name']} studies the image carefully* "
        
        # Add character-specific response based on their personality
        if "wizard" in current_char_id:
            response_msg += "Fascinating... I sense mystical energies in this image. Tell me, where did you encounter this?"
        elif "android" in current_char_id:
            response_msg += "Analyzing visual data... This image contains interesting patterns. Can you provide context about its significance?"
        elif "pirate" in current_char_id:
            response_msg += "Arrr, that be an interesting sight! Reminds me of adventures on the high seas. What story does this tell, matey?"
        elif "vampire" in current_char_id:
            response_msg += "How... intriguing. This image stirs memories of nights long past. Pray tell, what draws you to share this with me?"
        else:
            response_msg += f"This is quite interesting! {caption}"
        
        await update.message.reply_text(response_msg, parse_mode='Markdown')
        
        try:
            await db.log_interaction(
                user_id=user_id,
                content_type='image_response',
                prompt=caption,
                character_id=current_char_id,
                success=True
            )
            logger.info(f"Logged image response for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to log image response: {e}")
    
    async def handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle uploaded videos - generate character response"""
        user_id = update.effective_user.id
        
        current_char_id = self.user_contexts.get(user_id, {}).get("current_character", "wizard")
        character = await CharacterManager.get_character(current_char_id, user_id)
        
        if not character:
            await update.message.reply_text("No character selected. Use /characters to choose one.")
            return
        
        caption = update.message.caption or "What do you think of this video?"
        
        response_msg = f"🎭 **{character['name']}:** *{character['name']} watches the moving images with interest* "
        
        if "wizard" in current_char_id:
            response_msg += "Remarkable! These moving pictures are like scrying into distant realms. What magic is this?"
        elif "android" in current_char_id:
            response_msg += "Processing motion data... This video format is efficient for information transfer. What is its purpose?"
        elif "pirate" in current_char_id:
            response_msg += "By Blackbeard's ghost! Moving pictures like a ship on rolling waves! What tale does this tell?"
        else:
            response_msg += f"Fascinating moving images! {caption}"
        
        await update.message.reply_text(response_msg, parse_mode='Markdown')
        
        try:
            await db.log_interaction(
                user_id=user_id,
                content_type='video_response',
                prompt=caption,
                character_id=current_char_id,
                success=True
            )
            logger.info(f"Logged video response for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to log video response: {e}")
    
    async def run(self):
        """Initialize and run the bot"""
        logger.info("Starting bot initialization...")

        try:
            # Initialize database
            logger.info("Initializing database...")
            await db.init_db()
            logger.info("Database initialized successfully")

            # Initialize default characters in database
            logger.info("Setting up default characters...")
            for char_id, char_data in CharacterManager.DEFAULT_CHARACTERS.items():
                await db.ensure_default_character(char_id, char_data)
                logger.debug(f"Ensured character: {char_id}")
            logger.info("Default characters setup complete")

            # Start bot
            logger.info("Starting Telegram bot...")
            await self.app.initialize()
            await self.app.start()

            logger.info("🤖 AI Roleplay Bot started successfully!")
            logger.info(f"📊 Database: {DATABASE_PATH}")
            logger.info(f"🌐 HuggingFace Spaces: {list(HF_SPACES.keys())}")
            if DEBUG:
                logger.info("Debug mode enabled")

            # Start polling
            logger.info("Starting polling...")
            async with self.app:
                await self.app.updater.start_polling()
                logger.info("Bot is now running and polling for updates")
                while True:
                    await asyncio.sleep(60)  # Keep container alive

        except Exception as e:
            logger.critical(f"Failed to start bot: {e}")
            raise

if __name__ == "__main__":
    try:
        logger.info("Creating bot instance...")
        bot = AIBot()
        logger.info("Starting bot...")
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
        print("Bot shutdown requested.")
    except Exception as e:
        logger.critical(f"Critical bot error: {e}")
        print(f"Bot error: {e}")
        raise
