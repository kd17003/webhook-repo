from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime
import pymongo
from pymongo import MongoClient
import os
from models import Event
from dotenv import load_dotenv

# Load .env file - specify the path explicitly
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
CORS(app)

# MongoDB connection
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.getenv('DB_NAME', 'github_events')

# Debug: Print what we're using (remove password for security)
print(f"MONGO_URI loaded: {MONGO_URI[:30]}..." if len(MONGO_URI) > 30 else f"MONGO_URI: {MONGO_URI}")
print(f"DB_NAME: {DB_NAME}")

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    db = client[DB_NAME]
    events_collection = db['events']
    print("✓ MongoDB connection successful")
except Exception as e:
    print(f"✗ MongoDB connection error: {str(e)}")
    print("Please set MONGO_URI environment variable with your MongoDB Atlas connection string")
    client = None
    db = None
    events_collection = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/webhook', methods=['POST', 'OPTIONS'])
def webhook():
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    try:
        if events_collection is None:
            return jsonify({'status': 'error', 'message': 'MongoDB not connected'}), 500
            
        payload = request.json
        event_type = request.headers.get('X-GitHub-Event')
        
        print(f"Received webhook: {event_type}")  # Debug line
        
        if event_type == 'push':
            process_push_event(payload)
        elif event_type == 'pull_request':
            if payload.get('action') == 'opened':
                process_pull_request_event(payload)
            elif payload.get('action') == 'closed' and payload.get('pull_request', {}).get('merged'):
                process_merge_event(payload)
        
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

def process_push_event(payload):
    if not payload.get('head_commit'):
        return
    
    author = payload['pusher']['name']
    branch = payload['ref'].replace('refs/heads/', '')
    timestamp = payload['head_commit']['timestamp']
    
    event = Event(
        action='PUSH',
        author=author,
        from_branch=None,
        to_branch=branch,
        timestamp=timestamp
    )
    events_collection.insert_one(event.to_dict())
def process_pull_request_event(payload):
    pr = payload['pull_request']
    author = pr['user']['login']
    from_branch = pr['head']['ref']
    to_branch = pr['base']['ref']
    timestamp = pr['created_at']
    
    event = Event(
        action='PULL_REQUEST',
        author=author,
        from_branch=from_branch,
        to_branch=to_branch,
        timestamp=timestamp
    )
    events_collection.insert_one(event.to_dict())

def process_merge_event(payload):
    pr = payload['pull_request']
    author = pr['merged_by']['login'] if pr.get('merged_by') else pr['user']['login']
    from_branch = pr['head']['ref']
    to_branch = pr['base']['ref']
    timestamp = pr['merged_at']
    
    event = Event(
        action='MERGE',
        author=author,
        from_branch=from_branch,
        to_branch=to_branch,
        timestamp=timestamp
    )
    events_collection.insert_one(event.to_dict())

@app.route('/api/events', methods=['GET'])
def get_events():
    try:
        if events_collection is None:
            return jsonify({'status': 'error', 'message': 'MongoDB not connected'}), 500
        
        events = list(events_collection.find().sort('timestamp', -1).limit(50))
        for event in events:
            event['_id'] = str(event['_id'])
        return jsonify(events), 200
    except Exception as e:
        print(f"Error fetching events: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)