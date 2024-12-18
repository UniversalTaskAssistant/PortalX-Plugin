let conversationId = generateConversationId();
let websiteInfo = {}; 

$(document).ready(() => {
    initializePopup();
    setChat();
    setInputLoading();
});

function initializePopup() {
    const $newChatBtn = $('#newChatBtn');
    const $minimizeBtn = $('.minimize-btn');
    const $welcomeMessage = $('.welcome-message');

    // Get current tab's domain and update favicon
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
        websiteInfo = getWebsiteInfoFromUrl(tabs[0].url);
        websiteInfo.favicon = tabs[0].favIconUrl;
        $('.website-favicon').attr('src', websiteInfo.favicon);
    });

    $newChatBtn.on('click', () => {
        $('.message-container').remove();
        $welcomeMessage.fadeIn(200);
    });

    $minimizeBtn.on('click', () => {
        // Send message to parent window to minimize
        window.parent.postMessage('minimize', '*');
    });
}

function setChat(){
    const $messagesContainer = $('#messagesContainer');
    const $queryInput = $('#queryInput');
    const $sendButton = $('#sendButton');

    $sendButton.on('click', sendMessage);
    $queryInput.on('keypress', (e) => {
        if (e.which === 13 && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Handle sending messages
    function sendMessage() {
        const query = $queryInput.val().trim();
        if (!query) return;

        // Remove welcome message and add user message after fade completes
        $('.welcome-message').fadeOut(100, function() {
            // Add user message
            addMessage(query, 'user');
        });

        // Clear input
        $queryInput.val('');

        // TODO: Send query to backend and handle response
        // For now, just add a mock response
        setTimeout(() => {
            addMessage('This is a mock response. The actual integration with the backend will be implemented later.', 'assistant');
        }, 1000);
    }

    // Add a message to the chat
    function addMessage(text, type) {
        const $messageContainer = $('<div>', {
            class: `message-container ${type === 'assistant' ? 'assistant-container' : ''}`
        });

        if (type === 'assistant') {
            // Add assistant icon
            const $iconDiv = $('<div>', {
                class: 'assistant-icon'
            }).append(
                $('<img>', {
                    src: '../img/logo2.png',
                    alt: 'Assistant'
                })
            );
            $messageContainer.append($iconDiv);
        }

        const $message = $('<div>')
            .addClass(`message ${type}`)
            .html(text);
        
        $messageContainer.append($message);
        $messagesContainer.append($messageContainer);
        $messagesContainer.scrollTop($messagesContainer[0].scrollHeight);
    }
}

function setInputLoading() {
    const $startChatBtn = $('#startChatBtn');
    const $welcomeMessage = $('.welcome-message');
    const $queryInput = $('#queryInput');   

    $startChatBtn.on('click', () => {
        // First, ensure any existing fade animations are complete
        $welcomeMessage.stop().fadeOut(100, function() {
            initializingMessage(websiteInfo.hostName, websiteInfo.favicon);
            
            chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
                $.ajax({
                    url: 'http://127.0.0.1:7777/initialize_rag',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({ web_url: websiteInfo.url }),
                    success: (response) => {
                        console.log(response);
                        if (response.status === 'success') {
                            $welcomeMessage.stop().fadeOut(100, function() {
                                startNewChat(websiteInfo.hostName, websiteInfo.favicon);
                            });
                        } else {
                            alert('Failed to initialize RAG:', response.message);
                        }
                    },
                    error: (xhr, status, error) => {
                        alert('Error initializing RAG:', error);
                    }
                });
            });
        });
    });
    
    function initializingMessage(hostName, hostLogo) {
        conversationId = generateConversationId();
        $('.message-container').remove();
        $welcomeMessage.hide().html(`
            <div class="align-items-center mb-2">
                <span class="mb-4 welcome-title-intro">Initializing chating system for</span>
                <span class="text-muted mb-4 welcome-title-intro"><img src="${hostLogo}" alt="Logo" class="welcome-icon-intro">${hostName}</span>
                <h5><span class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></span></h5>
            </div>
        `).fadeIn(300);
        $queryInput.val('');
        $queryInput.prop('placeholder', 'Waiting for initializing...');
    }

    // Start a new chat
    function startNewChat(hostName, hostLogo) {
        conversationId = generateConversationId();
        $('.message-container').remove();
        $welcomeMessage.hide().html(`
            <div class="align-items-center mb-2">
                <span class="mb-4 welcome-title-intro">Hello! Ask me anything about</span>
                <span class="text-muted welcome-title-intro"><img src="${hostLogo}" alt="Logo" class="welcome-icon-intro">${hostName}</span>
            </div>
        `).fadeIn(300);
        $queryInput.val('');
        $queryInput.prop('placeholder', 'Type your question here...');
    }
}

function generateConversationId() {
    return `conv-${Math.random().toString(36).substring(2, 10)}`;
}

// Get the website info from the url
function getWebsiteInfoFromUrl(url) {
    const urlObj = new URL(url);
    const title = urlObj.hostname;
    const domainName = urlObj.hostname;
    const hostName = domainName.replace('www.', '').split('.')[0];
    const subdomain = urlObj.pathname.split('/')[1] ?
        `${domainName}/${urlObj.pathname.split('/')[1]}/` :
        domainName + '/';
    const favicon = `https://www.google.com/s2/favicons?domain=${domainName}`;
        
    return {
        url: url, 
        title: title, 
        domainName: domainName, 
        hostName: hostName, 
        subdomain: subdomain,
        favicon: favicon
    };
}
