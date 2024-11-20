document.addEventListener('DOMContentLoaded', function() {
    // Get current tab URL
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
        const currentUrl = tabs[0].url;
        document.getElementById('currentUrl').textContent = currentUrl;
    });

    // Crawl button handler
    document.getElementById('crawlButton').addEventListener('click', async function() {
        const response = await fetch('http://localhost:7777/crawl', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: document.getElementById('currentUrl').textContent
            })
        });
        
        const result = await response.json();
        document.getElementById('response').textContent = 'Crawling started...';
    });

    // Query button handler
    document.getElementById('queryButton').addEventListener('click', async function() {
        const query = document.getElementById('queryInput').value;
        
        const response = await fetch('http://localhost:7777/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                url: document.getElementById('currentUrl').textContent
            })
        });
        
        const result = await response.json();
        document.getElementById('response').textContent = result.answer;
    });
}); 