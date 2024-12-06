import os
from os.path import join as pjoin
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from multiprocessing import Process
import glob
import json
# Add Backend directory directly
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Backend'))

from Backend.UTAWeb import UTAWeb
from System.conversation import Conversation
from System.user import User

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["chrome-extension://ocjcneogfgoccopmmjdjhleafgpjfelp"],
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})
# Global variable declaration
utaweb = None


@app.route('/get_chat_history', methods=['POST'])
def get_chat_history():
    """
    Get chat history for a user
    Return:
        chat_history: List of chat history sorted by timestamp, newest first
    """
    data = request.json
    # Load all conversation files
    chat_files = glob.glob(f'Output/users/{data["user_id"]}/chats/*.json')
    chat_history = []
    for file_path in chat_files:
        try:
            with open(file_path, 'r') as f:
                chat_data = json.load(f)
                chat_history.append(chat_data)
        except Exception as e:
            print(f"Error reading chat file {file_path}: {e}")
    # Sort by timestamp, newest first
    chat_history.sort(key=lambda x: x['timestamp'], reverse=True)
    return jsonify(chat_history)

def crawl_process(web_url, domain_limit):
    # Create temporary UTAWeb instance for crawler process
    utaweb_instance = UTAWeb(data_dir="./Output/websites")
    # Get company name here if not provided
    company_name = utaweb_instance.get_company_name_from_url(web_url)
    utaweb_instance.crawl_web(
        web_url=web_url,
        company_name=company_name,
        domain_limit=domain_limit
    )

@app.route('/crawl', methods=['POST'])
def crawl():
    print(request.json)
    data = request.json
    web_url = data['web_url']
    if web_url == '':
        return jsonify({"status": "error", "message": "Web URL is empty"})

    # Start crawl process
    domain_limit = data['domain_limit'] if data['domain_limit'] != '' else None
    process = Process(
        target=crawl_process,
        args=(web_url, domain_limit)
    )
    process.start()
    return jsonify({"status": "success", "message": "Crawling started in background"})

@app.route('/query', methods=['POST'])
def query():
    print(request.json)
    data = request.json
    result = utaweb.query_web(query=data['query'], web_url=data['web_url'])
    # Init user for saving conversations
    user = User(user_id=data['user_id'])
    # Save conversation
    conv = Conversation(conversation_id=data['conversation_id'], data_dir=user.chat_dir)
    conv.append_conversation(role="user", content=data['query'])
    conv.append_conversation(role="assistant", content=result)
    conv.save_conversation()
    return jsonify({"answer": result})

@app.route('/get_websites', methods=['GET'])
def get_websites():
    """
    Get list of all crawled websites
    Return:
        websites: List of website info sorted by crawl time, newest first
    """
    website_files = glob.glob('Output/websites/*/website_info.json')
    websites = []
    for file_path in website_files:
        try:
            with open(file_path, 'r') as f:
                website_data = json.load(f)
                websites.append(website_data)
        except Exception as e:
            print(f"Error reading website file {file_path}: {e}")
    # Sort by crawl time, newest first
    websites.sort(key=lambda x: x['crawl_time'], reverse=True)
    return jsonify(websites)

@app.route('/initialize_rag', methods=['POST'])
def initialize_rag_systems():
    print(request.json)
    data = request.json
    utaweb.initialize_rag(directory_path=pjoin(utaweb.data_dir, utaweb.get_company_name_from_url(data['web_url'])))
    print('RAG systems initialized')
    return jsonify({"status": "success", "message": "RAG systems initialized"})


# Singleton initialization in the main
if __name__ == '__main__':
    # Create singleton UTAWeb instance for rag system
    utaweb = UTAWeb(initializing=False, data_dir="./Output/websites")
    utaweb.initialize_crawler()
    utaweb.initialize_rag()
    
    print("Starting server...")
    app.run(host='127.0.0.1', port=7777, debug=True) 