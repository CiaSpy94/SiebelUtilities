
from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)  # This enables CORS for all routes

DATA_FILE = 'switch.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/api/switches', methods=['GET'])
def get_switches():
    return jsonify(load_data())

@app.route('/api/switches', methods=['POST'])
def add_switch():
    new_entry = request.json
    data = load_data()
    data.append(new_entry)
    save_data(data)
    return jsonify({'status': 'success', 'data': new_entry}), 201

if __name__ == '__main__':
    app.run(debug=True)
