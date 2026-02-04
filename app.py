# app.py
import os
from flask import Flask
from dotenv import load_dotenv
from library import library_bp

load_dotenv()

# Explicitly set template directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, 'templates'))
app.secret_key = os.getenv("SECRET_KEY")

app.register_blueprint(library_bp)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)