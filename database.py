import sqlite3
import os

DATABASE = 'hcmut_market.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    db.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    username TEXT UNIQUE NOT NULL, 
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL, 
                    is_premium INTEGER DEFAULT 0)''')
    
    db.execute('''CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, 
                    category TEXT NOT NULL, price TEXT NOT NULL, contact TEXT NOT NULL, 
                    image_url TEXT, user_id INTEGER, 
                    FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    db.execute('''CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    user_id INTEGER, 
                    keyword TEXT, 
                    category TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id))''')
                    
    db.execute('''CREATE TABLE IF NOT EXISTS wishlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    user_id INTEGER, 
                    item_id INTEGER,
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    FOREIGN KEY(item_id) REFERENCES items(id),
                    UNIQUE(user_id, item_id))''')
    db.commit()
    return db

def check_migrations():
    """Ensures existing databases get new columns/tables without crashing."""
    if not os.path.exists(DATABASE):
        init_db()
    else:
        db = get_db()
        try:
            db.execute('SELECT email FROM users LIMIT 1')
        except sqlite3.OperationalError:
            db.execute('ALTER TABLE users ADD COLUMN email TEXT UNIQUE')
            db.commit()
            
        try:
            db.execute('SELECT * FROM wishlist LIMIT 1')
        except sqlite3.OperationalError:
            db.execute('''CREATE TABLE IF NOT EXISTS wishlist (
                            id INTEGER PRIMARY KEY AUTOINCREMENT, 
                            user_id INTEGER, 
                            item_id INTEGER,
                            FOREIGN KEY(user_id) REFERENCES users(id),
                            FOREIGN KEY(item_id) REFERENCES items(id),
                            UNIQUE(user_id, item_id))''')
            db.commit()