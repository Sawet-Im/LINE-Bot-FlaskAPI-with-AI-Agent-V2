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
                id INTEGER PRIMARY KEY,
                menu_name TEXT NOT NULL,
                price REAL NOT NULL
            )
        ''')

        # Create promotions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS promotions (
                id INTEGER PRIMARY KEY,
                promo_code TEXT NOT NULL,
                description TEXT NOT NULL
            )
        ''')

        # Create stores table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stores (
                id INTEGER PRIMARY KEY,
                store_name TEXT NOT NULL,
                status TEXT NOT NULL,
                location TEXT NOT NULL
            )
        ''')
        
        # Create tasks table for bot responses and admin actions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                task_id INTEGER PRIMARY KEY,
                line_id TEXT NOT NULL,
                user_message TEXT NOT NULL,
                ai_response TEXT,
                admin_response TEXT,
                reply_token TEXT NOT NULL,
                status TEXT NOT NULL,
                timestamp TEXT NOT NULL
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
            ('สาขาพระราม 9', 'Open', 'อาคารฟอร์จูนทาวน์ ชั้น 2'),
            ('สาขาสุขุมวิท 21', 'Closed', 'อาคาร GMM Grammy Place'),
            ('สาขาพญาไท', 'Open', 'อาคาร CP Tower')
        ]
        cursor.executemany("INSERT INTO stores (store_name, status, location) VALUES (?, ?, ?)", stores_data)
        conn.commit()

def add_new_task(line_id, reply_token, user_message):
    """Adds a new task to the tasks table with 'Pending' status."""
    conn = sqlite3.connect(DB_FILE_NAME)
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().isoformat()
    try:
        cursor.execute('''
            INSERT INTO tasks (line_id, user_message, reply_token, status, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (line_id, user_message, reply_token, 'Pending', timestamp))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error adding new task: {e}")
    finally:
        conn.close()

def get_tasks_by_status(status):
    """Fetches tasks from the tasks table based on their status."""
    conn = sqlite3.connect(DB_FILE_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM tasks WHERE status = ? ORDER BY timestamp DESC", (status,))
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

def update_task_response(task_id, new_ai_response):
    """Updates the AI's response for a specific task."""
    conn = sqlite3.connect(DB_FILE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE tasks SET ai_response = ? WHERE task_id = ?", (new_ai_response, task_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error updating AI response: {e}")
    finally:
        conn.close()

def update_admin_response(task_id, new_admin_response):
    """Updates the admin's edited response for a specific task."""
    conn = sqlite3.connect(DB_FILE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE tasks SET admin_response = ? WHERE task_id = ?", (new_admin_response, task_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error updating admin response: {e}")
    finally:
        conn.close()
