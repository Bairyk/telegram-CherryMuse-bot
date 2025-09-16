import aiosqlite
import json
from datetime import datetime
from config import DATABASE_PATH

class Database:
    def __init__(self):
        self.db_path = DATABASE_PATH
    
    async def init_db(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # User interactions table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    content_type TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    theme TEXT,
                    success BOOLEAN NOT NULL,
                    response_time REAL,
                    error_msg TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Analytics table for aggregated data
            await db.execute('''
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    content_type TEXT NOT NULL,
                    theme TEXT,
                    count INTEGER DEFAULT 1,
                    avg_response_time REAL,
                    success_rate REAL,
                    UNIQUE(date, content_type, theme)
                )
            ''')
            
            await db.commit()
    
    async def log_interaction(self, user_id, content_type, prompt, theme=None, 
                            success=True, response_time=None, error_msg=None):
        """Log user interaction"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO interactions 
                (user_id, content_type, prompt, theme, success, response_time, error_msg)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, content_type, prompt[:100], theme, success, response_time, error_msg))
            await db.commit()
    
    async def get_popular_themes(self, days=7, limit=10):
        """Get popular themes for analytics"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT theme, COUNT(*) as count 
                FROM interactions 
                WHERE timestamp > datetime('now', '-{} days') AND theme IS NOT NULL
                GROUP BY theme 
                ORDER BY count DESC 
                LIMIT ?
            '''.format(days), (limit,))
            return await cursor.fetchall()
    
    async def get_error_stats(self, days=1):
        """Get error statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT content_type, COUNT(*) as errors
                FROM interactions 
                WHERE timestamp > datetime('now', '-{} days') AND success = 0
                GROUP BY content_type
            '''.format(days))
            return await cursor.fetchall()

# Global database instance
db = Database()
