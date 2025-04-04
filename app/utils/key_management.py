# app/utils/key_management.py
import os
from app.models.registration_key import RegistrationKey

def load_keys_from_file(file_path='keys.txt'):
    """Load registration keys from a file and add them to the database."""
    try:
        if not os.path.exists(file_path):
            return False, "Keys file not found."
        
        with open(file_path, 'r') as f:
            keys = [line.strip() for line in f if line.strip()]
        
        # Add each key to the database if it doesn't already exist
        added_count = 0
        for key_value in keys:
            # Check if the key already exists
            key = RegistrationKey.get_by_value(key_value)
            
            if not key:
                # Create a new key record with the pre-defined value
                db = get_db()
                db.execute(
                    'INSERT INTO registration_keys (key_value) VALUES (?)',
                    (key_value,)
                )
                db.commit()
                added_count += 1
                
        return True, f"Added {added_count} keys to the database."
        
    except Exception as e:
        return False, f"Error loading keys: {str(e)}"
