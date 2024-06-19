from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, disconnect
from flask_jwt_extended import decode_token
from functools import wraps
from dotenv import load_dotenv
import os
from flask_cors import CORS

from extensions import jwt, socketio, bcrypt
from database import db

def jwt_required_cookie(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.cookies.get('access_token')  # 'access_token' is the cookie name
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            # Decode and verify the JWT token
            decode_token(token)
        except Exception as e:
            return jsonify({'message': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')

    # Initialize extensions
    jwt.init_app(app)
    bcrypt.init_app(app)

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'msg': 'The token has expired',
            'error': 'token_expired'
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            'msg': 'Signature verification failed',
            'error': 'invalid_token'
        }), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            'msg': 'Request does not contain an access token',
            'error': 'authorization_required'
        }), 401

    # Import blueprints
    from auth.routes import bp as auth_bp
    from chat.routes import bp as chat_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)

    # Initialize SocketIO with the app
    socketio.init_app(app, cors_allowed_origins="*", ping_interval=25, ping_timeout=60)

    # Import SocketIO event handlers
    from chat.events import ChatNamespace

    # Register the ChatNamespace
    socketio.on_namespace(ChatNamespace('/chat'))

    app.template_folder = 'templates'

    CORS(app)

    @app.route('/')
    def home():
        return render_template('home.html', login_url='/auth/login')

    return app

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, debug=True)
