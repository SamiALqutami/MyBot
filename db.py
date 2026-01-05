# db.py
import sqlite3
import logging
import os
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path="data/bot.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """إنشاء الجداول الأساسية فقط، الأنظمة الأخرى تضيف جداولها لاحقاً"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    username TEXT,
                    points INTEGER DEFAULT 100,
                    is_ban INTEGER DEFAULT 0,
                    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

    @contextmanager
    def get_cursor(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ خطأ في قاعدة البيانات: {e}")
            raise
        finally:
            conn.close()

# إنشاء نسخة واحدة ثابتة لكل الأنظمة
db = DatabaseManager()
