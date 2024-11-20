document.addEventListener('DOMContentLoaded', function() {
    const crawlButton = document.getElementById('crawlButton');
    const queryButton = document.getElementById('queryButton');
    const responseDiv = document.getElementById('response');
    const queryInput = document.getElementById('queryInput');

    // Get current tab URL
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
        const currentUrl = tabs[0].url;
        document.getElementById('currentUrl').textContent = currentUrl;
    });

    function addMessage(text, isUser = false) {
        const messageContainer = document.createElement('div');
        messageContainer.className = 'message-container';
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
        messageDiv.textContent = text;
        
        messageContainer.appendChild(messageDiv);
        document.getElementById('response').appendChild(messageContainer);
        messageDiv.scrollIntoView({ behavior: 'smooth' });
    }

    function showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'typing-indicator';
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('span');
            indicator.appendChild(dot);
        }
        document.getElementById('response').appendChild(indicator);
        indicator.scrollIntoView({ behavior: 'smooth' });
        return indicator;
    }

    // Crawl button handler
    crawlButton.addEventListener('click', async function() {
        try {
            crawlButton.disabled = true;
            crawlButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Crawling...';
            
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
            addMessage('Crawling completed successfully! You can now ask questions about this website.');
        } catch (error) {
            addMessage(`Error during crawling: ${error.message}`);
        } finally {
            crawlButton.disabled = false;
            crawlButton.innerHTML = '<i class="bi bi-spider"></i> Crawl This Site';
        }
    });

    // Query button handler
    queryButton.addEventListener('click', async function() {
        const query = queryInput.value;
        if (!query.trim()) {
            addMessage('Please enter a question', true);
            return;
        }
        
        try {
            queryButton.disabled = true;
            queryInput.disabled = true;
            queryButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
            
            // Add user question to chat
            addMessage(query, true);
            
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
            addMessage(result.answer);
            queryInput.value = ''; // Clear input after successful response
        } catch (error) {
            addMessage(`Error getting response: ${error.message}`);
        } finally {
            queryButton.disabled = false;
            queryInput.disabled = false;
            queryButton.innerHTML = '<i class="bi bi-search"></i> Ask Question';
        }
    });

    // Handle enter key in textarea
    queryInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            queryButton.click();
        }
    });
}); 