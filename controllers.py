from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity, create_access_token
from bson import ObjectId
from datetime import datetime, timezone, timedelta
from models import (get_user, get_recent_sessions, get_recent_checkins, create_user,open_session, close_session, record_attendance, get_weekly_attendance,get_student_attendance, get_courses, is_session_active, check_password, get_session_status)

def index_controller():
    user_id = get_jwt_identity()
    user = get_user(user_id)
    
    if not user:
        return jsonify({"msg": "User not found"}), 404

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

    if user['role'] == 'lecturer':
        recent_sessions = get_recent_sessions(user_id, seven_days_ago)
        return jsonify({
            "role": "lecturer",
            "recent_sessions": recent_sessions
        })
    elif user['role'] == 'student':
        recent_checkins = get_recent_checkins(user_id, seven_days_ago)
        return jsonify({
            "role": "student",
            "recent_checkins": recent_checkins
        })
    else:
        return jsonify({"msg": "Invalid user role"}), 400

def register_controller():
    # Extract data from request
    data = request.json
    # Create user
    user_id = create_user(data)
    return jsonify({"msg": "User created successfully", "user_id": str(user_id)}), 201

def login_controller():
    email = request.json.get('email', None)
    password = request.json.get('password', None)
    user = get_user(email=email)
    if user and check_password(user['password'], password):
        user['_id'] = str(user['_id'])
        access_token = create_access_token(identity=str(user['_id']))
        return jsonify(access_token=access_token, user=user), 200
    return jsonify({"msg": "Invalid email or password"}), 401

def manage_session_controller():
    user_id = get_jwt_identity()
    user = get_user(user_id)
    if user['role'] != 'lecturer':
        return jsonify({"msg": "Unauthorized"}), 403
    course_code = request.json.get('course_code')
    action = request.json.get('action')
    course_name = request.json.get('course_name')
    if action == 'open':
        open_session(user_id, course_code, course_name)
        return jsonify({"msg": "Session opened successfully"}), 200
    elif action == 'close':
        close_session(user_id, course_code, course_name)
        return jsonify({"msg": "Session closed successfully"}), 200
    else:
        return jsonify({"msg": "Invalid action"}), 400

def check_attendance_controller():
    user_id = get_jwt_identity()
    user = get_user(user_id)
    if user['role'] != 'student':
        return jsonify({"msg": "Unauthorized"}), 403
    course_code = request.json.get('course_code')
    course_name = request.json.get('course_name')
    location = request.json.get('location')
    if not is_session_active(course_code):
        return jsonify({"msg": "No active session for this course"}), 400
    record_attendance(user_id, course_code,course_name, location)
    return jsonify({"msg": "Attendance recorded successfully"}), 200

def get_student_attendance_controller():
    user_id = get_jwt_identity()
    user = get_user(user_id)
    if user['role'] != 'student':
        return jsonify({"msg": "Unauthorized"}), 403
    course_code = request.args.get('course_code')
    weekly_attendance = get_weekly_attendance(user_id, course_code)
    return jsonify(weekly_attendance)

def get_lecturer_attendance_controller():
    user_id = get_jwt_identity()
    user = get_user(user_id)
    if user['role'] != 'lecturer':
        return jsonify({"msg": "Unauthorized"}), 403
    course_code = request.args.get('course_code')
    student_attendance = get_student_attendance(course_code)
    return jsonify(student_attendance)

def get_student_courses_controller():
    user_id = get_jwt_identity()
    user = get_user(user_id)
    if user['role'] != 'student':
        return jsonify({"msg": "Unauthorized"}), 403
    programme = request.args.get('programme')
    year = request.args.get('year')
    data = get_courses('student_courses', programme=programme, year=year)
    for obj in data:
        if '_id' in obj:
            obj['_id'] = str(obj['_id'])

        courses = obj['courses']
        for course in courses:
            if course:
                session_status = get_session_status(course['course_code'])
                course['session_status'] = session_status
            else: 
                course['session_status'] = 'unknown'
    return jsonify(courses)



def get_lecturer_courses_controller():
    user_id = get_jwt_identity()
    user = get_user(user_id)
    if user['role'] != 'lecturer':
        return jsonify({"msg": "Unauthorized"}), 403
    school_id = request.args.get('school_id')
    courses = get_courses('lecturer_courses', school_id=school_id)
    return jsonify(courses)