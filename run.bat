@echo off
set FLASK_APP=app.py
set FLASK_ENV=development
set FLASK_DEBUG=1
py app.py runserver --host=0.0.0.0 --port=8000