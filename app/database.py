import os
import sqlite3

DATABASE_PATH = os.getenv("DATABASE_PATH", "app.db")

def get_db_connection():
    # Ensure the parent directory exists (e.g. if DATABASE_PATH is /app/data/app.db)
    db_dir = os.path.dirname(DATABASE_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # Create api_keys table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        key_value TEXT NOT NULL UNIQUE,
        rate_limit INTEGER NOT NULL, -- requests per minute (RPM)
        is_active INTEGER DEFAULT 1, -- 1 = active, 0 = inactive
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create usage_logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usage_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_key_id INTEGER,
        api_key_name TEXT, -- denormalized for durability if api_key is deleted
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        endpoint TEXT NOT NULL,
        ip_address TEXT NOT NULL,
        status_code INTEGER NOT NULL,
        characters_count INTEGER DEFAULT 0,
        voice TEXT,
        duration_seconds REAL DEFAULT 0.0,
        error_message TEXT,
        FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE SET NULL
    )
    """)
    
    conn.commit()
    conn.close()

def log_request(api_key_id, api_key_name, endpoint, ip_address, status_code, characters_count=0, voice=None, duration_seconds=0.0, error_message=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO usage_logs (api_key_id, api_key_name, endpoint, ip_address, status_code, characters_count, voice, duration_seconds, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (api_key_id, api_key_name, endpoint, ip_address, status_code, characters_count, voice, duration_seconds, error_message))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging request to database: {e}")

