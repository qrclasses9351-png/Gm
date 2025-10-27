import os
import logging
import re
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from downloader import DownloadManager

# Bot configuration
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramDownloaderBot:
    def __init__(self):
        self.download_manager = DownloadManager()
        self.download_tasks = {}
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message when command /start is issued."""
        user = update.effective_user
        welcome_text = f"""
नमस्ते {user.first_name}! 🙏

मैं एक डाउनलोडर बॉट हूं जो आपको PDF और वीडियो फाइलें डाउनलोड करने में मदद कर सकता हूं।

📁 **उपयोग करने का तरीका:**
1. मुझे कोई टेक्स्ट फाइल भेजें जिसमें डाउनलोड लिंक्स हों
2. या सीधे PDF/वीडियो लिंक भेजें

🔧 **कमांड्स:**
/start - बॉट शुरू करें
/download - डाउनलोड शुरू करें
/status - डाउनलोड स्टेटस देखें

बस मुझे अपनी फाइल भेजें और मैं आपकी मदद करूंगा! 😊
        """
        await update.message.reply_text(welcome_text)

    async def handle_text_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text files containing download links."""
        try:
            await update.message.reply_text("📥 फाइल प्राप्त हुई, प्रोसेसिंग...")
            
            file = await update.message.document.get_file()
            file_path = f"temp_{update.message.document.file_name}"
            
            await file.download_to_drive(file_path)
            
            # Read the file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Parse links
            links = self.extract_links(content)
            
            if not links:
                await update.message.reply_text("❌ इस फाइल में कोई वैध लिंक नहीं मिला।")
                os.remove(file_path)
                return
            
            await update.message.reply_text(f"✅ {len(links)} लिंक मिले! डाउनलोड शुरू कर रहा हूं...")
            
            # Start download process in background
            asyncio.create_task(self.start_download(update, context, links))
            
            # Clean up
            os.remove(file_path)
            
        except Exception as e:
            logger.error(f"Error handling text file: {e}")
            await update.message.reply_text("❌ फाइल प्रोसेस करने में त्रुटि हुई।")

    async def handle_direct_links(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle direct links sent as text."""
        text = update.message.text
        links = self.extract_links(text)
        
        if not links:
            await update.message.reply_text("❌ कोई वैध लिंक नहीं मिला।")
            return
        
        await update.message.reply_text(f"✅ {len(links)} लिंक मिले! डाउनलोड शुरू कर रहा हूं...")
        asyncio.create_task(self.start_download(update, context, links))

    def extract_links(self, text):
        """Extract PDF and video links from text."""
        # Pattern for URLs
        url_pattern = r'https?://[^\s<>"]+'
        all_urls = re.findall(url_pattern, text)
        
        valid_urls = []
        for url in all_urls:
            # Check for file extensions
            if any(ext in url.lower() for ext in ['.pdf', '.mp4', '.mp3', '.mov', '.avi', '.mkv', '.webm']):
                valid_urls.append(url)
            # Check for utkarshapp domains
            elif any(domain in url for domain in ['utkarshapp.com', 'cloudfront.net']):
                valid_urls.append(url)
        
        return list(set(valid_urls))  # Remove duplicates

    async def start_download(self, update: Update, context: ContextTypes.DEFAULT_TYPE, links):
        """Start the download process."""
        chat_id = update.effective_chat.id
        
        try:
            # Create download directory
            download_dir = f"downloads_{chat_id}"
            os.makedirs(download_dir, exist_ok=True)
            
            # Start download
            total_files = len(links)
            downloaded_files = []
            failed_files = []
            
            for i, link in enumerate(links, 1):
                try:
                    status_msg = await update.message.reply_text(
                        f"📥 डाउनलोड हो रहा है ({i}/{total_files}):\n"
                        f"`{link}`",
                        parse_mode='Markdown'
                    )
                    
                    filename = await self.download_manager.download_file(link, download_dir)
                    
                    if filename:
                        downloaded_files.append(filename)
                        await status_msg.edit_text(
                            f"✅ सफलतापूर्वक डाउनलोड हुआ ({i}/{total_files}):\n"
                            f"`{filename}`",
                            parse_mode='Markdown'
                        )
                    else:
                        failed_files.append(link)
                        await status_msg.edit_text(
                            f"❌ डाउनलोड विफल ({i}/{total_files}):\n"
                            f"`{link}`",
                            parse_mode='Markdown'
                        )
                        
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(1)
                        
                except Exception as e:
                    logger.error(f"Error downloading {link}: {e}")
                    failed_files.append(link)
                    await update.message.reply_text(f"❌ त्रुटि: {link}")
            
            # Send completion message
            completion_text = (
                f"🎉 डाउनलोड पूरा हुआ!\n"
                f"✅ सफल: {len(downloaded_files)}/{total_files} फाइलें\n"
                f"❌ विफल: {len(failed_files)}/{total_files} फाइलें\n"
                f"📁 लोकेशन: `{download_dir}`"
            )
            
            if failed_files:
                completion_text += f"\n\n❌ विफल लिंक्स:\n" + "\n".join(failed_files[:5])
                if len(failed_files) > 5:
                    completion_text += f"\n... और {len(failed_files) - 5} और"
            
            await update.message.reply_text(completion_text, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Download process error: {e}")
            await update.message.reply_text("❌ डाउनलोड प्रक्रिया में त्रुटि हुई।")

    async def download_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /download command."""
        await update.message.reply_text(
            "📁 कृपया मुझे एक टेक्स्ट फाइल भेजें जिसमें डाउनलोड लिंक्स हों, "
            "या सीधे लिंक्स को टेक्स्ट के रूप में पेस्ट करें।"
        )

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        await update.message.reply_text("🤖 बॉट सक्रिय है और काम कर रहा है!")

def main():
    """Start the bot."""
    # Create bot instance
    bot = TelegramDownloaderBot()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("download", bot.download_command))
    application.add_handler(CommandHandler("status", bot.status_command))
    application.add_handler(MessageHandler(filters.Document.TEXT, bot.handle_text_file))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_direct_links))

    # Start the Bot
    if os.environ.get('RENDER'):
        # Production (with webhook)
        port = int(os.environ.get('PORT', 8443))
        webhook_url = os.environ.get('WEBHOOK_URL', '')
        
        if webhook_url:
            application.run_webhook(
                listen="0.0.0.0",
                port=port,
                url_path=BOT_TOKEN,
                webhook_url=f"{webhook_url}/{BOT_TOKEN}"
            )
        else:
            # Use polling if no webhook URL
            application.run_polling()
    else:
        # Development (polling)
        print("🤖 Bot started with polling...")
        application.run_polling()

if __name__ == '__main__':
    main()
