import cv2
import dlib
import numpy as np
from scipy.spatial import distance as dist

# Initialize dlib's face detector and facial landmark predictor
face_detector = dlib.get_frontal_face_detector()
landmark_predictor = dlib.shape_predictor("./shape_predictor_68_face_landmarks.dat")

def eye_aspect_ratio(eye):
    # Compute the euclidean distances between the two sets of vertical eye landmarks
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])
    # Compute the euclidean distance between the horizontal eye landmarks
    C = dist.euclidean(eye[0], eye[3])
    # Compute the eye aspect ratio
    ear = (A + B) / (2.0 * C)
    return ear

def detect_blinks(frames):
    EYE_AR_THRESH = 0.3
    EYE_AR_CONSEC_FRAMES = 3
    
    blink_counter = 0
    frame_counter = 0
    
    for frame in frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_detector(gray, 0)
        
        for face in faces:
            shape = landmark_predictor(gray, face)
            shape = np.array([(shape.part(i).x, shape.part(i).y) for i in range(68)])
            
            left_eye = shape[42:48]
            right_eye = shape[36:42]
            left_ear = eye_aspect_ratio(left_eye)
            right_ear = eye_aspect_ratio(right_eye)
            
            ear = (left_ear + right_ear) / 2.0
            
            if ear < EYE_AR_THRESH:
                frame_counter += 1
            else:
                if frame_counter >= EYE_AR_CONSEC_FRAMES:
                    blink_counter += 1
                frame_counter = 0
    
    return blink_counter

def detect_head_movements(frames):
    MOVEMENT_THRESHOLD = 20  # Adjust as needed
    
    movement_counter = 0
    prev_shape = None
    
    for frame in frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_detector(gray, 0)
        
        if len(faces) > 0:
            shape = landmark_predictor(gray, faces[0])
            shape = np.array([(shape.part(i).x, shape.part(i).y) for i in range(68)])
            
            if prev_shape is not None:
                # Calculate the movement of specific landmarks (e.g., nose tip)
                movement = np.linalg.norm(shape[30] - prev_shape[30])
                
                if movement > MOVEMENT_THRESHOLD:
                    movement_counter += 1
            
            prev_shape = shape
    
    return movement_counter