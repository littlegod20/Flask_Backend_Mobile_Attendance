# models.py
from flask import current_app
from bson import ObjectId
from datetime import datetime, timezone
from geopy.distance import geodesic
import cv2
import numpy as np
import dlib
from scipy.spatial.distance import cosine
from deepface import DeepFace
from flask import jsonify
from matplotlib import pyplot as plt
from sklearn.metrics import precision_recall_fscore_support, accuracy_score
import numpy as np


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



# Configure DeepFace
model_name = 'VGG-Face'

# Initialize dlib's face detector
detector = dlib.get_frontal_face_detector()

def preprocess_image(image, save_path=None):
    # Convert to RGB
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Detect faces
    faces = detector(rgb_image)
    
    if len(faces) == 0:
        print("No face detected")
        return None
    
    # Get the first face
    face = faces[0]
    x, y, w, h = (face.left(), face.top(), face.width(), face.height())
    
    # Crop the face
    cropped_face = image[y:y+h, x:x+w]
    
    # Resize to a standard size (e.g., 224x224 for VGG-Face)
    preprocessed_image = cv2.resize(cropped_face, (224, 224))

     # Save or display the image if a save path is provided
    # if save_path:
    #     cv2.imwrite(save_path, preprocessed_image)
    # else:
    #     # Display the image using matplotlib
    #     plt.imshow(cv2.cvtColor(preprocessed_image, cv2.COLOR_BGR2RGB))
    #     plt.axis('off')
    #     plt.show()
    
    return preprocessed_image

def extract_features(face_img):
    preprocessed_face = preprocess_image(face_img)
    if preprocessed_face is None:
        return False,"No face detected in the image"
    
    result = DeepFace.represent(preprocessed_face, model_name=model_name, enforce_detection=False)
    # The result is now a list of dictionaries, we'll take the first one
    embedding = result[0]['embedding']
    return embedding


def create_user(data):
    users = get_mongo().db.users
    
    if 'image' not in data.files:
        return jsonify({"error": "No image file"})
    
    name = data.form.get('name')
    email = data.form.get('email')
    password = data.form.get('password')
    school_id = data.form.get('school_id')
    role = data.form.get('role')
    year = data.form.get('year')
    faculty = data.form.get('faculty')
    programme = data.form.get('programme')
    image = cv2.imdecode(np.frombuffer(data.files['image'].read(), np.uint8), cv2.IMREAD_COLOR)
    
    if not email or not password or not role or not year or not programme:
        raise ValueError("Missing credentials, check your form inputs")
    
    
    if users.find_one({'email': email}):
        raise ValueError("Email already exists")
    
    hashed_password = current_app.bcrypt.generate_password_hash(password).decode('utf-8')
    
    try:
        features =  extract_features(image)
        user_data = {
            'name': name,
            'password': hashed_password,
            'email': email,
            'school_id': school_id,
            'role': role,
            'year': year or None,
            'faculty': faculty,
            'programme': programme,
            "face_features": features
        }
        user_id = users.insert_one(user_data).inserted_id
        return user_id
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f'Failed to register face:{str(e)}'}), 400

def open_session(user_id, course_code, course_name, location, perimeter):
    get_mongo().db.sessions.insert_one({
        'lecturer_id': ObjectId(user_id),
        'course_code': course_code,
        'course_name': course_name,
        'timestamp': datetime.now(timezone.utc),
        'location': location,
        'perimeter': perimeter,
        'active': True
    })

def close_session(user_id, course_code, course_name, location):
    get_mongo().db.sessions.update_one(
        {
            'lecturer_id': ObjectId(user_id),
            'course_code': course_code,
            'course_name': course_name,
            'location': location,
            'active': True
        },
        {
            '$set': {'active': False, 'end_time': datetime.now(timezone.utc)}
        }
    )

def get_lecturer_location(course_code): 
    session = get_mongo().db.sessions.find_one({'course_code':course_code, 'active': True})
    if session: 
        # session['location'][0]
        return {
            "location" : session.get("location"),
            "perimeter": session.get("perimeter", 100) # Default to 100 if not set
        }
    return None


def is_session_active(course_code):
    return get_mongo().db.sessions.find_one({'course_code': course_code, 'active': True}) is not None

def record_attendance(user_id, course_code,course_name, location, attendance_checked, image):

    # Get the current active session for this course
    session = get_mongo().db.sessions.find_one({
        'course_code': course_code,
        'active': True
    })

    if not session:
        return False, "No active session for this course"
    
    try:
        # input_features = extract_features(image)
        user = get_mongo().db.users.find_one({'_id':ObjectId(user_id)})
        # print(f'found user: {user}')

        if not user:
            return False, "User not found"
        
        face_recognized = False
        similarity = None

        if image is not None:
            input_features = extract_features(image)
            stored_features = np.array(user['face_features'])
            similarity = 1 - cosine(input_features, stored_features)
            print(f'Similarity:{similarity:.2f}')

            # If face is not recognized, return error
            if similarity <= 0.6:
                return False, f"Face not recognized. Similarity: {similarity:.2f}"
            
            face_recognized = True

        # Face recognized, record attendance
        attendance_record = {
            'student_id': ObjectId(user_id),
            'course_code': course_code,
            'course_name': course_name,
            'session_id': session['_id'],
            'timestamp': datetime.now(timezone.utc),
            'location': location,
            'attendance_checked': attendance_checked,
            'face_recognized': face_recognized,
            'face_similarity': float(similarity) if image is not None else None
        }
        
        get_mongo().db.attendance.insert_one(attendance_record)

        # Update the student's course data
        get_mongo().db.student_courses.update_one(
            {'student_id': ObjectId(user_id), 'courses.course_code': course_code},
            {'$set': {'courses.$.attendance_checked': attendance_checked}}
        )
        return True, f"Attendance recorded successfully."
    except ValueError as ve:
        print(f"ValueError in record_attendance: {str(ve)}")
        return False, f'ValueError: {str(ve)}'
    except Exception as e:
        print(f"Exception in record_attendance: {str(e)}")
        return False, f"Failed to record attendance:{str(e)}"

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
        {
            '$match': {
                'courses.course_code': course_code
            }
        },
        {
            '$unwind': '$courses'
        },
        {
            '$match': {
                'courses.course_code': course_code
            }
        },
        {
            '$lookup': {
                'from': 'users',
                'let': {'programme': '$programme', 'year': '$year'},
                'pipeline': [
                    {
                        '$match': {
                            '$expr': {
                                '$and': [
                                    {'$eq': ['$programme', '$$programme']},
                                    {'$eq': ['$year', '$$year']},
                                    {'$eq': ['$role', 'student']}
                                ]
                            }
                        }
                    }
                ],
                'as': 'student'
            }
        },
        {
            '$unwind': '$student'
        },
        {
            '$lookup': {
                'from': 'attendance',
                'let': {'student_id': '$student._id', 'course_code': course_code},
                'pipeline': [
                    {
                        '$match': {
                            '$expr': {
                                '$and': [
                                    {'$eq': ['$student_id', '$$student_id']},
                                    {'$eq': ['$course_code', '$$course_code']}
                                ]
                            }
                        }
                    },
                    {'$count': 'attendance_count'}
                ],
                'as': 'attendance'
            }
        },
        {
            '$lookup': {
                'from': 'sessions',
                'let': {'course_code': course_code},
                'pipeline': [
                    {
                        '$match': {
                            '$expr': {
                                '$and': [
                                    {'$eq': ['$course_code', '$$course_code']},
                                    {'$eq': ['$active', False]}  # Only count closed sessions
                                ]
                            }
                        }
                    },
                    {'$count': 'total_sessions'}
                ],
                'as': 'sessions'
            }
        },
        {
            '$unwind': {
                'path': '$sessions',
                'preserveNullAndEmptyArrays': True
            }
        },
        {
            '$project': {
                '_id': 0,
                'student_name': '$student.name',
                'student_id': '$student.school_id',
                'attendance_count': {'$ifNull': [{'$arrayElemAt': ['$attendance.attendance_count', 0]}, 0]},
                'total_sessions': {'$ifNull': ['$sessions.total_sessions', 0]},
                'attendance_percentage': {
                    '$cond': [
                        {'$eq': [{'$ifNull': ['$sessions.total_sessions', 0]}, 0]},
                        0,
                        {
                            '$multiply': [
                                {
                                    '$divide': [
                                        {'$ifNull': [{'$arrayElemAt': ['$attendance.attendance_count', 0]}, 0]},
                                        {'$ifNull': ['$sessions.total_sessions', 1]}
                                    ]
                                },
                                100
                            ]
                        }
                    ]
                }
            }
        }
    ]
   
    return list(get_mongo().db.student_courses.aggregate(pipeline))

def get_courses(collection, **kwargs):
    return list(get_mongo().db[collection].find(kwargs, {'_id': False}))


def get_session_status(course_code):
    session = get_mongo().db.sessions.find_one(
        {'course_code': course_code, 'active': True},
        {'_id': False, 'active': True}
    )
    return 'open' if session else 'closed'


def check_attendance_status(user_id, course_code):
    # Find the current active session for this course
    session = get_mongo().db.sessions.find_one({
        'course_code': course_code,
        'active': True
    })

    if not session:
        return False  # No active session, so attendance can't be checked

    # Check if there's an attendance record for this user in this session
    attendance = get_mongo().db.attendance.find_one({
        'student_id': ObjectId(user_id),
        'course_code': course_code,
        'session_id': session['_id']
    })

    return bool(attendance)


def calculate_distance(location1, location2):
    # location and location2 should be tuples like (latitude, longitude)
    tuple1 = tuple(location1.values())
    tuple2 = tuple(location2.values())
    return geodesic(tuple1, tuple2).meters


def get_recent_attendance(user_id):
    # Define the semester start date
    semester_start_date = datetime(2024, 5, 12) 

    pipeline = [
        {'$match': {'student_id': ObjectId(user_id)}},
        {'$sort': {'timestamp': -1}},
        {'$limit': 5},
        {'$lookup': {
            'from': 'student_courses',
            'let': {'course_code': '$course_code'},
            'pipeline': [
                {'$match': {
                    '$expr': {
                        '$in': [
                            '$$course_code',
                            '$courses.course_code'
                        ]
                    }
                }},
                {'$unwind': '$courses'},
                {'$match': {
                    '$expr': {
                        '$eq': ['$courses.course_code', '$$course_code']
                    }
                }}
            ],
            'as': 'course_info'
        }},
        {'$unwind': '$course_info'},
        {'$lookup': {
            'from': 'sessions',
            'let': {'course_code': '$course_code'},
            'pipeline': [
                {'$match': {
                    '$expr': {
                        '$eq': ['$course_code', '$$course_code']
                    }
                }},
                {'$count': 'total_sessions'}
            ],
            'as': 'session_info'
        }},
        {'$unwind': '$session_info'},
        {'$group': {
            '_id': '$course_code',
            'courseName': {'$first': '$course_name'},
            'programme': {'$first': '$course_info.programme'},
            'year': {'$first': '$course_info.year'},
            'credits': {'$first': '$course_info.courses.credits'},
            'total_sessions': {'$first': '$session_info.total_sessions'},
            'attended_sessions': {'$sum': 1},
            'latest_timestamp': {'$max': '$timestamp'}
        }},
        {'$addFields': {
            'week_of_semester': {
                '$ceil': {
                    '$divide': [
                        {'$subtract': ['$latest_timestamp', semester_start_date]},
                        1000 * 60 * 60 * 24 * 7  # milliseconds in a week
                    ]
                }
            },
            'attendance_fraction': {
                '$divide': ['$attended_sessions', '$total_sessions']
            }
        }},
        {'$project': {
            '_id': 0,
            'courseId': '$_id',
            'courseName': 1,
            'attendance': {
                '$concat': [
                    {'$toString': '$attended_sessions'},
                    '/',
                    {'$toString': '$total_sessions'}
                ]
            },
            'attendanceFraction': '$attendance_fraction',
            'timestamp': '$latest_timestamp',
            'week': '$week_of_semester',
            'programme': 1,
            'year': 1,
            'credits': 1,
            'code':1
        }},
        {'$sort': {'timestamp': -1}}
    ]
    
    return list(get_mongo().db.attendance.aggregate(pipeline))


def get_overall_class_attendance(course_code, course_name):
    pipeline = [
        {
            '$match': {
                'courses.course_code': course_code
            }
        },
        {
            '$unwind': '$courses'
        },
        {
            '$match': {
                'courses.course_code': course_code
            }
        },
        {
            '$lookup': {
                'from': 'users',
                'let': {'programme': '$programme', 'year': '$year'},
                'pipeline': [
                    {
                        '$match': {
                            '$expr': {
                                '$and': [
                                    {'$eq': ['$programme', '$$programme']},
                                    {'$eq': ['$year', '$$year']},
                                    {'$eq': ['$role', 'student']}
                                ]
                            }
                        }
                    }
                ],
                'as': 'students'
            }
        },
        {
            '$unwind': '$students'
        },
        {
            '$lookup': {
                'from': 'attendance',
                'let': {'student_id': '$students._id', 'course_code': course_code},
                'pipeline': [
                    {
                        '$match': {
                            '$expr': {
                                '$and': [
                                    {'$eq': ['$student_id', '$$student_id']},
                                    {'$eq': ['$course_code', '$$course_code']}
                                ]
                            }
                        }
                    },
                    {'$count': 'attendance_count'}
                ],
                'as': 'attendance'
            }
        },
        {
            '$lookup': {
                'from': 'sessions',
                'let': {'course_code': course_code},
                'pipeline': [
                    {
                        '$match': {
                            '$expr': {
                                '$and': [
                                    {'$eq': ['$course_code', '$$course_code']},
                                    {'$eq': ['$active', False]}  # Only count closed sessions
                                ]
                            }
                        }
                    },
                    {'$count': 'total_sessions'}
                ],
                'as': 'sessions'
            }
        },
        {
            '$unwind': {
                'path': '$sessions',
                'preserveNullAndEmptyArrays': True
            }
        },
        {
            '$group': {
                '_id': None,
                'total_students': {'$sum': 1},
                'total_attendance': {'$sum': {'$ifNull': [{'$arrayElemAt': ['$attendance.attendance_count', 0]}, 0]}},
                'total_sessions': {'$first': '$sessions.total_sessions'}
            }
        },
        {
            '$project': {
                '_id': 0,
                'course_code': course_code,
                'course_name': course_name,
                'total_students': 1,
                'total_sessions': 1,
                'total_attendance': 1,
                'average_attendance': {
                    '$cond': [
                        {'$eq': ['$total_sessions', 0]},
                        0,
                        {
                            '$multiply': [
                                {
                                    '$divide': [
                                        '$total_attendance',
                                        {'$multiply': ['$total_students', '$total_sessions']}
                                    ]
                                },
                                100
                            ]
                        }
                    ]
                }
            }
        }
    ]
   
    result = list(get_mongo().db.student_courses.aggregate(pipeline))
    return result[0] if result else None


# Evaluating my facial recognition model
def evaluate_model(test_images, test_labels, user_ids):
    predictions = []
    true_labels = []
    
    print(f"Total test cases: {len(test_images)}")
    
    for i, (image, label, user_id) in enumerate(zip(test_images, test_labels, user_ids)):
        print(f"\nProcessing image {i+1}")
        print(f"Label: {label}, User ID: {user_id}")
        
        # Use your existing functions to process the image and compare
        input_features = extract_features(image)
        if input_features is False:
            print("No face detected in image")
            continue  # Skip images where no face is detected
        
        if user_id is not None:
            try:
                user_id_obj = ObjectId(user_id)
                user = get_mongo().db.users.find_one({'_id': user_id_obj})
                if not user:
                    print(f'User with ID {user_id} not found in database')
                    continue  # Skip if user not found
                
                stored_features = np.array(user['face_features'])
                similarity = 1 - cosine(input_features, stored_features)
                
                print(f"Similarity: {similarity}")
                
                # Use the same threshold as in your record_attendance function
                prediction = similarity > 0.6
            except Exception as e:
                print(f"Error processing user {user_id}: {str(e)}")
                continue
        else:
            # For unrecognized faces, always predict False
            prediction = False
        
        predictions.append(prediction)
        true_labels.append(label)
    
    print(f"\nTotal processed cases: {len(predictions)}")
    
    # Calculate metrics
    if len(predictions) > 0:
        precision, recall, _, _ = precision_recall_fscore_support(true_labels, predictions, average='binary')
        accuracy = accuracy_score(true_labels, predictions)
    else:
        print("No valid predictions made")
        return {'accuracy': 0, 'precision': 0, 'recall': 0}
    
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall
    }