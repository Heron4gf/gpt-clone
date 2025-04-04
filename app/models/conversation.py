# app/models/conversation.py
from app.utils.db import get_db

class Conversation:
    def __init__(self, id=None, user_id=None, title=None, created_at=None, updated_at=None, messages=None):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.created_at = created_at
        self.updated_at = updated_at
        self.messages = messages or []
        
    @staticmethod
    def create(user_id, title="New Conversation"):
        db = get_db()
        cursor = db.execute(
            'INSERT INTO conversations (user_id, title) VALUES (?, ?)',
            (user_id, title)
        )
        db.commit()
        return Conversation.get_by_id(cursor.lastrowid)
    
    @staticmethod
    def get_by_id(conversation_id):
        db = get_db()
        conversation = db.execute(
            'SELECT * FROM conversations WHERE id = ?', (conversation_id,)
        ).fetchone()
        
        if not conversation:
            return None
            
        from app.models.message import Message
        messages = Message.get_by_conversation_id(conversation_id)
        
        return Conversation(
            id=conversation['id'],
            user_id=conversation['user_id'],
            title=conversation['title'],
            created_at=conversation['created_at'],
            updated_at=conversation['updated_at'],
            messages=messages
        )
    
    @staticmethod
    def get_by_user_id(user_id):
        db = get_db()
        conversations = db.execute(
            'SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC', 
            (user_id,)
        ).fetchall()
        
        result = []
        for conv in conversations:
            from app.models.message import Message
            messages = Message.get_by_conversation_id(conv['id'])
            
            result.append(Conversation(
                id=conv['id'],
                user_id=conv['user_id'],
                title=conv['title'],
                created_at=conv['created_at'],
                updated_at=conv['updated_at'],
                messages=messages
            ))
        
        return result
    
    def update_title(self, new_title):
        db = get_db()
        db.execute(
            'UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (new_title, self.id)
        )
        db.commit()
        self.title = new_title
        return self
        
    def delete(self):
        db = get_db()
        db.execute('DELETE FROM messages WHERE conversation_id = ?', (self.id,))
        db.execute('DELETE FROM conversations WHERE id = ?', (self.id,))
        db.commit()
        
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'messages': [message.to_dict() for message in self.messages]
        }
