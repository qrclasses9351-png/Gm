import os
import logging
import re
import requests
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
            file = await update.message.document.get_file()
            file_path = f"temp_{update.message.document.file_name}"
            
            await file.download_to_drive(file_path)
            
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse links
            links = self.extract_links(content)
            
            if not links:
                await update.message.reply_text("❌ इस फाइल में कोई वैध लिंक नहीं मिला।")
                os.remove(file_path)
                return
            
            await update.message.reply_text(f"✅ {len(links)} लिंक मिले! डाउनलोड शुरू कर रहा हूं...")
            
            # Start download process
            await self.start_download(update, context, links)
            
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
        await self.start_download(update, context, links)

    def extract_links(self, text):
        """Extract PDF and video links from text."""
        # Pattern for both PDF and video links
        pattern = r'https?://[^\s<>"]+?\.(pdf|PDF|mp4|MP4|mp3|MP3|mov|MOV|avi|AVI)'
        links = re.findall(pattern, text)
        
        # Also get all URLs and filter
        url_pattern = r'https?://[^\s<>"]+'
        all_urls = re.findall(url_pattern, text)
        
        valid_urls = []
        for url in all_urls:
            if any(ext in url.lower() for ext in ['.pdf', '.mp4', '.mp3', '.mov', '.avi']):
                valid_urls.append(url)
            elif 'utkarshapp.com' in url or 'cloudfront.net' in url:
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
            
            for i, link in enumerate(links, 1):
                try:
                    await update.message.reply_text(f"📥 डाउनलोड हो रहा है ({i}/{total_files}):\n{link}")
                    
                    filename = await self.download_manager.download_file(link, download_dir)
                    
                    if filename:
                        downloaded_files.append(filename)
                        await update.message.reply_text(f"✅ सफलतापूर्वक डाउनलोड हुआ: {filename}")
                    else:
                        await update.message.reply_text(f"❌ डाउनलोड विफल: {link}")
                        
                except Exception as e:
                    logger.error(f"Error downloading {link}: {e}")
                    await update.message.reply_text(f"❌ त्रुटि: {link}")
            
            # Send completion message
            if downloaded_files:
                await update.message.reply_text(
                    f"🎉 डाउनलोड पूरा हुआ!\n"
                    f"✅ सफल: {len(downloaded_files)}/{total_files} फाइलें\n"
                    f"📁 लोकेशन: {download_dir}"
                )
            else:
                await update.message.reply_text("❌ कोई भी फाइल डाउनलोड नहीं हो सकी।")
                
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
    port = int(os.environ.get('PORT', 8443))
    webhook_url = os.environ.get('WEBHOOK_URL', '')
    
    if webhook_url:
        # Production (with webhook)
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=BOT_TOKEN,
            webhook_url=f"{webhook_url}/{BOT_TOKEN}"
        )
    else:
        # Development (polling)
        application.run_polling()

if __name__ == '__main__':
    main()
