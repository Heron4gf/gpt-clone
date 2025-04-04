# app/models/registration_key.py
from app.utils.db import get_db
import datetime
import secrets
import string

class RegistrationKey:
    def __init__(self, id=None, key_value=None, is_used=False, used_by=None, 
                 created_at=None, used_at=None):
        self.id = id
        self.key_value = key_value
        self.is_used = is_used
        self.used_by = used_by
        self.created_at = created_at
        self.used_at = used_at
    
    @staticmethod
    def generate_key(length=16):
        """Generate a random alphanumeric key."""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def create():
        """Create a new registration key."""
        db = get_db()
        key_value = RegistrationKey.generate_key()
        
        db.execute(
            'INSERT INTO registration_keys (key_value) VALUES (?)',
            (key_value,)
        )
        db.commit()
        
        # Return the created key
        key = db.execute(
            'SELECT * FROM registration_keys WHERE key_value = ?', 
            (key_value,)
        ).fetchone()
        
        return RegistrationKey(
            id=key['id'],
            key_value=key['key_value'],
            is_used=bool(key['is_used']),
            used_by=key['used_by'],
            created_at=key['created_at'],
            used_at=key['used_at']
        )
    
    @staticmethod
    def get_by_value(key_value):
        """Get a registration key by its value."""
        db = get_db()
        key = db.execute(
            'SELECT * FROM registration_keys WHERE key_value = ?', 
            (key_value,)
        ).fetchone()
        
        if not key:
            return None
            
        return RegistrationKey(
            id=key['id'],
            key_value=key['key_value'],
            is_used=bool(key['is_used']),
            used_by=key['used_by'],
            created_at=key['created_at'],
            used_at=key['used_at']
        )
    
    @staticmethod
    def get_all():
        """Get all registration keys."""
        db = get_db()
        keys = db.execute('SELECT * FROM registration_keys ORDER BY created_at DESC').fetchall()
        
        return [RegistrationKey(
            id=key['id'],
            key_value=key['key_value'],
            is_used=bool(key['is_used']),
            used_by=key['used_by'],
            created_at=key['created_at'],
            used_at=key['used_at']
        ) for key in keys]
    
    def mark_as_used(self, user_id):
        """Mark this key as used by a specific user."""
        if self.is_used:
            return False
            
        db = get_db()
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        db.execute(
            '''UPDATE registration_keys 
               SET is_used = 1, used_by = ?, used_at = ? 
               WHERE id = ?''',
            (user_id, now, self.id)
        )
        db.commit()
        
        self.is_used = True
        self.used_by = user_id
        self.used_at = now
        
        return True
    
    def to_dict(self):
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'key_value': self.key_value,
            'is_used': self.is_used,
            'used_by': self.used_by,
            'created_at': self.created_at,
            'used_at': self.used_at
        }
