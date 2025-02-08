import os
from dotenv import load_dotenv

class Config:
    # Load environment variables
    load_dotenv()

    # Bot configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7315635157:AAGNDO3SIUsP8-09P3UljrKlU9avxrKnAcU')
    ADMIN_ID = int(os.getenv('ADMIN_TELEGRAM_ID', 0))

    # Paths
    BASE_DIR = os.getcwd()
    DOWNLOAD_DIR = os.path.join(BASE_DIR, 'downloads')
    DB_PATH = os.path.join(BASE_DIR, 'bot_database.sqlite')

    # Limits
    MAX_FILE_SIZE_MB = 50
    MAX_SEARCH_RESULTS = 5
    RATE_LIMIT_SECONDS = 30
    CLEANUP_INTERVAL = 3600  # 1 hour
    MAX_CACHE_AGE = 24 * 60 * 60  # 24 hours

    # Available formats
    FORMATS = {
        'mp3': {
            'ext': 'mp3',
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }]
        },
        'mp4': {
            'ext': 'mp4',
            'format': 'best[height<=720]',
            'postprocessors': []
        }
    }

    # Audio quality options
    AUDIO_QUALITIES = {
        'low': '96',
        'medium': '192',
        'high': '320'
    }

    # Create required directories
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)