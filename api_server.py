from flask import Flask, request, jsonify
from flask_cors import CORS
from UTAWeb import UTAWeb
import urllib.parse

app = Flask(__name__)
CORS(app)

utaweb = UTAWeb()

@app.route('/crawl', methods=['POST'])
def crawl():
    data = request.json
    url = data['url']
    domain = urllib.parse.urlparse(url).netloc
    company_name = domain.split('.')[1]  # Simple way to get company name from domain
    
    utaweb.crawl_web(
        web_urls=[url],
        company_name=company_name,
        domain_limit=url
    )
    return jsonify({"status": "success"})

@app.route('/query', methods=['POST'])
def query():
    data = request.json
    query = data['query']
    url = data['url']
    domain = urllib.parse.urlparse(url).netloc
    company_name = domain.split('.')[1]
    
    result = utaweb.rag_system.query(query)
    formatted_response = utaweb.rag_system.format_response(result)
    
    return jsonify({"answer": formatted_response})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=7777, debug=True) 