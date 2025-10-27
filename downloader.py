import aiohttp
import aiofiles
import os
import re
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

class DownloadManager:
    def __init__(self):
        self.session = None
        
    async def get_session(self):
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=300)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def download_file(self, url, download_dir):
        """Download a file from URL."""
        try:
            session = await self.get_session()
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    # Get filename from URL or Content-Disposition header
                    filename = await self.get_filename(url, response)
                    filepath = os.path.join(download_dir, filename)
                    
                    # Download file
                    total_size = 0
                    async with aiofiles.open(filepath, 'wb') as file:
                        async for chunk in response.content.iter_chunked(8192):
                            await file.write(chunk)
                            total_size += len(chunk)
                    
                    logger.info(f"Downloaded: {filename} ({total_size} bytes)")
                    return filename
                else:
                    logger.error(f"HTTP {response.status} for URL: {url}")
                    return None
                    
        except Exception as e:
            logger.error(f"Download error for {url}: {e}")
            return None

    async def get_filename(self, url, response):
        """Extract filename from URL or response headers."""
        # Try to get filename from Content-Disposition header
        content_disposition = response.headers.get('Content-Disposition', '')
        if 'filename=' in content_disposition:
            filename = re.findall('filename="?([^"]+)"?', content_disposition)
            if filename:
                return self.sanitize_filename(filename[0])
        
        # Try to get filename from URL
        parsed_url = urlparse(url)
        url_path = parsed_url.path
        if '/' in url_path:
            filename = url_path.split('/')[-1]
            if filename and '.' in filename:
                return self.sanitize_filename(filename)
        
        # Generate a filename based on content type and URL
        content_type = response.headers.get('Content-Type', '')
        url_hash = hash(url) % 10000  # Simple hash
        
        if 'pdf' in content_type.lower() or '.pdf' in url.lower():
            return f"document_{url_hash}.pdf"
        elif 'video' in content_type.lower() or any(ext in url.lower() for ext in ['.mp4', '.mov', '.avi']):
            return f"video_{url_hash}.mp4"
        else:
            return f"file_{url_hash}.bin"

    def sanitize_filename(self, filename):
        """Sanitize filename to remove invalid characters."""
        # Remove invalid characters for filenames
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename.strip()

    async def close(self):
        """Close the session."""
        if self.session:
            await self.session.close()
