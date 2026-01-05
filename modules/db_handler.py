import sqlite3
import logging
import os

logger = logging.getLogger(__name__)

DB_PATH = "bot_database.db"

def get_db_connection():
    """إنشاء اتصال مع قاعدة البيانات"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # للوصول للبيانات بأسماء الأعمدة
    return conn

def init_db():
    """إنشاء الجداول إذا لم تكن موجودة عند تشغيل البوت أول مرة"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # جدول المستخدمين (النقاط، الأسماء، VIP)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            nickname TEXT,
            points INTEGER DEFAULT 0,
            is_vip BOOLEAN DEFAULT 0,
            vip_expiry REAL DEFAULT 0,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول الإحصائيات العامة
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_stats (
            stat_name TEXT PRIMARY KEY,
            stat_value INTEGER DEFAULT 0
        )
    ''')
    
    # تهيئة الإحصائيات إذا كانت فارغة
    cursor.execute("INSERT OR IGNORE INTO system_stats (stat_name, stat_value) VALUES ('total_chats', 0)")
    
    conn.commit()
    conn.close()
    logger.info("💾 تم تهيئة قاعدة البيانات على القرص بنجاح.")

# تنفيذ التهيئة فور استدعاء الملف
init_db()
