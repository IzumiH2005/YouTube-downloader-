import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List

class Database:
    def __init__(self):
        self.db_path = 'bot_database.sqlite'
        self._init_database()

    def _init_database(self):
        """Initialize database with enhanced schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Users table with additional fields
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language TEXT DEFAULT 'en',
                join_date DATETIME,
                total_downloads INTEGER DEFAULT 0,
                total_size REAL DEFAULT 0,
                last_download_date DATETIME
            )
            ''')
            
            # Downloads table with quality info
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                video_id TEXT,
                title TEXT,
                download_date DATETIME,
                file_hash TEXT,
                quality TEXT,
                file_size REAL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            ''')
            
            # Favorites table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                video_id TEXT,
                title TEXT,
                added_date DATETIME,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            ''')
            
            conn.commit()

    def log_download(self, user_id: int, info: Dict[str, Any], file_hash: str,
                    quality: str, file_size: float):
        """Log download with enhanced information"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Update user stats
            cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, total_downloads, total_size, last_download_date)
            VALUES (
                ?,
                COALESCE((SELECT total_downloads + 1 FROM users WHERE user_id = ?), 1),
                COALESCE((SELECT total_size + ? FROM users WHERE user_id = ?), ?),
                ?
            )
            ''', (user_id, user_id, file_size, user_id, file_size, datetime.now()))
            
            # Log download
            cursor.execute('''
            INSERT INTO downloads 
            (user_id, video_id, title, download_date, file_hash, quality, file_size)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                info.get('id', 'unknown'),
                info.get('title', 'Unknown Title'),
                datetime.now(),
                file_hash,
                quality,
                file_size
            ))
            
            conn.commit()

    def get_user_stats(self, user_id: int) -> Optional[Tuple]:
        """Get enhanced user statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    total_downloads,
                    last_download_date,
                    COUNT(DISTINCT d.video_id) as unique_downloads,
                    COUNT(f.id) as favorites_count,
                    total_size
                FROM users u
                LEFT JOIN downloads d ON u.user_id = d.user_id
                LEFT JOIN favorites f ON u.user_id = f.user_id
                WHERE u.user_id = ?
                GROUP BY u.user_id
            ''', (user_id,))
            return cursor.fetchone()

    def get_user_favorites(self, user_id: int) -> List[Dict]:
        """Get user's favorite tracks"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT video_id, title, added_date
                FROM favorites
                WHERE user_id = ?
                ORDER BY added_date DESC
            ''', (user_id,))
            
            favorites = []
            for row in cursor.fetchall():
                favorites.append({
                    'video_id': row[0],
                    'title': row[1],
                    'added_date': row[2]
                })
                
            return favorites