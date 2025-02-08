import os
import asyncio
import hashlib
import logging
from typing import Dict, Any, Tuple, List
from datetime import datetime, timedelta

from yt_dlp import YoutubeDL
from config import Config

logger = logging.getLogger(__name__)

class DownloadManager:
    def __init__(self):
        self.config = Config()
        self.base_opts = {
            'noplaylist': True,
            'nooverwrites': True,
            'geo_bypass': True,
            'quiet': True,
            'no_warnings': True,
            'outtmpl': os.path.join(self.config.DOWNLOAD_DIR, '%(id)s.%(ext)s'),
            'max_filesize': self.config.MAX_FILE_SIZE_MB * 1024 * 1024,
            'cookiefile': 'cookies.txt'  # Added this line to use the cookies file
        }

    def search_video(self, query: str) -> List[Dict]:
        """Search videos with enhanced metadata"""
        with YoutubeDL(self.base_opts) as ydl:
            try:
                results = ydl.extract_info(
                    f"ytsearch{self.config.MAX_SEARCH_RESULTS}:{query}",
                    download=False
                )
                if results and 'entries' in results:
                    return [{
                        'id': entry['id'],
                        'title': entry['title'],
                        'duration': entry['duration'],
                        'url': entry['webpage_url'],
                        'thumbnail': entry.get('thumbnail'),
                        'uploader': entry.get('uploader', 'Unknown'),
                        'height': entry.get('height', 0),
                        'filesize': entry.get('filesize', 0)
                    } for entry in results['entries']]
            except Exception as e:
                logger.error(f"Search error: {str(e)}")
                return []
        return []

    def process_playlist(self, url: str) -> List[Dict]:
        """Process YouTube playlist"""
        ydl_opts = dict(self.base_opts)
        ydl_opts['noplaylist'] = False

        with YoutubeDL(ydl_opts) as ydl:
            try:
                results = ydl.extract_info(url, download=False)
                if results and 'entries' in results:
                    return [{
                        'id': entry['id'],
                        'title': entry['title'],
                        'duration': entry['duration'],
                        'url': entry['webpage_url'],
                        'uploader': entry.get('uploader', 'Unknown')
                    } for entry in results['entries']]
            except Exception as e:
                logger.error(f"Playlist error: {str(e)}")
                return []
        return []

    def download_media(self, url: str, format_type: str = 'mp3', quality: str = 'medium') -> Tuple[str, Dict, float]:
        """Download media in specified format"""
        format_config = self.config.FORMATS[format_type].copy()
        ydl_opts = dict(self.base_opts)

        # Add format specific options
        ydl_opts.update({
            'format': format_config['format'],
            'postprocessors': format_config['postprocessors']
        })

        # Add quality for MP3
        if format_type == 'mp3':
            ydl_opts['postprocessors'][0]['preferredquality'] = self.config.AUDIO_QUALITIES[quality]

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)

                # Adjust extension based on format
                if format_type == 'mp3':
                    file_path = file_path.replace('.webm', '.mp3').replace('.m4a', '.mp3')
                elif format_type == 'mp4':
                    file_path = file_path.replace('.webm', '.mp4')

                file_size = os.path.getsize(file_path) / (1024 * 1024)  # Convert to MB

                # Vérifier la taille du fichier
                if file_size > self.config.MAX_FILE_SIZE_MB:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    raise ValueError(f"Le fichier est trop volumineux ({file_size:.1f}MB > {self.config.MAX_FILE_SIZE_MB}MB)")

                return file_path, info, file_size

        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            logger.error(f"Erreur de téléchargement : {str(e)}")
            raise

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate file hash for deduplication"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    async def cleanup_old_files(self):
        """Clean up old temporary files"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=1)
            for filename in os.listdir(self.config.DOWNLOAD_DIR):
                file_path = os.path.join(self.config.DOWNLOAD_DIR, filename)
                if os.path.getctime(file_path) < cutoff_time.timestamp():
                    os.remove(file_path)
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")