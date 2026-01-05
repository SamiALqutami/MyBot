from modules.db_handler import get_db_connection

class PepperManager:
    @staticmethod
    def get_balance(user_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0

    @staticmethod
    def update_balance(user_id, amount):
        conn = get_db_connection()
        cursor = conn.cursor()
        # تحديث النقاط أو إنشاء مستخدم جديد إذا لم يوجد
        cursor.execute('''
            INSERT INTO users (user_id, points) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET points = points + ?
        ''', (user_id, amount, amount))
        conn.commit()
        conn.close()
