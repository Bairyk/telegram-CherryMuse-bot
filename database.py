import aiosqlite
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from config import DATABASE_PATH

class Database:
    def __init__(self):
        self.db_path = DATABASE_PATH
    
    async def init_db(self):
        """Initialize database tables with enhanced schema"""
        async with aiosqlite.connect(self.db_path) as db:
            # User interactions table (enhanced)
            await db.execute('''
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    content_type TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    character_id TEXT,
                    theme TEXT,
                    success BOOLEAN NOT NULL,
                    response_time REAL,
                    error_msg TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # Characters table for custom characters
            await db.execute('''
                CREATE TABLE IF NOT EXISTS characters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    lore TEXT NOT NULL,
                    behavior TEXT NOT NULL,
                    appearance TEXT NOT NULL,
                    creator_id INTEGER,
                    public BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    usage_count INTEGER DEFAULT 0
                )
            ''')
            
            # User preferences and settings
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    current_character TEXT DEFAULT 'wizard',
                    preferred_themes TEXT,
                    settings TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_active DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Analytics table for aggregated data
            await db.execute('''
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    content_type TEXT NOT NULL,
                    theme TEXT,
                    character_id TEXT,
                    count INTEGER DEFAULT 1,
                    avg_response_time REAL,
                    success_rate REAL,
                    UNIQUE(date, content_type, theme, character_id)
                )
            ''')
            
            # Create indexes for better performance
            await db.execute('CREATE INDEX IF NOT EXISTS idx_interactions_user_id ON interactions(user_id)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON interactions(timestamp)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_interactions_character_id ON interactions(character_id)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_characters_creator_id ON characters(creator_id)')
            
            await db.commit()
            print("Database initialized successfully")
    
    async def log_interaction(self, user_id: int, content_type: str, prompt: str, 
                            character_id: str = None, theme: str = None, 
                            success: bool = True, response_time: float = None, 
                            error_msg: str = None, metadata: Dict = None):
        """Log user interaction with enhanced data"""
        async with aiosqlite.connect(self.db_path) as db:
            metadata_json = json.dumps(metadata) if metadata else None
            
            await db.execute('''
                INSERT INTO interactions 
                (user_id, content_type, prompt, character_id, theme, success, response_time, error_msg, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, content_type, prompt[:200], character_id, theme, success, response_time, error_msg, metadata_json))
            
            # Update user last active
            await db.execute('''
                INSERT OR REPLACE INTO user_settings (user_id, last_active)
                VALUES (?, ?)
            ''', (user_id, datetime.now().isoformat()))
            
            await db.commit()
    
    async def create_character(self, user_id: int, name: str, lore: str, 
                             behavior: str, appearance: str, public: bool = False) -> Optional[str]:
        """Create a custom character"""
        character_id = f"custom_{name.lower().replace(' ', '_').replace(',', '').replace('.', '')}"
        
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute('''
                    INSERT INTO characters (character_id, name, lore, behavior, appearance, creator_id, public)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (character_id, name, lore, behavior, appearance, user_id, public))
                await db.commit()
                return character_id
            except aiosqlite.IntegrityError:
                # Character ID already exists, try with user suffix
                character_id = f"custom_{name.lower().replace(' ', '_')}_{user_id}"
                try:
                    await db.execute('''
                        INSERT INTO characters (character_id, name, lore, behavior, appearance, creator_id, public)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (character_id, name, lore, behavior, appearance, user_id, public))
                    await db.commit()
                    return character_id
                except Exception as e:
                    print(f"Error creating character: {e}")
                    return None
    
    async def get_character(self, character_id: str, user_id: int = None) -> Optional[Dict]:
        """Get character data"""
        async with aiosqlite.connect(self.db_path) as db:
            # Try to get custom character first
            cursor = await db.execute('''
                SELECT character_id, name, lore, behavior, appearance, creator_id, public
                FROM characters 
                WHERE character_id = ? AND (public = 1 OR creator_id = ?)
            ''', (character_id, user_id or 0))
            
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "lore": row[2],
                    "behavior": row[3],
                    "appearance": row[4],
                    "creator_id": row[5],
                    "public": bool(row[6])
                }
            return None
    
    async def get_user_characters(self, user_id: int) -> List[Dict]:
        """Get user's custom characters"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT character_id, name, lore, behavior, appearance, usage_count
                FROM characters 
                WHERE creator_id = ?
                ORDER BY usage_count DESC, created_at DESC
            ''', (user_id,))
            
            rows = await cursor.fetchall()
            return [{
                "id": row[0],
                "name": row[1],
                "lore": row[2],
                "behavior": row[3],
                "appearance": row[4],
                "usage_count": row[5]
            } for row in rows]
    
    async def ensure_default_character(self, character_id: str, character_data: Dict):
        """Ensure default character exists in database"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT id FROM characters WHERE character_id = ?', (character_id,))
            exists = await cursor.fetchone()
            
            if not exists:
                await db.execute('''
                    INSERT INTO characters (character_id, name, lore, behavior, appearance, creator_id, public)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (character_id, character_data["name"], character_data["lore"], 
                     character_data["behavior"], character_data["appearance"], 0, True))
                await db.commit()
    
    async def get_popular_themes(self, days: int = 7, limit: int = 10) -> List[tuple]:
        """Get popular themes for analytics"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT theme, COUNT(*) as count 
                FROM interactions 
                WHERE timestamp > datetime('now', '-{} days') 
                AND theme IS NOT NULL 
                AND theme != 'general'
                GROUP BY theme 
                ORDER BY count DESC 
                LIMIT ?
            '''.format(days), (limit,))
            return await cursor.fetchall()
    
    async def get_popular_characters(self, days: int = 7, limit: int = 10) -> List[tuple]:
        """Get popular characters for analytics"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT character_id, COUNT(*) as count 
                FROM interactions 
                WHERE timestamp > datetime('now', '-{} days') 
                AND character_id IS NOT NULL 
                AND content_type IN ('roleplay', 'image', 'video')
                GROUP BY character_id 
                ORDER BY count DESC 
                LIMIT ?
            '''.format(days), (limit,))
            return await cursor.fetchall()
    
    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            # Total interactions
            cursor = await db.execute('''
                SELECT COUNT(*), 
                       AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate,
                       AVG(response_time) as avg_response_time
                FROM interactions 
                WHERE user_id = ?
            ''', (user_id,))
            
            row = await cursor.fetchone()
            if row and row[0] > 0:
                return {
                    "total_interactions": row[0],
                    "success_rate": row[1] or 0.0,
                    "avg_response_time": row[2] or 0.0
                }
            return {"total_interactions": 0, "success_rate": 0.0, "avg_response_time": 0.0}
    
    async def get_error_stats(self, days: int = 1) -> List[tuple]:
        """Get error statistics for debugging"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT content_type, COUNT(*) as errors
                FROM interactions 
                WHERE timestamp > datetime('now', '-{} days') 
                AND success = 0
                GROUP BY content_type
                ORDER BY errors DESC
            '''.format(days))
            return await cursor.fetchall()
    
    async def update_character_usage(self, character_id: str):
        """Update character usage count"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE characters 
                SET usage_count = usage_count + 1 
                WHERE character_id = ?
            ''', (character_id,))
            await db.commit()
    
    async def cleanup_old_data(self, days: int = 30):
        """Clean up old interaction data (optional maintenance)"""
        async with aiosqlite.connect(self.db_path) as db:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cursor = await db.execute('''
                DELETE FROM interactions 
                WHERE timestamp < ? AND content_type NOT IN ('feedback', 'character_creation')
            ''', (cutoff_date.isoformat(),))
            
            deleted_count = cursor.rowcount
            await db.commit()
            return deleted_count

# Global database instance - FIXED: No circular import
db = Database()
