from flask import Blueprint
from flask_jwt_extended import jwt_required
from controllers import (index_controller, register_controller, login_controller, manage_session_controller, check_attendance_controller,get_student_attendance_controller, get_lecturer_attendance_controller,get_student_courses_controller, get_lecturer_courses_controller, set_student_location_controller, set_lecturer_location_controller, get_recent_attendance_controller)

main = Blueprint('main', __name__)

# route for recent history
@main.route('/', methods=['GET'])
@jwt_required()
def index():
    return index_controller()

# route for registration
@main.route('/register', methods=['POST'])
def register():
    return register_controller()

# route for login
@main.route('/login', methods=['POST'])
def login():
    return login_controller()

# route for open/close session
@main.route('/session', methods=['POST'])
@jwt_required()
def manage_session():
    return manage_session_controller()

# route for setting lecturer location
@main.route('/lecturer/location', methods=['POST'])
@jwt_required()
def set_lecturer_location():
    return set_lecturer_location_controller()
 
# student route for taking attendance
@main.route('/attendance', methods=['POST'])
@jwt_required()
def check_attendance():
    return check_attendance_controller()

# student route for updating location
@main.route('/student/location', methods=['POST'])
@jwt_required()
def set_student_location():
    return set_student_location_controller()

# student route for checking attendance records
@main.route('/student/attendance', methods=['GET'])
@jwt_required()
def get_student_attendance():
    return get_student_attendance_controller()

# lecturer route for checking records of students attendance
@main.route('/lecturer/attendance', methods=['GET'])
@jwt_required()
def get_lecturer_attendance():
    return get_lecturer_attendance_controller()

# route for fetching student courses
@main.route('/student/courses', methods=['GET'])
@jwt_required()
def get_student_courses():
    return get_student_courses_controller()

# route for fetching lecturer course
@main.route('/lecturer/courses', methods=['GET'])
@jwt_required()
def get_lecturer_courses():
    return get_lecturer_courses_controller()


# route for recent attendance
@main.route('/student/recent-attendance', methods=['GET'])
@jwt_required()
def get_recent_attendance():
    return get_recent_attendance_controller()