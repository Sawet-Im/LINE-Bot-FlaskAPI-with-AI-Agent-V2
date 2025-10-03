import sqlite3
import datetime

DB_FILE_NAME = "store_database.db"

def initialize_database():
    """Initializes the database by creating tables if they don't exist."""
    try:
        conn = sqlite3.connect(DB_FILE_NAME)
        cursor = conn.cursor()

        # Create menu table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS menu (
                menu_id INTEGER PRIMARY KEY,
                menu_name TEXT,
                price REAL,
                category TEXT,
                store_id INTEGER,
                FOREIGN KEY(store_id) REFERENCES stores(store_id)
            )
        ''')

        # Create promotions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS promotions (
                id INTEGER PRIMARY KEY,
                promo_code TEXT NOT NULL,
                description TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                FOREIGN KEY(menu_id) REFERENCES menu(menu_id)
            )
        ''')
        
        # ตาราง stores ถูกปรับเปลี่ยนเพื่อเก็บการตั้งค่าการตอบกลับอัตโนมัติ
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stores (
                store_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                store_name TEXT,
                opening_hours TEXT,
                status TEXT,
                location TEXT,
                is_auto_reply_enabled INTEGER DEFAULT 1
            )
        ''')

        # Create tasks table for bot responses and admin actions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                task_id INTEGER PRIMARY KEY,
                user_id TEXT NOT NULL,
                line_id TEXT NOT NULL,
                user_message TEXT NOT NULL,
                ai_response TEXT,
                using_sql TEXT,
                admin_response TEXT,
                reply_token TEXT NOT NULL,
                status TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                response_timestamp DATETIME
            )
        ''')

        # Create line_channels table to store per-user credentials
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS line_channels (
                user_id TEXT PRIMARY KEY,
                channel_secret TEXT NOT NULL,
                channel_access_token TEXT NOT NULL
            )
        ''')

        # Add initial data if tables are empty
        seed_data(conn, cursor)

        conn.commit()
        conn.close()
        print(f"Database '{DB_FILE_NAME}' initialized successfully.")
        return f"sqlite:///{DB_FILE_NAME}"

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None

def seed_data(conn, cursor):
    """Inserts initial data into tables if they are empty."""
    cursor.execute("SELECT COUNT(*) FROM menu")
    if cursor.fetchone()[0] == 0:
        menu_data = [
            ('ข้าวผัดกะเพราไก่', 50.00),
            ('ผัดซีอิ๊วหมู', 55.00),
            ('ต้มยำกุ้ง', 80.00),
            ('แกงเขียวหวานเนื้อ', 75.00),
            ('ชาเย็น', 25.00),
            ('กาแฟ', 30.00)
        ]
        cursor.executemany("INSERT INTO menu (menu_name, price) VALUES (?, ?)", menu_data)
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM promotions")
    if cursor.fetchone()[0] == 0:
        promotions_data = [
            ('WELCOME10', 'ลด 10% สำหรับลูกค้าใหม่'),
            ('BUY3GET1', 'ซื้อ 3 จานฟรี 1 จาน')
        ]
        cursor.executemany("INSERT INTO promotions (promo_code, description) VALUES (?, ?)", promotions_data)
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM stores")
    if cursor.fetchone()[0] == 0:
        stores_data = [
            ('สาขาพระราม 9', 'Open', 'อาคารฟอร์จูนทาวน์ ชั้น 2', 1), # ค่า 1 หมายถึงเปิดใช้งาน
            ('สาขาสุขุมวิท 21', 'Closed', 'อาคาร GMM Grammy Place', 1),
            ('สาขาพญาไท', 'Open', 'อาคาร CP Tower', 1)
        ]
        cursor.executemany("INSERT INTO stores (store_name, status, location, is_auto_reply_enabled) VALUES (?, ?, ?, ?)", stores_data)
        conn.commit()
    
def add_credentials(user_id, channel_secret, channel_access_token):
    """Adds or updates a user's LINE channel credentials."""
    conn = sqlite3.connect(DB_FILE_NAME)
    cursor = conn.cursor()
    try:
        # เพิ่มข้อมูลในตาราง line_channels
        cursor.execute('''
            INSERT OR REPLACE INTO line_channels (user_id, channel_secret, channel_access_token)
            VALUES (?, ?, ?)
        ''', (user_id, channel_secret, channel_access_token))
        
        # เพิ่มข้อมูลในตาราง stores ด้วย user_id และตั้งค่าเริ่มต้น is_auto_reply_enabled เป็น 1
        cursor.execute('''
            INSERT OR IGNORE INTO stores (user_id, is_auto_reply_enabled)
            VALUES (?, 1)
        ''', (user_id,))
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Database error adding credentials: {e}")
        return False
    finally:
        conn.close()

def get_credentials(user_id):
    """Retrieves a user's LINE channel credentials."""
    conn = sqlite3.connect(DB_FILE_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        # ดึงข้อมูล channel_secret และ channel_access_token จากตาราง line_channels
        cursor.execute("SELECT * FROM line_channels WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error getting credentials: {e}")
        return None
    finally:
        conn.close()

def get_auto_reply_setting(user_id):
    """Retrieves the auto-reply status for a specific user from the stores table."""
    conn = sqlite3.connect(DB_FILE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT is_auto_reply_enabled FROM stores WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        # หากไม่พบข้อมูล ให้คืนค่าเริ่มต้น (เปิดใช้งาน)
        return result[0] if result else 1
    except sqlite3.Error as e:
        print(f"Database error getting auto-reply setting: {e}")
        return 1 # คืนค่าเริ่มต้นในกรณีเกิดข้อผิดพลาด
    finally:
        conn.close()

def update_auto_reply_setting(user_id, status):
    """Updates the auto-reply status for a specific user in the stores table."""
    conn = sqlite3.connect(DB_FILE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE stores SET is_auto_reply_enabled = ? WHERE user_id = ?", (status, user_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error updating auto-reply setting: {e}")
    finally:
        conn.close()
        

def add_new_task(user_id, line_id, reply_token, user_message):
    """Adds a new message task from a LINE user to the database."""
    conn = sqlite3.connect(DB_FILE_NAME)
    cursor = conn.cursor()
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        cursor.execute("""
            INSERT INTO tasks (user_id, line_id, reply_token, user_message, status,timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, line_id, reply_token, user_message, "Pending",timestamp))
        conn.commit()
        return cursor.lastrowid  # คืนค่า ID ที่สร้างขึ้นมา
    except sqlite3.Error as e:
        print(f"Database error adding new task: {e}")
        return None
    finally:
        conn.close()

# อัปเดตฟังก์ชันให้ใช้ 'user_id'
def get_tasks_by_status(user_id, status):
    """Fetches tasks from the tasks table based on their status and store user ID."""
    conn = sqlite3.connect(DB_FILE_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM tasks WHERE user_id = ? AND status = ? ORDER BY timestamp DESC", (user_id, status))
        tasks = cursor.fetchall()
        return [dict(task) for task in tasks]
    except sqlite3.Error as e:
        print(f"Database error fetching tasks: {e}")
        return []
    finally:
        conn.close()

def update_task_status(task_id, new_status):
    """Updates the status of a specific task."""
    conn = sqlite3.connect(DB_FILE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE tasks SET status = ? WHERE task_id = ?", (new_status, task_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error updating task status: {e}")
    finally:
        conn.close()

def update_task_response(task_id, response):
    """
    Updates the AI's response, status, and records a dedicated response timestamp.
    """
    conn = sqlite3.connect(DB_FILE_NAME)
    cursor = conn.cursor()
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        cursor.execute("""
            UPDATE tasks
            SET
                ai_response = ?,
                status = 'Responded',
                response_timestamp = ?
            WHERE
                task_id = ?
        """, (response, timestamp, task_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error updating AI response: {e}")
    finally:
        conn.close()

def update_admin_response(task_id, response):
    """
    Updates the admin's response, status, and records a dedicated response timestamp.
    """
    conn = sqlite3.connect(DB_FILE_NAME)
    cursor = conn.cursor()
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        cursor.execute("""
            UPDATE tasks
            SET
                admin_response = ?,
                status = 'Responded',
                response_timestamp = ?
            WHERE
                task_id = ?
        """, (response, task_id,timestamp))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error updating admin response: {e}")
    finally:
        conn.close()


def get_chat_history(user_id, line_id):
    """
    Fetches the entire chat history for a specific LINE user.
    Args:
        user_id (str): The ID of the store.
        line_id (str): The ID of the LINE user.
    Returns:
        list: A list of dictionaries, each representing a message/task.
    """
    conn = sqlite3.connect(DB_FILE_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM tasks WHERE user_id = ? AND line_id = ? ORDER BY timestamp ASC", (user_id, line_id))
        tasks = cursor.fetchall()
        return [dict(task) for task in tasks]
    except sqlite3.Error as e:
        print(f"Database error fetching chat history: {e}")
        return []
    finally:
        conn.close()

def get_chat_threads_by_status(user_id, status):
    """
    Fetches a list of unique line_ids where the latest task has the specified status.
    This is used to group chats by the status of their most recent message.
    """
    conn = sqlite3.connect(DB_FILE_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT
                t1.*
            FROM
                tasks t1
            JOIN
                (
                    SELECT
                        line_id,
                        MAX(timestamp) AS max_timestamp
                    FROM
                        tasks
                    WHERE
                        user_id = ?
                    GROUP BY
                        line_id
                ) AS t2 ON t1.line_id = t2.line_id AND t1.timestamp = t2.max_timestamp
            WHERE
                t1.user_id = ? AND t1.status = ?
            ORDER BY
                t1.timestamp DESC
        """, (user_id, user_id, status))
        
        threads = cursor.fetchall()
        return [dict(thread) for thread in threads]
    except sqlite3.Error as e:
        print(f"Database error fetching chat threads: {e}")
        return []
    finally:
        conn.close()

def get_chat_history(user_id, line_id):
    """Fetches the entire chat history for a specific LINE user."""
    conn = sqlite3.connect(DB_FILE_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM tasks WHERE user_id = ? AND line_id = ? ORDER BY timestamp ASC", (user_id, line_id))
        tasks = cursor.fetchall()
        return [dict(task) for task in tasks]
    except sqlite3.Error as e:
        print(f"Database error fetching chat history: {e}")
        return []
    finally:
        conn.close()