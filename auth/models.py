# auth/models.py
from database import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from bson.objectid import ObjectId

class User:
    def __init__(self, username, password, email):
        self.username = username
        self.password = password
        self.email = email

    def save(self):
        hashed_password = generate_password_hash(self.password)
        db.users.insert_one({
            'username': self.username,
            'password': hashed_password,
            'email': self.email
        })

    @staticmethod
    def get_by_username(username):
        return db.users.find_one({'username': username})

    @staticmethod
    def get_by_id(user_id):
        return db.users.find_one({'_id': ObjectId(user_id)})

    def check_password(self, password):
        user_data = self.get_by_username(self.username)
        if user_data:
            return check_password_hash(user_data['password'], password)
        return False

    def generate_access_token(self):
        user_data = self.get_by_username(self.username)
        if user_data:
            return create_access_token(identity=str(user_data['_id']))
        return None