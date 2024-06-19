# chat/events.py
from flask_socketio import Namespace, emit, join_room, leave_room
from flask_jwt_extended import jwt_required, get_jwt_identity

from auth.models import User
from chat.models import ChatRoom, Message

class ChatNamespace(Namespace):
    @jwt_required()
    def on_connect(self):
        user_id = get_jwt_identity()
        user = User.get_by_id(user_id)
        if not user:
            return False  # reject the connection
        print(f"User {user['username']} connected")

    @jwt_required()
    def on_disconnect(self):
        print("Client disconnected")

    @jwt_required()
    def on_ping(self):
        emit('pong')

    @jwt_required()
    def on_join(self, data):
        user_id = get_jwt_identity()
        user = User.get_by_id(user_id)
        room = data['room']
        join_room(room)
        emit('status', {'msg': user['username'] + ' has entered the room.'}, room=room)

    @jwt_required()
    def on_leave(self, data):
        user_id = get_jwt_identity()
        user = User.get_by_id(user_id)
        room = data['room']
        leave_room(room)
        emit('status', {'msg': user['username'] + ' has left the room.'}, room=room)

    @jwt_required()
    def on_message(self, data):
        user_id = get_jwt_identity()
        user = User.get_by_id(user_id)
        room = data['room']
        message_content = data['message']

        message = Message(content=message_content, sender=str(user['_id']), chat_room=room)
        message.save()

        emit('message', {
            'msg': message_content,
            'username': user['username'],
            'timestamp': message.timestamp.isoformat()
        }, room=room)