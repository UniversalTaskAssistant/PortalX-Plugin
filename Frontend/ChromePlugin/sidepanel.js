$(document).ready(function() {
    const $crawlButton = $('#crawlButton');
    const $queryButton = $('#queryButton');
    const $responseDiv = $('#response');
    const $queryInput = $('#queryInput');
    const $welcomeMessage = $('.welcome-msg');
    let currentUrl = '';

    // Get current tab URL
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
        currentUrl = tabs[0].url;
        console.log(currentUrl);
    });

    // Add message to response area
    function addMessage(text, isUser = false) {
        if ($welcomeMessage.is(':visible')) {
            $welcomeMessage.hide();
        }

        const $messageContainer = $('<div>', {
            class: 'message-container'
        });
        
        const $messageDiv = $('<div>', {
            class: `message ${isUser ? 'user' : 'assistant'}`,
            text: text
        });
        
        $messageContainer.append($messageDiv);
        $responseDiv.append($messageContainer);
        $messageDiv[0].scrollIntoView({ behavior: 'smooth' });
    }

    // Crawl button handler
    $crawlButton.on('click', async function() {
        try {
            console.log(currentUrl);
            $crawlButton.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Crawling...');
            const response = await $.ajax({
                url: 'http://localhost:7777/crawl',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    web_url: currentUrl,
                    company_name: '',
                    domain_limit: ''
                })
            });
            addMessage('Crawling completed successfully! You can now ask questions about this website.');
        } catch (error) {
            addMessage(`Error during crawling: ${error.message}`);
        } finally {
            $crawlButton.prop('disabled', false)
                       .html('<i class="bi bi-spider me-2"></i>Analyze This Website');
        }
    });

    // Query button handler
    $queryButton.on('click', async function() {
        const query = $queryInput.val().trim();
        if (!query) {
            addMessage('Please enter a question', true);
            return;
        }
        
        try {
            // Update loading state
            $queryButton.prop('disabled', true)
                       .addClass('loading')
                       .html('<span class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></span>');
            $queryInput.prop('disabled', true);
            
            // Add user question to chat
            addMessage(query, true);
            
            const response = await $.ajax({
                url: 'http://localhost:7777/query',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    user_id: 'test1',
                    conversation_id: 'conv1',
                    query: query,
                    web_url: 'https://www.tum.de/en/'
                })
            });
            
            addMessage(response.answer);
            $queryInput.val(''); // Clear input after successful response
        } catch (error) {
            addMessage(`Error getting response: ${error.message}`);
        } finally {
            // Reset button state
            $queryButton.prop('disabled', false)
                       .removeClass('loading')
                       .html('<i class="bi bi-send-fill"></i>');
            $queryInput.prop('disabled', false);
        }
    });

    // Handle enter key in textarea
    $queryInput.on('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            $queryButton.click();
        }
    });
}); 