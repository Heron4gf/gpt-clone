# app/models/message.py
from app.utils.db import get_db

class Message:
    def __init__(self, id=None, conversation_id=None, role=None, content=None, created_at=None):
        self.id = id
        self.conversation_id = conversation_id
        self.role = role
        self.content = content
        self.created_at = created_at
    
    @staticmethod
    def create(conversation_id, role, content):
        db = get_db()
        # Update the conversation's updated_at timestamp
        db.execute(
            'UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (conversation_id,)
        )
        
        cursor = db.execute(
            'INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)',
            (conversation_id, role, content)
        )
        db.commit()
        return Message.get_by_id(cursor.lastrowid)
    
    @staticmethod
    def get_by_id(message_id):
        db = get_db()
        message = db.execute(
            'SELECT * FROM messages WHERE id = ?', (message_id,)
        ).fetchone()
        
        if message:
            return Message(
                id=message['id'],
                conversation_id=message['conversation_id'],
                role=message['role'],
                content=message['content'],
                created_at=message['created_at']
            )
        return None
    
    @staticmethod
    def get_by_conversation_id(conversation_id):
        db = get_db()
        messages = db.execute(
            'SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC',
            (conversation_id,)
        ).fetchall()
        
        return [Message(
            id=message['id'],
            conversation_id=message['conversation_id'],
            role=message['role'],
            content=message['content'],
            created_at=message['created_at']
        ) for message in messages]
    
    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'role': self.role,
            'content': self.content,
            'created_at': self.created_at
        }
