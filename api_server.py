from flask import Flask, request, jsonify
from flask_cors import CORS
from UTAWeb import UTAWeb
import urllib.parse

app = Flask(__name__)
CORS(app)

utaweb = UTAWeb(initializing=True)

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
    print(request)
    print(request.json)
    data = request.json
    result = utaweb.query_web(query=data['query'], web_url=data['web_url'])
    return jsonify({"answer": result})

if __name__ == '__main__':
    print("Starting server...")
    app.run(host='127.0.0.1', port=7777, debug=True) 