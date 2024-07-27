from flask import Flask
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager
from datetime import timedelta
from routes import main
from flask_socketio import SocketIO

def create_app():
    app = Flask(__name__)
    CORS(app)
    bcrypt = Bcrypt(app)
    app.bcrypt = bcrypt

    # Mongo configuration
    app.config['MONGO_URI'] = 'mongodb://localhost:27017/attendance_management'
    mongo = PyMongo(app)

    app.extensions['pymongo'] = mongo

    # JWT configuration
    app.config['JWT_SECRET_KEY'] = 'my-secret-key'
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)
    jwt = JWTManager(app)

    app.register_blueprint(main)

    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*")
    app.socketio = socketio 

    return app, socketio

app, socketio = create_app()

# Import WebSocket routes
from websocket_routes import *

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port='8000', debug=True)
