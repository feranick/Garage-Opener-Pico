# **********************************************
# * PicoGarageOpener - System Mail Backend
# * v2025.11.22.2
# * By: Nicola Ferralis <feranick@hotmail.com>
# **********************************************

import os
import sys
import json
import datetime
import configparser
import subprocess
from flask import Flask, request, jsonify
from flask_cors import CORS

# ----------------------------------------------------
# 1. WSGI PATH SETUP
# ----------------------------------------------------
sys.path.insert(0, '/var/www/PicoGarageOpener')

# ----------------------------------------------------
# 2. CONFIG FILE LOADING
# ----------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, 'config.cfg')

SERVER_SECRET_KEY = None
DEFAULT_RECIPIENT = None

try:
    config = configparser.ConfigParser(allow_no_value=True)
    with open(CONFIG_PATH, 'r') as f:
        config.read_string(f'[DEFAULT]\n{f.read()}')

    SERVER_SECRET_KEY = config['DEFAULT'].get('SERVER_SECRET_KEY')
    DEFAULT_RECIPIENT = config['DEFAULT'].get('DEFAULT_RECIPIENT')

    print(f"[DEBUG] PicoGarageOpener (System Mail) configuration loaded.")

except Exception as e:
    print(f"[CRITICAL ERROR] General error during configuration setup: {e}")

# ----------------------------------------------------
# 3. FLASK APP INITIALIZATION
# ----------------------------------------------------
app = Flask(__name__)
CORS(app)

# ----------------------------------------------------
# 4. HELPER FUNCTION: SEND VIA SHELL
# ----------------------------------------------------
def send_email_via_system(subject, body, recipient):
    """
    Uses the system 'mail' command (mailutils) to send email.
    Equivalent to: echo "body" | mail -s "subject" recipient
    """
    try:
        # Construct command arguments safely (prevents shell injection)
        cmd = ['mail', '-s', subject, recipient]

        # Execute the command, passing the body into stdin
        result = subprocess.run(
            cmd,
            input=body,
            text=True,           # Treat input/output as strings, not bytes
            capture_output=True, # Capture stdout/stderr for debugging
            check=True           # Raise exception if command returns non-zero exit code
        )

        return True, "Email handed off to system mailer"

    except subprocess.CalledProcessError as e:
        # This catches errors if the 'mail' command fails (returns non-zero)
        error_msg = f"Mail command failed. Stderr: {e.stderr}"
        print(f"[EMAIL ERROR] {error_msg}")
        return False, error_msg

    except Exception as e:
        print(f"[EMAIL ERROR] {str(e)}")
        return False, str(e)

# ----------------------------------------------------
# 5. ROUTES
# ----------------------------------------------------

@app.route('/trigger-email', methods=['POST'])
def trigger_email():
    """Receives command from Pico to send an email."""

    # 1. Key Validation
    try:
        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400

        data = request.get_json()
        submitted_key = data.get('api_secret_key')

        if not submitted_key or submitted_key != SERVER_SECRET_KEY:
            print(f"[ERROR] Unauthorized access attempt.")
            return jsonify({"message": "Unauthorized access or missing key."}), 403

    except Exception as e:
        return jsonify({"message": f"Invalid request payload: {str(e)}"}), 400

    # 2. Extract Data
    subject = data.get('subject', 'PicoGarageOpener Alert')
    body = data.get('body', 'An event occurred at the garage.')
    recipient = data.get('recipient', DEFAULT_RECIPIENT)

    if not recipient:
         return jsonify({"message": "No recipient specified."}), 400

    # 3. Send Email via System
    success, message = send_email_via_system(subject, body, recipient)

    if success:
        print(f"[INFO] System mail command executed for {recipient}")
        return jsonify({"message": "Email sent successfully"}), 200
    else:
        return jsonify({"message": f"Failed to send email: {message}"}), 500

@app.route('/status', methods=['GET'])
def status_check():
    return jsonify({
        "status": "PicoGarageOpener System-Mail Backend Online",
        "time": datetime.datetime.utcnow().isoformat()
    }), 200

# ----------------------------------------------------
# 6. WSGI Entry Point
# ----------------------------------------------------
application = app
