import cv2
from flask import request
import numpy as np
from flask_socketio import emit
from app import socketio

# You'll need to implement or use libraries for these functions
from liveness_utils import detect_blinks, detect_head_movements

REQUIRED_BLINKS = 2
REQUIRED_HEAD_MOVEMENTS = 2
FRAME_HISTORY = 30

sessions = {}

@socketio.on('liveness_frame')
def handle_liveness_frame(data):
    # Convert base64 image to numpy array
    frame = cv2.imdecode(np.frombuffer(data['image'], np.uint8), cv2.IMREAD_COLOR)
    
    # Get user's session (you need to implement session management)
    session = get_user_session(request.sid)
    session['frames'].append(frame)
    session['frames'] = session['frames'][-FRAME_HISTORY:]  # Keep only recent frames

    # Perform detections
    blinks = detect_blinks(session['frames'])
    head_movements = detect_head_movements(session['frames'])

    # Update counts
    session['blink_count'] += blinks
    session['head_movement_count'] += head_movements

    # Check if liveness criteria are met
    if session['blink_count'] >= REQUIRED_BLINKS and session['head_movement_count'] >= REQUIRED_HEAD_MOVEMENTS:
        emit('liveness_result', {
            'complete': True,
            'success': True,
            'message': 'Liveness check passed'
        })
    else:
        # Send intermediate results
        emit('liveness_result', {
            'complete': False,
            'blinks': session['blink_count'],
            'headMovements': session['head_movement_count']
        })

def get_user_session(sid):
    if sid not in sessions:
        sessions[sid] = {
            'frames': [],
            'blink_count': 0,
            'head_movement_count': 0
        }
    return sessions[sid]