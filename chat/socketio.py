from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_socketio import join_room, leave_room, emit
from flask import request
from app import socketio
from .models import ChatRoom, Message
from auth.models import User
from datetime import datetime

@socketio.on('join_room')
@jwt_required()
def on_join(data):
  room_id = data['room_id']
  current_user_id = get_jwt_identity()
  user = User.get_by_id(current_user_id)

  if not user:
    return

  join_room(room_id)
  emit('message', {'username': 'System', 'content': f'{user.username} has joined the room', 'timestamp': datetime.utcnow().isoformat()}, room=room_id)

@socketio.on('leave_room')
@jwt_required()
def on_leave(data):
    room_id = data['room_id']
    current_user_id = get_jwt_identity()
    user = User.get_by_id(current_user_id)

    leave_room(room_id)
    
    # Notify other users in the room
    emit('message', {
        'username': 'System',
        'content': f'{user.username} has left the room.',
        'timestamp': datetime.utcnow().isoformat()
    }, room=room_id)
    
    # Notify the user that they have left the room
    emit('left_room', {'status': 'success'}, to=request.sid)
    

@socketio.on('send_message')  # Changed event name to match client-side
@jwt_required()
def handle_message(data):
  room_id = data['room_id']
  message_content = data['message']
  file_url = data.get('file_url')  # Retrieve file URL if provided
  current_user_id = get_jwt_identity()
  user = User.get_by_id(current_user_id)

  if not user:
    return

  room = ChatRoom.objects(id=room_id).first()

  if not room:
    return

  message = Message(content=message_content, sender=user, chat_room=room)
  message.save()

  emit('message', {
    'username': user.username,
    'content': message_content,
    'file_url': file_url,
    'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
  }, room=room_id)

  print(f"Message received and processed: {message_content}")

  
