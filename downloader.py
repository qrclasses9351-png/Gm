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
            self.session = aiohttp.ClientSession()
        return self.session

    async def download_file(self, url, download_dir):
        """Download a file from URL."""
        try:
            session = await self.get_session()
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=300)) as response:
                if response.status == 200:
                    # Get filename from URL or Content-Disposition header
                    filename = self.get_filename(url, response)
                    filepath = os.path.join(download_dir, filename)
                    
                    # Download file
                    async with aiofiles.open(filepath, 'wb') as file:
                        async for chunk in response.content.iter_chunked(1024):
                            await file.write(chunk)
                    
                    logger.info(f"Downloaded: {filename}")
                    return filename
                else:
                    logger.error(f"HTTP {response.status} for URL: {url}")
                    return None
                    
        except Exception as e:
            logger.error(f"Download error for {url}: {e}")
            return None

    def get_filename(self, url, response):
        """Extract filename from URL or response headers."""
        # Try to get filename from Content-Disposition header
        content_disposition = response.headers.get('Content-Disposition', '')
        if 'filename=' in content_disposition:
            filename = re.findall('filename="?([^"]+)"?', content_disposition)
            if filename:
                return filename[0]
        
        # Try to get filename from URL
        parsed_url = urlparse(url)
        url_path = parsed_url.path
        if '/' in url_path:
            filename = url_path.split('/')[-1]
            if filename and '.' in filename:
                return filename
        
        # Generate a filename based on content type
        content_type = response.headers.get('Content-Type', '')
        if 'pdf' in content_type.lower():
            return f"document_{hash(url)}.pdf"
        elif 'video' in content_type.lower():
            return f"video_{hash(url)}.mp4"
        else:
            return f"file_{hash(url)}.bin"

    async def close(self):
        """Close the session."""
        if self.session:
            await self.session.close()
