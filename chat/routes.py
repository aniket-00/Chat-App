from flask import Blueprint, request, jsonify, redirect, url_for, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity, decode_token
from flask_socketio import join_room, leave_room, emit
from bson import ObjectId
from datetime import datetime
from app import db, socketio, jwt_required_cookie # Importing socketio instance from app
import jwt
from dotenv import load_dotenv
import os
from werkzeug.utils import secure_filename
import google.generativeai as genai
load_dotenv()

bp = Blueprint('chat', __name__, url_prefix='/chat')

SECRET_KEY = os.getenv('JWT_SECRET_KEY')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

@bp.route('/bot/chat', methods=['POST'])
@jwt_required()
def chat_with_bot():
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    try:
        response = model.generate_content(user_message)
        return jsonify({'response': response.text}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    
# Route to get all rooms for a user
@bp.route('/rooms', methods=['GET'])
@jwt_required()
def get_rooms():
    rooms = db.chat_rooms.find()
    room_data = [{'id': str(room['_id']), 'name': room['name']} for room in rooms]

    return jsonify({'rooms': room_data}), 200

# Route to create a new chat room
@bp.route('/room', methods=['POST'])
@jwt_required_cookie
def create_room():
    token = request.cookies.get('access_token')

    if not token:
        return jsonify({'message': 'Token is missing'}), 401

    try:
        decoded_token = decode_token(token)
        current_user_id = decoded_token['sub']
    except Exception as e:
        return jsonify({'message': 'Invalid token'}), 401
    
    user = db.users.find_one({'_id': ObjectId(current_user_id)})

    if not user:
        return jsonify({'message': 'User not found'}), 404

    data = request.get_json()
    room_name = data.get('name')

    if not room_name:
        return jsonify({'message': 'Room name is required'}), 400

    if db.chat_rooms.find_one({'name': room_name}):
        return jsonify({'message': 'Room name already exists'}), 400

    room_id = db.chat_rooms.insert_one({'name': room_name, 'participants': [current_user_id]}).inserted_id

    return jsonify({'message': 'Room created successfully', 'room_id': str(room_id)}), 201

# Route to retrieve a specific room details
@bp.route('/room/<room_id>', methods=['GET'])
@jwt_required_cookie
def get_room(room_id):
    token = request.cookies.get('access_token')

    if not token:
        return jsonify({'message': 'Token is missing'}), 401

    try:
        decoded_token = decode_token(token)
        user_id = decoded_token['sub']
    except Exception as e:
        return jsonify({'message': 'Invalid token'}), 401

    room = db.chat_rooms.find_one({'_id': ObjectId(room_id)})

    if not room:
        return jsonify({'message': 'Room not found'}), 404

    if user_id not in room['participants']:
        db.chat_rooms.update_one(
            {'_id': ObjectId(room_id)},
            {'$push': {'participants': user_id}}
        )

    # Fetch additional room details if needed
    room_name = room['name']

    # Redirect to room_page route with room_id
    return redirect(url_for('chat.room_page', room_id=room_id))

# Route to render the chat room page
@bp.route('/room_page/<room_id>', methods=['GET'])
@jwt_required_cookie
def room_page(room_id):
    token = request.cookies.get('access_token')

    if not token:
        return jsonify({'message': 'Token is missing'}), 401

    try:
        decoded_token = decode_token(token)
        current_user_id = decoded_token['sub']
    except Exception as e:
        return jsonify({'message': 'Invalid token'}), 401

    room = db.chat_rooms.find_one({'_id': ObjectId(room_id), 'participants': current_user_id})

    if not room:
        # If room is not found or user is not a participant, redirect to rooms page
        return redirect(url_for('chat.get_rooms'))

    user = db.users.find_one({'_id': ObjectId(current_user_id)})

    room_name = room['name']
    return render_template('chats.html', room_id=room_id, room_name=room_name, current_user=user)

# Route to retrieve messages for a specific room
@bp.route('/room/<room_id>/messages', methods=['GET'])
@jwt_required_cookie
def get_room_messages(room_id):
    room = db.chat_rooms.find_one({'_id': ObjectId(room_id)})

    if not room:
        return jsonify({'message': 'Room not found'}), 404

    messages = db.messages.find({'chat_room': room_id}).sort('timestamp', -1).limit(50)
    message_data = [{
        'id': str(message['_id']),
        'content': message['content'],
        'sender': db.users.find_one({'_id': ObjectId(message['sender'])})['username'],
        'timestamp': message['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
    } for message in messages]

    return jsonify({'messages': message_data}), 200

@bp.route('/room/<room_id>/message', methods=['POST'])
@jwt_required_cookie
def send_message(room_id):
    token = request.cookies.get('access_token')

    if not token:
        return jsonify({'message': 'Token is missing'}), 401

    try:
        decoded_token = decode_token(token)
        current_user_id = decoded_token['sub']
    except Exception as e:
        return jsonify({'message': 'Invalid token'}), 401
    
    user = db.users.find_one({'_id': ObjectId(current_user_id)})

    if not user:
        return jsonify({'message': 'User not found'}), 404

    room = db.chat_rooms.find_one({'_id': ObjectId(room_id)})
    if not room:
        return jsonify({'message': 'Room not found'}), 404

    file_url = None
    if 'file' in request.files:
        file = request.files['file']
        if file.filename == '':
            return jsonify({'message': 'No selected file'}), 400
        # if file and allowed_file(file.filename):
        #     filename = secure_filename(file.filename)
        #     file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        #     file.save(file_path)
        #     file_url = url_for('chat.uploaded_file', filename=filename, _external=True)

    message_content = request.form.get('content')
    if not message_content and not file_url:
        return jsonify({'message': 'Message content or file is required'}), 400

    message_id = db.messages.insert_one({
        'content': message_content,
        'sender': current_user_id,
        'chat_room': room_id,
        'timestamp': datetime.utcnow(),
        'file_url': file_url
    }).inserted_id

    message = db.messages.find_one({'_id': ObjectId(message_id)})
    socketio.emit('message', {
        'sender': user['username'],
        'content': message['content'],
        'file_url': message['file_url'],
        'timestamp': message['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
    }, room=room_id)

    return jsonify({'message': 'Message sent successfully'}), 201

def allowed_file(filename):
    """Check if the file type is allowed based on its extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/leave_room/<room_id>', methods=['POST'])
@jwt_required_cookie
def leave_room(room_id):
    token = request.cookies.get('access_token')

    if not token:
        return jsonify({'message': 'Token is missing'}), 401

    try:
        decoded_token = decode_token(token)
        current_user_id = decoded_token['sub']
    except Exception as e:
        return jsonify({'message': 'Invalid token'}), 401
    
    # Remove the user from the room's participants
    result = db.chat_rooms.update_one(
        {'_id': ObjectId(room_id)},
        {'$pull': {'participants': current_user_id}}
    )
    
    if result.modified_count > 0:
        return jsonify({'status': 'success', 'message': 'Left the room successfully'})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to leave the room'}), 400