#!/usr/bin/env python3
"""
Telegram + ImgBB Upload Bot
Upload images from Telegram chat to ImgBB
"""

import os
import json
import base64
import logging
from pathlib import Path
from datetime import datetime
from getpass import getpass

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters, ContextTypes
)
from dotenv import load_dotenv
from PIL import Image

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramImgBBBot:
    def __init__(self):
        self.config_file = "imgbb_config.json"
        self.env_file = ".env"
        self.api_key = None
        self.api_url = "https://api.imgbb.com/1/upload"
        self.telegram_token = None
        self.user_sessions = {}  # Store user upload sessions
        
        # Supported image extensions
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        
    def load_config(self):
        """Load API keys from config or environment"""
        # Load ImgBB API key
        self.api_key = os.getenv('IMGBB_API_KEY')
        if not self.api_key and os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.api_key = config.get('api_key')
            except:
                pass
        
        # Load Telegram token
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        
        return self.api_key is not None and self.telegram_token is not None
    
    def save_config(self):
        """Save API keys to config files"""
        # Save ImgBB key
        if self.api_key:
            config = {'api_key': self.api_key}
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
            
            # Save to .env
            with open(self.env_file, 'a') as f:
                if 'IMGBB_API_KEY' not in open(self.env_file).read():
                    f.write(f"\nIMGBB_API_KEY={self.api_key}\n")
            
            os.chmod(self.config_file, 0o600)
        
        # Save Telegram token
        if self.telegram_token:
            with open(self.env_file, 'a') as f:
                if 'TELEGRAM_BOT_TOKEN' not in open(self.env_file).read():
                    f.write(f"TELEGRAM_BOT_TOKEN={self.telegram_token}\n")
            
            os.chmod(self.env_file, 0o600)
        
        print("✅ Configuration saved successfully!")
    
    def verify_imgbb_key(self):
        """Verify ImgBB API key"""
        test_image = base64.b64encode(b"test").decode('utf-8')
        try:
            response = requests.post(
                self.api_url,
                data={'key': self.api_key, 'image': test_image},
                timeout=10
            )
            return response.status_code == 200 and 'error' not in response.text.lower()
        except:
            return False
    
    def upload_image(self, image_data, filename):
        """Upload image to ImgBB"""
        try:
            # Encode image
            encoded_image = base64.b64encode(image_data).decode('utf-8')
            
            # Prepare payload
            payload = {
                'key': self.api_key,
                'image': encoded_image,
                'name': Path(filename).stem
            }
            
            # Upload
            response = requests.post(self.api_url, data=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return {
                        'success': True,
                        'url': result['data']['url'],
                        'delete_url': result['data'].get('delete_url'),
                        'size': result['data']['size'],
                        'filename': filename
                    }
            
            return {'success': False, 'error': 'Upload failed'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

# Initialize bot
imgbb_bot = TelegramImgBBBot()

# ============ TELEGRAM BOT HANDLERS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when /start is issued"""
    welcome_text = """
🤖 **ImgBB Upload Bot - Welcome!**

I can help you upload images to ImgBB directly from Telegram!

**Commands:**
/start - Show this menu
/help - Get help
/upload - Start uploading images
/stats - View your upload statistics
/set_imgbb_key - Set/Update ImgBB API key
/about - About this bot

**How to use:**
1. First set your ImgBB API key using /set_imgbb_key
2. Then send me any image or use /upload
3. I'll upload it to ImgBB and give you the link!

**Get your ImgBB API key:** https://api.imgbb.com/
    """
    
    keyboard = [
        [InlineKeyboardButton("📸 Upload Image", callback_data='upload')],
        [InlineKeyboardButton("📊 My Stats", callback_data='stats'),
         InlineKeyboardButton("❓ Help", callback_data='help')],
        [InlineKeyboardButton("🔑 Set API Key", callback_data='set_key'),
         InlineKeyboardButton("ℹ️ About", callback_data='about')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text, 
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message"""
    help_text = """
📚 **Help Guide**

**First Time Setup:**
1. Get ImgBB API key from: https://api.imgbb.com/
2. Use /set_imgbb_key to save your key

**Upload Images:**
- Send any image directly in chat
- Or use /upload command
- Multiple images? Send them one by one

**Features:**
✅ Single or multiple image upload
✅ Get direct image URLs
✅ Get delete URLs
✅ View upload history
✅ No file size limits (ImgBB limits apply)

**Commands:**
/start - Main menu
/upload - Start upload session
/stats - View your uploads
/set_imgbb_key - Change API key
/cancel - Cancel current operation
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def set_imgbb_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle ImgBB API key setup"""
    user_id = update.effective_user.id
    
    # Check if key is provided in command
    if context.args:
        imgbb_bot.api_key = context.args[0]
        if imgbb_bot.verify_imgbb_key():
            imgbb_bot.save_config()
            await update.message.reply_text(
                "✅ **ImgBB API key saved successfully!**\n\n"
                "Now you can start uploading images! 📸",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ **Invalid API key!**\n"
                "Please check your key and try again.\n\n"
                "Get a valid key from: https://api.imgbb.com/",
                parse_mode='Markdown'
            )
    else:
        await update.message.reply_text(
            "🔑 **Set your ImgBB API Key**\n\n"
            "Please send your ImgBB API key.\n"
            "Get it from: https://api.imgbb.com/\n\n"
            "Format: `/set_imgbb_key YOUR_API_KEY`\n\n"
            "Or just send the key in this chat.",
            parse_mode='Markdown'
        )
        context.user_data['waiting_for_key'] = True

async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /upload command"""
    if not imgbb_bot.api_key:
        await update.message.reply_text(
            "⚠️ **No ImgBB API key found!**\n\n"
            "Please set your API key first using:\n"
            "/set_imgbb_key YOUR_API_KEY\n\n"
            "Get your key from: https://api.imgbb.com/",
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text(
        "📸 **Ready to upload!**\n\n"
        "Please send me the images you want to upload.\n"
        "You can send multiple images one by one.\n\n"
        "Type /cancel to stop uploading.",
        parse_mode='Markdown'
    )
    context.user_data['uploading'] = True
    context.user_data['uploaded_count'] = 0
    context.user_data['uploaded_urls'] = []

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo uploads"""
    if not imgbb_bot.api_key:
        await update.message.reply_text(
            "⚠️ Please set your ImgBB API key first using /set_imgbb_key"
        )
        return
    
    user_id = update.effective_user.id
    
    # Handle API key input
    if context.user_data.get('waiting_for_key'):
        api_key = update.message.text.strip()
        imgbb_bot.api_key = api_key
        
        if imgbb_bot.verify_imgbb_key():
            imgbb_bot.save_config()
            await update.message.reply_text(
                "✅ **API key saved!** Now you can upload images. Send me any image! 📸",
                parse_mode='Markdown'
            )
            context.user_data['waiting_for_key'] = False
        else:
            await update.message.reply_text(
                "❌ Invalid API key. Please try again with /set_imgbb_key"
            )
            context.user_data['waiting_for_key'] = False
        return
    
    # Handle regular photo upload
    photo = update.message.photo[-1]  # Get highest quality
    file = await photo.get_file()
    
    # Send processing message
    status_msg = await update.message.reply_text("🔄 Uploading to ImgBB...")
    
    # Download image
    image_data = await file.download_as_bytearray()
    filename = f"telegram_photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    
    # Upload to ImgBB
    result = imgbb_bot.upload_image(bytes(image_data), filename)
    
    if result['success']:
        # Prepare response
        response_text = (
            f"✅ **Upload Successful!**\n\n"
            f"📸 **Image:** {result['filename']}\n"
            f"🔗 **URL:** {result['url']}\n"
            f"🗑️ **Delete URL:** {result['delete_url']}\n"
            f"📊 **Size:** {result['size']} bytes\n\n"
            f"💾 Save this link to access your image!"
        )
        
        # Create keyboard with actions
        keyboard = [
            [InlineKeyboardButton("🔗 Open Image", url=result['url'])],
            [InlineKeyboardButton("📋 Copy URL", callback_data=f"copy_{result['url']}"),
             InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{result['delete_url']}")],
            [InlineKeyboardButton("📸 Upload More", callback_data='upload')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await status_msg.edit_text(response_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        # Store in user stats
        if user_id not in context.bot_data:
            context.bot_data[user_id] = {'uploads': [], 'count': 0}
        context.bot_data[user_id]['uploads'].append(result)
        context.bot_data[user_id]['count'] += 1
        
        # Update session
        if context.user_data.get('uploading'):
            context.user_data['uploaded_count'] += 1
            context.user_data['uploaded_urls'].append(result['url'])
            
            if context.user_data['uploaded_count'] >= 10:  # Limit per session
                await update.message.reply_text(
                    f"📊 **Session Complete!**\n"
                    f"Uploaded {context.user_data['uploaded_count']} images.\n"
                    f"Use /upload to start a new session.",
                    parse_mode='Markdown'
                )
                context.user_data['uploading'] = False
    else:
        await status_msg.edit_text(
            f"❌ **Upload Failed!**\n\nError: {result.get('error', 'Unknown error')}\n\nPlease try again.",
            parse_mode='Markdown'
        )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document/image file uploads"""
    if not imgbb_bot.api_key:
        await update.message.reply_text("⚠️ Please set ImgBB API key first using /set_imgbb_key")
        return
    
    document = update.message.document
    file_extension = Path(document.file_name).suffix.lower()
    
    # Check if it's an image
    if file_extension not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
        await update.message.reply_text(
            f"❌ Unsupported file type: {file_extension}\n"
            f"Supported: JPG, PNG, GIF, BMP, WEBP"
        )
        return
    
    status_msg = await update.message.reply_text(f"🔄 Uploading {document.file_name}...")
    
    file = await document.get_file()
    image_data = await file.download_as_bytearray()
    
    result = imgbb_bot.upload_image(bytes(image_data), document.file_name)
    
    if result['success']:
        response_text = (
            f"✅ **Upload Successful!**\n\n"
            f"📄 **File:** {result['filename']}\n"
            f"🔗 **URL:** {result['url']}\n"
            f"🗑️ **Delete URL:** {result['delete_url']}\n"
            f"📊 **Size:** {result['size']} bytes"
        )
        await status_msg.edit_text(response_text, parse_mode='Markdown')
    else:
        await status_msg.edit_text(f"❌ Failed: {result.get('error')}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics"""
    user_id = update.effective_user.id
    
    if user_id not in context.bot_data:
        await update.message.reply_text(
            "📊 **Your Stats**\n\n"
            "No uploads yet! Send me some images to get started. 📸",
            parse_mode='Markdown'
        )
        return
    
    stats = context.bot_data[user_id]
    total_uploads = stats['count']
    recent_uploads = stats['uploads'][-5:]  # Last 5 uploads
    
    stats_text = f"📊 **Your Upload Statistics**\n\n"
    stats_text += f"📸 **Total Uploads:** {total_uploads}\n\n"
    stats_text += f"**Recent Uploads:**\n"
    
    for upload in recent_uploads:
        stats_text += f"• [{upload['filename']}]({upload['url']})\n"
    
    keyboard = [[InlineKeyboardButton("📸 Upload More", callback_data='upload')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        stats_text, 
        parse_mode='Markdown',
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation"""
    if context.user_data.get('uploading'):
        context.user_data['uploading'] = False
        await update.message.reply_text(
            f"❌ **Upload session cancelled!**\n"
            f"Uploaded {context.user_data.get('uploaded_count', 0)} images.\n"
            f"Use /upload to start a new session.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("No active operation to cancel.")

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """About the bot"""
    about_text = """
🤖 **ImgBB Telegram Bot v1.0**

**Features:**
• Upload images directly from Telegram
• Get instant ImgBB hosting links
• Delete URLs for each upload
• Upload history tracking
• Support for multiple image formats

**Developer:** Your Name
**Source Code:** GitHub Repository
**API:** ImgBB API

**Commands:** /start to see all commands
    """
    await update.message.reply_text(about_text, parse_mode='Markdown')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'upload':
        await upload_command(update, context)
    
    elif query.data == 'stats':
        await stats(update, context)
    
    elif query.data == 'help':
        await help_command(update, context)
    
    elif query.data == 'set_key':
        await set_imgbb_key(update, context)
    
    elif query.data == 'about':
        await about(update, context)
    
    elif query.data.startswith('copy_'):
        url = query.data[5:]
        await query.edit_message_text(
            f"✅ URL copied to clipboard!\n\n{url}\n\nYou can now share this link.",
            parse_mode='Markdown'
        )
    
    elif query.data.startswith('delete_'):
        delete_url = query.data[7:]
        await query.edit_message_text(
            f"🗑️ **Delete this image using this link:**\n{delete_url}\n\n"
            f"⚠️ Note: This action is irreversible!",
            parse_mode='Markdown'
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error {context.error}")

# ============ MAIN FUNCTION ============

def setup_bot():
    """Setup and run the bot"""
    print("🤖 Telegram + ImgBB Upload Bot")
    print("="*40)
    
    # Check if configuration exists
    if not imgbb_bot.load_config():
        print("\n⚠️ No configuration found! Let's set it up.\n")
        
        # Setup ImgBB API Key
        print("🔑 ImgBB API Key Setup")
        print("-" * 35)
        print("Get your key from: https://api.imgbb.com/")
        
        while True:
            api_key = getpass("Enter ImgBB API key: ").strip()
            if api_key:
                imgbb_bot.api_key = api_key
                if imgbb_bot.verify_imgbb_key():
                    break
                else:
                    print("❌ Invalid API key! Please try again.\n")
            else:
                print("❌ API key cannot be empty!\n")
        
        # Setup Telegram Bot Token
        print("\n🤖 Telegram Bot Token Setup")
        print("-" * 35)
        print("1. Message @BotFather on Telegram")
        print("2. Create a new bot: /newbot")
        print("3. Copy the bot token\n")
        
        while True:
            token = getpass("Enter Telegram Bot Token: ").strip()
            if token:
                imgbb_bot.telegram_token = token
                break
            else:
                print("❌ Token cannot be empty!\n")
        
        # Save configuration
        imgbb_bot.save_config()
        print("\n✅ Configuration saved successfully!")
    
    # Create application
    application = Application.builder().token(imgbb_bot.telegram_token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("upload", upload_command))
    application.add_handler(CommandHandler("set_imgbb_key", set_imgbb_key))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("about", about))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.IMAGE, handle_document))
    
    # Callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    print(f"\n✅ Bot is running! Find your bot on Telegram: @{application.bot.username}")
    print("Press Ctrl+C to stop\n")
    
    # Start the bot
    application.run_polling()

def main():
    """Main function with menu"""
    while True:
        print("\n" + "="*40)
        print("📋 MAIN MENU")
        print("="*40)
        print("1. Start Telegram Bot")
        print("2. Update API Keys")
        print("3. Exit")
        
        choice = input("\n👉 Choose option (1-3): ").strip()
        
        if choice == '1':
            setup_bot()
        elif choice == '2':
            print("\n🔄 Updating configuration...")
            imgbb_bot.api_key = None
            imgbb_bot.telegram_token = None
            imgbb_bot.load_config()
            
            if not imgbb_bot.api_key:
                api_key = getpass("Enter new ImgBB API key: ").strip()
                if api_key:
                    imgbb_bot.api_key = api_key
                    if imgbb_bot.verify_imgbb_key():
                        print("✅ ImgBB API key updated!")
                    else:
                        print("❌ Invalid key!")
            
            token = getpass("Enter new Telegram Bot Token (or press Enter to skip): ").strip()
            if token:
                imgbb_bot.telegram_token = token
                print("✅ Telegram token updated!")
            
            imgbb_bot.save_config()
        elif choice == '3':
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice!")

if __name__ == "__main__":
    # Install requirements if needed
    try:
        import telegram
    except ImportError:
        print("📦 Installing required packages...")
        os.system("pip install python-telegram-bot Pillow python-dotenv")
    
    main()
