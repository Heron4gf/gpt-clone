# app/utils/db.py
import sqlite3
import os
from flask import g, current_app

def get_db():
    """Get a connection to the SQLite database."""
    if 'db' not in g:
        # Ensure the instance directory exists
        db_path = current_app.config['DATABASE_PATH']
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Connect to the database
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row  # Return rows as dict-like objects
    
    return g.db

def close_db(e=None):
    """Close the database connection at the end of request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

# app/utils/db.py (update init_db function)

def init_db():
    """Initialize the database tables."""
    db = get_db()
    
    # Create users table (without email)
    db.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create registration keys table
    db.execute('''
    CREATE TABLE IF NOT EXISTS registration_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_value TEXT UNIQUE NOT NULL,
        is_used BOOLEAN DEFAULT 0,
        used_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        used_at TIMESTAMP,
        FOREIGN KEY (used_by) REFERENCES users (id)
    )
    ''')
    
    # Create conversations table (unchanged)
    db.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Create messages table (unchanged)
    db.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversations (id)
    )
    ''')
    
    db.commit()


def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)
