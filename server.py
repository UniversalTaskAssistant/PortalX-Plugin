import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from multiprocessing import Process
# Add Backend directory directly
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Backend'))

from Backend.UTAWeb import UTAWeb  #
from System.conversation import Conversation

app = Flask(__name__)
CORS(app)

utaweb = UTAWeb(initializing=True)

def crawl_process(web_url, company_name, domain_limit):
    utaweb_instance = UTAWeb(initializing=False)
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

    company_name = data['company_name'] if data['company_name'] != '' else None
    domain_limit = data['domain_limit'] if data['domain_limit'] != '' else None
    process = Process(
        target=crawl_process,
        args=(web_url, company_name, domain_limit)
    )
    process.start()
    return jsonify({"status": "success", "message": "Crawling started in background"})

@app.route('/query', methods=['POST'])
def query():
    print(request.json)
    data = request.json
    result = utaweb.query_web(query=data['query'], web_url=data['web_url'])
    # Save conversation
    conv = Conversation(conversation_id=data['conversation_id'], data_dir="./Output/chat")
    conv.append_conversation(role="user", content=data['query'])
    conv.append_conversation(role="assistant", content=result)
    conv.save_conversation()
    return jsonify({"answer": result})

if __name__ == '__main__':
    print("Starting server...")
    app.run(host='127.0.0.1', port=7777, debug=True) 