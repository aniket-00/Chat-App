# chat/models.py
from database import db
from bson.objectid import ObjectId
from datetime import datetime

class ChatRoom:
    def __init__(self, name, participants=[]):
        self.name = name
        self.participants = participants

    def save(self):
        result = db.chat_rooms.insert_one({
            'name': self.name,
            'participants': self.participants
        })
        return result.inserted_id

    @staticmethod
    def get_by_id(room_id):
        return db.chat_rooms.find_one({'_id': ObjectId(room_id)})

    @staticmethod
    def find_by_participant(user):
        return db.chat_rooms.find({'participants': user})

class Message:
    def __init__(self, content, sender, chat_room):
        self.content = content
        self.sender = sender
        self.chat_room = chat_room
        self.timestamp = datetime.utcnow()

    def save(self):
        db.messages.insert_one({
            'content': self.content,
            'sender': self.sender,
            'chat_room': self.chat_room,
            'timestamp': self.timestamp
        })

    @staticmethod
    def get_recent_messages(chat_room, limit=50):
        return db.messages.find({'chat_room': chat_room}).sort('timestamp', -1).limit(limit)