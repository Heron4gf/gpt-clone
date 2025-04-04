# setup.py
import os
import sys
import sqlite3
from werkzeug.security import generate_password_hash
import secrets
import string

def generate_key(length=16):
    """Generate a random alphanumeric key."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def setup_database():
    """Initialize the database, create admin user, and generate initial keys."""
    # Ensure the instance directory exists
    os.makedirs('instance', exist_ok=True)
    
    # Connect to the database
    db_path = os.path.join('instance', 'chatgpt_clone.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables as in init_db() function
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
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
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversations (id)
    )
    ''')
    
    # Create admin user if it doesn't exist
    admin_username = 'admin'
    admin_password = 'admin123'  # Change this in production!
    
    # Check if admin user already exists
    cursor.execute('SELECT id FROM users WHERE username = ?', (admin_username,))
    admin_exists = cursor.fetchone()
    
    if not admin_exists:
        password_hash = generate_password_hash(admin_password)
        cursor.execute(
            'INSERT INTO users (username, password_hash) VALUES (?, ?)',
            (admin_username, password_hash)
        )
        print(f"Admin user created with username: {admin_username} and password: {admin_password}")
    else:
        print("Admin user already exists")
    
    # Generate some initial keys
    num_keys = 5
    keys = []
    
    for _ in range(num_keys):
        key_value = generate_key()
        try:
            cursor.execute('INSERT INTO registration_keys (key_value) VALUES (?)', (key_value,))
            keys.append(key_value)
        except sqlite3.IntegrityError:
            # Key already exists, try another one
            continue
    
    # Write keys to keys.txt file
    try:
        with open('keys.txt', 'w') as f:
            for key in keys:
                f.write(f"{key}\n")
        print(f"Generated {len(keys)} registration keys and saved to keys.txt")
    except Exception as e:
        print(f"Error writing keys to file: {e}")
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Setup completed successfully!")

if __name__ == "__main__":
    setup_database()
