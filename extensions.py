# extensions.py
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_bcrypt import Bcrypt

jwt = JWTManager()
bcrypt = Bcrypt()
socketio = SocketIO()