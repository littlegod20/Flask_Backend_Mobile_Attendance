# from flask import Flask, request, jsonify
# from flask_cors import CORS
# from flask_bcrypt import Bcrypt
# from flask_pymongo import PyMongo
# from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
# from bson import ObjectId
# from datetime import datetime, timezone, timedelta


# app = Flask('__name__')
# CORS(app)
# bcrypt = Bcrypt(app)

# # Mongo configuration
# app.config['MONGO_URI'] = 'mongodb://localhost:27017/attendance_management'
# mongo = PyMongo(app)

# # JWT configuration
# app.config['JWT_SECRET_KEY'] = 'my-secret-key'
# app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1) # sets token expiration to 1 day
# jwt = JWTManager(app)


# # route for recent sessions or check-ins 
# @app.route('/', methods=['GET'])
# @jwt_required()
# def index():
#     user_id = get_jwt_identity()
#     user = mongo.db.users.find_one({'_id': ObjectId(user_id)})

#     if not user:
#         return jsonify({"msg": "User not found"}), 404

#     # Get data from the last 7 days
#     seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

#     if user['role'] == 'lecturer':
#         # Get recent sessions created by the lecturer
#         recent_sessions = list(mongo.db.sessions.find(
#             {
#                 'lecturer_id': ObjectId(user_id),
#                 'timestamp': {'$gte': seven_days_ago}
#             },
#             {
#                 '_id': False,
#                 'course_code': True,
#                 'timestamp': True,
#                 'active': True
#             }
#         ).sort('timestamp', -1).limit(5))  # Get the 5 most recent sessions

#         # Convert datetime objects to strings for JSON serialization
#         for session in recent_sessions:
#             session['timestamp'] = session['timestamp'].isoformat()

#         return jsonify({
#             "role": "lecturer",
#             "recent_sessions": recent_sessions
#         })

#     elif user['role'] == 'student':
#         # Get recent check-ins for the student
#         recent_checkins = list(mongo.db.attendance.find(
#             {
#                 'student_id': ObjectId(user_id),
#                 'timestamp': {'$gte': seven_days_ago}
#             },
#             {
#                 '_id': False,
#                 'course_code': True,
#                 'timestamp': True
#             }
#         ).sort('timestamp', -1).limit(5))  # Get the 5 most recent check-ins

#         # Convert datetime objects to strings for JSON serialization
#         for checkin in recent_checkins:
#             checkin['timestamp'] = checkin['timestamp'].isoformat()

#         return jsonify({
#             "role": "student",
#             "recent_checkins": recent_checkins
#         })

#     else:
#         return jsonify({"msg": "Invalid user role"}), 400



# # route for registration
# @app.route('/register', methods=['POST'])
# def register():
#       users = mongo.db.users
#       username = request.json.get('username')
#       email = request.json.get('email')
#       password = request.json.get('password')
#       school_id = request.json.get('school_id')
#       role = request.json.get('role')
#       yearOfStudy= request.json.get('yearOfStudy')
#       faculty=request.json.get('faculty')
#       programme=request.json.get('programme') # this is the department on the frontend

#       if not email or not password or not role:
#             return jsonify({"msg": "Missing email or password, or role"}), 400
#       if users.find_one({'email': email}):
#             return jsonify({"msg": "Email already exists"}), 400
      
#       hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
#       user_id = users.insert_one(
#            {
#            'username': username, 
#            'password': hashed_password,
#            'email':email, 
#            'school_id':school_id, 
#            'role':role, 
#            'yearOfStudy':yearOfStudy or None,
#            'faculty': faculty,
#            'programme':programme # also the department
#            }
#         ).inserted_id

#       return jsonify({"msg": "User created successfully", "user_id": str(user_id)}), 201


# # route for login
# @app.route('/login', methods=['POST'])
# def login():
#       users = mongo.db.users
#       email = request.json.get('email', None)
#       password = request.json.get('password', None)

#       user = users.find_one({'email': email})

#       if user and bcrypt.check_password_hash(user['password'], password):
#             access_token = create_access_token(identity=str(user['_id']))
#             return jsonify(access_token=access_token), 200
#       return jsonify({"msg": "Invalid email or password"}), 401


# # route for lecturers to open/close attendance sessions
# @app.route('/session', methods=['POST'])
# @jwt_required()
# def manage_session():
#      user_id = get_jwt_identity()
#      user = mongo.db.users.find_one({'_id': ObjectId(user_id)})

#      if user['role'] != 'lecturer':
#           return jsonify({"msg": "Unauthorized"}), 403
     
#      course_code = request.json.get('course_code')
#      action = request.json.get('action') # 'open' or 'close'

#      if action == 'open':
#           mongo.db.sessions.insert_one({
#                'lecturer_id': ObjectId(user_id),
#                'course_code': course_code,
#                'timestamp': datetime.now(timezone.utc),
#                'active': True
#           })
#           return jsonify({"msg": "Session opened successfully"}), 200
#      elif action == 'close':
#           mongo.db.sessions.update_one(
#                {
#                 'lecturer_id': ObjectId(user_id), 
#                 'course_code': course_code,
#                 'active': True
#                 },
#                {
#                   '$set': {'active':False, 'end_time': datetime.now(timezone.utc)}
#                }
#           )
#           return jsonify({"msg": "Session closed successfully"}), 200
#      else: 
#           return jsonify({"msg": "Invalid action"}), 400


# # route for student attendance check-in
# @app.route('/attendance', methods=['POST'])
# @jwt_required()
# def check_attendance():
#      user_id = get_jwt_identity()
#      user = mongo.db.users.find_one({'_id': ObjectId(user_id)})

#      if user['role'] != 'student':
#           return jsonify({"msg": "Unauthorized"}), 403
     
#      course_code = request.json.get('course_code')
#      location = request.json.get('location') # Assum this is a dict with lat and long

#      #Check if there's an active session for this course
#      active_session = mongo.db.sessions.find_one({'course_code': course_code, 'active':True})

#      if not active_session:
#           return jsonify({"msg": "No active session for this course"}), 400
     
#      # Here I would implement geolocation check
#      # For now, I'll assume it's always valid


#      # Record attendance
#      mongo.db.attendance.insert_one({
#           'student_id': ObjectId(user_id),
#           'course_code': course_code,
#           'timestamp': datetime.now(timezone.utc),
#           'location': location
#      })
#      return jsonify({"msg": "Attendance recorded successfully"}), 200


# # route for students to view their attendance
# @app.route('/student/attendance', methods=['GET'])
# @jwt_required()
# def get_student_attendnce():
#      user_id = get_jwt_identity()
#      user = mongo.db.users.find_one({'_id': ObjectId(user_id)})

#      if user['role'] != 'student':
#           return jsonify({"msg": "Unauthorized"}), 403
     
#      course_code = request.args.get('course_code')

#     # Defining the semester start date: Will be implemented in admin in future version.
#      semester_start_date = datetime(2024,5,12) 

#      # Group attendance by week
#      pipeline = [
#     {'$match': {'student_id': ObjectId(user_id), 'course_code': course_code}},
#     {'$addFields': {
#         'week_of_semester': {
#             '$ceil': {
#                 '$divide': [
#                     {'$subtract': ['$timestamp', semester_start_date]},
#                     1000 * 60 * 60 * 24 * 7
#                 ]
#             }
#         }
#     }},
#     {'$group': {
#         '_id': {'week': '$week_of_semester'},
#         'count': {'$sum': 1}
#     }},
#     {'$lookup': {
#         'from': 'sessions',
#         'let': {'week': '$_id.week', 'course_code': course_code},
#         'pipeline': [
#             {'$match': {'$expr': {'$and': [
#                 {'$eq': ['$course_code', '$$course_code']},
#                 {'$eq': [
#                     {'$ceil': {
#                         '$divide': [
#                             {'$subtract': ['$timestamp', semester_start_date]},
#                             1000 * 60 * 60 * 24 * 7
#                         ]
#                     }},
#                     '$$week'
#                 ]}
#             ]}}},
#             {'$group': {'_id': None, 'total_sessions': {'$sum': 1}}}
#         ],
#         'as': 'session_info'
#     }},
#     {'$unwind': '$session_info'},
#     {'$project': {
#         'week': '$_id.week',
#         'attendance': {'$concat': [{'$toString': '$count'}, '/', {'$toString': '$session_info.total_sessions'}]}
#     }},
#     {'$sort': {'week': 1}}
# ]

#      weekly_attendance = list(mongo.db.attendance.aggregate(pipeline))

#      return jsonify(weekly_attendance)

# # route for lecturers to view attendance
# @app.route('/lecturer/attendance', methods=['GET'])
# @jwt_required()
# def get_lecturer_attendance():
#      user_id = get_jwt_identity()
#      user = mongo.db.users.find_one({'_id': ObjectId(user_id)})

#      if user['role'] != 'lecturer':
#           return jsonify({"msg": "Unauthorized"}), 403
     
#      course_code = request.args.get('course_code')

#      # Calculate attendance percentage for each student
#      pipeline = [
#     {'$match': {'course_code': course_code}},
#     {'$group': {
#         '_id': '$student_id',
#         'attendance_count': {'$sum': 1}
#     }},
#     {'$lookup': {
#         'from': 'users',
#         'localField': '_id',
#         'foreignField': '_id',
#         'as': 'student_info'
#     }},
#     {'$unwind': '$student_info'},
#     {'$lookup': {
#         'from': 'sessions',
#         'let': {'course_code': course_code},
#         'pipeline': [
#             {'$match': 
#                 {'$expr': 
#                     {'$and': [
#                         {'$eq': ['$course_code', '$$course_code']},
#                         {'$eq': ['$active', False]}  # Only count closed sessions
#                     ]}
#                 }
#             },
#             {'$count': 'total_sessions'}
#         ],
#         'as': 'sessions'
#     }},
#     {'$unwind': '$sessions'},
#     {'$project': {
#          '_id': 0,
#         'student_name': '$student_info.username',
#         'attendance_count': 1,
#         'total_sessions': '$sessions.total_sessions',
#         'attendance_percentage': {
#             '$multiply': [
#                 {'$divide': ['$attendance_count', '$sessions.total_sessions']}, 
#                 100
#             ]
#         }
#     }}
# ]
#      student_attendance = list(mongo.db.attendance.aggregate(pipeline))

#      return jsonify(student_attendance)



# # Route for getting courses
# @app.route('/student/courses', methods=['GET'])
# @jwt_required() # this decorator ensures the route is protected and requires a valid JWT
# def get_student_courses():
#     user_id = get_jwt_identity()
#     user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    
#     if user['role'] != 'student':
#         return jsonify({"msg": "Unauthorized"}), 403
    
#     programme = request.args.get('programme')
#     yearOfStudy = request.args.get('yearOfStudy')

#     courses = list(mongo.db.student_courses.find({'programme':programme, 'yearOfStudy':yearOfStudy}, {'_id': False})) # fetch all courses from database and exclude their ids('_id':False)
#     return jsonify(courses)



# # Route to get lecturer's courses``
# @app.route('/lecturer/courses', methods=['GET'])
# @jwt_required()
# def get_lecturer_courses():
#     user_id = get_jwt_identity()
#     user = mongo.db.users.find_one({'_id': ObjectId(user_id)})

#     school_id = request.args.get('school_id')
    
#     if user['role'] != 'lecturer':
#         return jsonify({"msg": "Unauthorized"}), 403
    
#     courses = list(mongo.db.lecturer_courses.find({'school_id': school_id}, {'_id': False}))
#     return jsonify(courses)

   

# if __name__ == '__main__':
#     app.run(host='0.0.0.0',port='8000', debug='True')












# #fetch course options list based on student programme or lecturer's field of study
# # @app.route('/user_courses', methods=['GET'])
# # @jwt_required()
# # def user_courses():
# #     user_id = get_jwt_identity()
# #     user = mongo.db.users.find_one({'_id': ObjectId(user_id)})

# #     if not user:
# #         return jsonify({"error": "User not found"}), 404

# #     if user['role'] == 'student':
# #         # Assuming 'program' is stored in the user document
# #         program = request.args.get('programme')
# #         year = request.args.get('')
# #         if not program:
# #             return jsonify({"error": "Student program not found"}), 400
        
# #         courses = list(mongo.db.courses.find(
# #             {'program': program},
# #             {'_id': False, 'course_code': True, 'course_name': True}
# #         ))
    
# #     elif user['role'] == 'lecturer':
# #         # Assuming lecturer's courses are stored with their ID
# #         courses = list(mongo.db.courses.find(
# #             {'lecturer_id': ObjectId(user_id)},
# #             {'_id': False, 'course_code': True, 'course_name': True}
# #         ))
    
# #     else:
# #         return jsonify({"error": "Invalid user role"}), 400

# #     if not courses:
# #         return jsonify({"message": "No courses found"}), 404

# #     return jsonify({"courses": courses})






# sessions = {}

#     @socketio.on('liveness_frame')
#     def handle_liveness_frame(data):
#         print("Received frame for processing")
#         # Convert base64 data to numpy array
#         frame = cv2.imdecode(np.frombuffer(data['frame'], np.uint8), cv2.IMREAD_COLOR)
        
#         # Get user's session (you need to implement session management)
#         session = get_user_session(request.sid)
#         session['frames'].append(frame)
#         session['frames'] = session['frames'][-FRAME_HISTORY:]  # Keep only recent frames

#         # Perform detections
#         blinks = detect_blinks(session['frames'])
#         head_movements = detect_head_movements(session['frames'])

#         # Update counts
#         session['blink_count'] += blinks
#         session['head_movement_count'] += head_movements

#         # Check if liveness criteria are met
#         if session['blink_count'] >= REQUIRED_BLINKS and session['head_movement_count'] >= REQUIRED_HEAD_MOVEMENTS:
#             emit('liveness_result', {
#                 'complete': True,
#                 'success': True,
#                 'message': 'Liveness check passed'
#             })
#         else:
#             # Send intermediate results
#             emit('liveness_result', {
#                 'complete': False,
#                 'blinks': session['blink_count'],
#                 'headMovements': session['head_movement_count']
#             })

#     def get_user_session(sid):
#         if sid not in sessions:
#             sessions[sid] = {
#                 'frames': [],
#                 'blink_count': 0,
#                 'head_movement_count': 0
#             }
#         return sessions[sid]