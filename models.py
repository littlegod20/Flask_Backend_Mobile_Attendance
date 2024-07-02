from flask import current_app
from bson import ObjectId
from datetime import datetime, timezone

def get_mongo():
    if 'pymongo' not in current_app.extensions:
        raise RuntimeError("PyMongo extension not found")
    return current_app.extensions['pymongo']


def get_user(user_id=None, email=None):
    if user_id:
        return get_mongo().db.users.find_one({'_id': ObjectId(user_id)})
    elif email:
        return get_mongo().db.users.find_one({'email': email})

def check_password(hashed_password, password):
    return current_app.bcrypt.check_password_hash(hashed_password, password)

def get_recent_sessions(user_id, seven_days_ago):
    return list(get_mongo().db.sessions.find(
        {
            'lecturer_id': ObjectId(user_id),
            'timestamp': {'$gte': seven_days_ago},
            'active': False

        },
        {
            '_id': False,
            'course_name': True,
            'course_code': True,
            'timestamp': True,
            'active': True
        }
    ).sort('timestamp', -1).limit(5))

def get_recent_checkins(user_id, seven_days_ago):
    return list(get_mongo().db.attendance.find(
        {
            'student_id': ObjectId(user_id),
            'timestamp': {'$gte': seven_days_ago}
        },
        {
            '_id': False,
            'course_name': True,
            'course_code': True,
            'timestamp': True
        }
    ).sort('timestamp', -1).limit(5))

def create_user(data):
    users = get_mongo().db.users
    
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    school_id = data.get('school_id')
    role = data.get('role')
    year = data.get('year')
    faculty = data.get('faculty')
    programme = data.get('programme')
    
    if not email or not password or not role:
        raise ValueError("Missing email or password, or role")
    
    if users.find_one({'email': email}):
        raise ValueError("Email already exists")
    
    hashed_password = current_app.bcrypt.generate_password_hash(password).decode('utf-8')
    
    user_data = {
        'name': name,
        'password': hashed_password,
        'email': email,
        'school_id': school_id,
        'role': role,
        'year': year or None,
        'faculty': faculty,
        'programme': programme
    }
    
    user_id = users.insert_one(user_data).inserted_id
    return user_id

def open_session(user_id, course_code, course_name):
    get_mongo().db.sessions.insert_one({
        'lecturer_id': ObjectId(user_id),
        'course_code': course_code,
        'course_name': course_name,
        'timestamp': datetime.now(timezone.utc),
        'active': True
    })

def close_session(user_id, course_code, course_name):
    get_mongo().db.sessions.update_one(
        {
            'lecturer_id': ObjectId(user_id),
            'course_code': course_code,
            'course_name': course_name,
            'active': True
        },
        {
            '$set': {'active': False, 'end_time': datetime.now(timezone.utc)}
        }
    )

def is_session_active(course_code):
    return get_mongo().db.sessions.find_one({'course_code': course_code, 'active': True}) is not None

def record_attendance(user_id, course_code,course_name, location):
    get_mongo().db.attendance.insert_one({
        'student_id': ObjectId(user_id),
        'course_code': course_code,
        'course_name': course_name,
        'timestamp': datetime.now(timezone.utc),
        'location': location
    })

def get_weekly_attendance(user_id, course_code):
    semester_start_date = datetime(2024, 5, 12)
    pipeline = [
        {'$match': {'student_id': ObjectId(user_id), 'course_code': course_code}},
        {'$addFields': {
            'week_of_semester': {
                '$ceil': {
                    '$divide': [
                        {'$subtract': ['$timestamp', semester_start_date]},
                        1000 * 60 * 60 * 24 * 7
                    ]
                }
            }
        }},
        {'$group': {
            '_id': {'week': '$week_of_semester'},
            'count': {'$sum': 1}
        }},
        {'$lookup': {
            'from': 'sessions',
            'let': {'week': '$_id.week', 'course_code': course_code},
            'pipeline': [
                {'$match': {'$expr': {'$and': [
                    {'$eq': ['$course_code', '$$course_code']},
                    {'$eq': [
                        {'$ceil': {
                            '$divide': [
                                {'$subtract': ['$timestamp', semester_start_date]},
                                1000 * 60 * 60 * 24 * 7
                            ]
                        }},
                        '$$week'
                    ]}
                ]}}},
                {'$group': {'_id': None, 'total_sessions': {'$sum': 1}}}
            ],
            'as': 'session_info'
        }},
        {'$unwind': '$session_info'},
        {'$project': {
            'week': '$_id.week',
            'attendance': {'$concat': [{'$toString': '$count'}, '/', {'$toString': '$session_info.total_sessions'}]},
            'attendance_fraction': {
                '$divide': ['$count', '$session_info.total_sessions']
            }
        }},
        {'$addFields': {
            'code': {
                '$cond': [
                    {'$gte': ['$attendance_fraction', 0.75]}, 'green',
                    {'$cond': [
                        {'$gte': ['$attendance_fraction', 0.5]}, 'yellow', 'red'
                    ]}
                ]
            }
        }},
        {'$sort': {'week': 1}}
    ]

    return list(get_mongo().db.attendance.aggregate(pipeline))

def get_student_attendance(course_code):
    pipeline = [
        {'$match': {'course_code': course_code}},
        {'$group': {
            '_id': '$student_id',
            'attendance_count': {'$sum': 1}
        }},
        {'$lookup': {
            'from': 'users',
            'localField': '_id',
            'foreignField': '_id',
            'as': 'student_info'
        }},
        {'$unwind': '$student_info'},
        {'$lookup': {
            'from': 'sessions',
            'let': {'course_code': course_code},
            'pipeline': [
                {'$match':
                    {'$expr':
                        {'$and': [
                            {'$eq': ['$course_code', '$$course_code']},
                            {'$eq': ['$active', False]}  # Only count closed sessions
                        ]}
                    }
                },
                {'$count': 'total_sessions'}
            ],
            'as': 'sessions'
        }},
        {'$unwind': '$sessions'},
        {'$project': {
            '_id': 0,
            'student_name': '$student_info.name',
            'attendance_count': 1,
            'total_sessions': '$sessions.total_sessions',
            'attendance_percentage': {
                '$multiply': [
                    {'$divide': ['$attendance_count', '$sessions.total_sessions']},
                    100
                ]
            }
        }}
    ]
    
    return list(get_mongo().db.attendance.aggregate(pipeline))

def get_courses(collection, **kwargs):
    return list(get_mongo().db[collection].find(kwargs, {'_id': False}))


def get_session_status(course_code):
    session = get_mongo().db.sessions.find_one(
        {'course_code': course_code, 'active': True},
        {'_id': False, 'active': True}
    )
    return 'open' if session else 'closed'
