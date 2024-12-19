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

@app.route('/get_all_websites_info', methods=['GET'])
def get_all_websites_info():
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

@app.route('/get_website_info', methods=['POST'])
def get_website_info():
    """
    Get information for a specific website
    Args:
        web_url: URL of the website to get info for
    Return:
        website_info: Website information or error message
    """
    data = request.json
    domain_name = data.get('domainName')
    company_name = utaweb.get_company_name_from_url(domain_name)
    file_path = f'Output/websites/{company_name}/website_info.json'
    
    try:
        with open(file_path, 'r') as f:
            website_data = json.load(f)
            return jsonify({"status": "success", "data": website_data})
    except FileNotFoundError:
        return jsonify({"status": "not_found", "message": f"Website {domain_name} not found in the database"})
    except Exception as e:
        print(f"Error reading website file {file_path}: {e}")
        return jsonify({"status": "error", "message": f"Error reading website information: {str(e)}"})


@app.route('/initialize_rag', methods=['POST'])
def initialize_rag_systems():
    """
    Initialize RAG systems for a company
    Return:
        status: success or error
        message: message to display
    """
    print(request.json)
    data = request.json
    directory_path = pjoin(utaweb.data_dir, utaweb.get_company_name_from_url(data['web_url']))
    if not os.path.exists(directory_path):
        return jsonify({"status": "not_found", "message": f"Website {data['web_url']} not found in the database"})
    try:
        utaweb.initialize_rag(directory_path=directory_path)
        print('RAG systems initialized')
        return jsonify({"status": "success", "message": "RAG systems initialized"})
    except Exception as e:
        print(f"Error initializing RAG systems: {e}")
        return jsonify({"status": "error", "message": "Error initializing RAG systems"})

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
    """
    Crawl a website
    Return:
        status: success or error
        message: message to display
    """
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
    """
    Crawl a website
    Return:
        status: success or error
        message: message to display
    """
    print(request.json)
    data = request.json
    domain_name = data['domainName']
    if domain_name == '':
        return jsonify({"status": "error", "message": "Web URL is empty"})

    # Use the domain limit as the start url if provided, otherwise use the domain name
    domain_limit = data['domainLimit'] if data['domainLimit'] != '' else data['domainName']
    # Start crawl process
    process = Process(
        target=crawl_process,
        args=(domain_limit, domain_limit)
    )
    process.start()
    return jsonify({"status": "success", "message": "Crawling started in background"})

@app.route('/query', methods=['POST'])
def query():
    """
    Query a website
    Return:
        answer: answer to the query
    """
    print(request.json)
    data = request.json
    result = utaweb.query_web(query=data['query'], web_url=data['web_url'])
    # Init user for saving conversations
    user = User(user_id=data['user_id'])
    # Save conversation
    conv = Conversation(conversation_id=data['conversation_id'], host_name=data['host_name'], host_logo=data['host_logo'], host_url=data['web_url'], data_dir=user.chat_dir)
    conv.append_conversation(role="user", content=data['query'])
    conv.append_conversation(role="assistant", content=result)
    conv.save_conversation()
    return jsonify({"answer": result})


# Singleton initialization in the main
if __name__ == '__main__':
    # Create singleton UTAWeb instance for rag system
    utaweb = UTAWeb(initializing=False, data_dir="./Output/websites")
    
    print("Starting server...")
    app.run(host='127.0.0.1', port=7777, debug=True) 