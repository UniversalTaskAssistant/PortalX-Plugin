let conversationId = generateConversationId();
let websiteInfo = {}; 

$(document).ready(() => {
    initializePopup();
    setChat();
    setStart();
});

function initializePopup() {
    const $newChatBtn = $('#newChatBtn');
    const $minimizeBtn = $('.minimize-btn');
    const $welcomeMessage = $('.welcome-message');

    // Get current tab's domain and update favicon
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
        websiteInfo = getWebsiteInfoFromUrl(tabs[0].url);
        websiteInfo.hostLogo = tabs[0].favIconUrl;
        console.log(websiteInfo);
        $('.website-favicon').attr('src', websiteInfo.hostLogo);
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

    async function sendMessage() {
        const query = $queryInput.val().trim();
        if (!query) return;

        // Clear input immediately
        $queryInput.val('');
        
        // Remove welcome message and add user message synchronously
        $('.welcome-message').hide();
        addMessage(query, 'user');
        
        // Add loading/thinking message after user message
        const $thinkingContainer = addThinkingMessage();

        try {
            const response = await $.ajax({
                url: 'http://localhost:7777/query',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    user_id: 'test1', // You might want to get this from user settings
                    conversation_id: conversationId,
                    query: query,
                    web_url: websiteInfo.url,
                    host_name: websiteInfo.hostName,
                    host_logo: websiteInfo.hostLogo
                })
            });

            // Remove thinking message
            $thinkingContainer.remove();
            
            // Add response message
            addMessage(response.answer, 'assistant');

        } catch (error) {
            // Remove thinking message
            $thinkingContainer.remove();
            
            // Add error message
            addMessage(`Error: ${error.message}`, 'assistant');
        }
    }

    function addThinkingMessage() {
        const $container = $('<div>', {
            class: 'message-container assistant-container thinking-message'
        });

        const $iconDiv = $('<div>', {
            class: 'assistant-icon'
        }).append(
            $('<img>', {
                src: '../img/logo2.png',
                alt: 'Assistant'
            })
        );

        const $message = $('<div>')
            .addClass('message assistant')
            .append(
                $('<div>', {
                    class: 'thinking-indicator'
                }).html('Thinking <span class="dot-1">.</span><span class="dot-2">.</span><span class="dot-3">.</span><span class="dot-4">.</span><span class="dot-5">.</span><span class="dot-6">.</span>')
            );

        $container.append($iconDiv, $message);
        $messagesContainer.append($container);
        $messagesContainer.scrollTop($messagesContainer[0].scrollHeight);

        return $container;
    }

    $sendButton.on('click', sendMessage);
    $queryInput.on('keypress', (e) => {
        if (e.which === 13 && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
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

function setStart() {
    const $startChatBtn = $('#startChatBtn');
    const $welcomeMessage = $('.welcome-message');
    const $inputSection = $('.input-section');
    const $queryInput = $('#queryInput');   

    $startChatBtn.on('click', () => {
        // Disable the start chat button
        $startChatBtn.prop('disabled', true);
        $startChatBtn.text('Loading...');

        // Ensure any existing fade animations are complete
        $welcomeMessage.stop().fadeOut(100, function() {
            showInitializingMessage(websiteInfo.hostName, websiteInfo.hostLogo);
            
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
                                startNewChat(websiteInfo.hostName, websiteInfo.hostLogo);
                            });
                        } else if (response.status === 'not_found') {
                            showFailureMessage(response.message);
                        } else {
                            showFailureMessage('Failed to initialize chat system');
                        }
                    },
                    error: (xhr, status, error) => {
                        showFailureMessage('Unable to connect to the server. Please try again.');
                    }
                });
            });
        });
    });

    function startNewChat(hostName, hostLogo) {
        conversationId = generateConversationId();
        $('.message-container').remove();
        $welcomeMessage.hide().html(`
            <div class="align-items-center mb-2">
                <span class="mb-4 welcome-title-intro">Hello! Ask me anything about</span>
                <span class="text-muted welcome-title-intro"><img src="${hostLogo}" alt="Logo" class="welcome-icon-intro">${hostName}</span>
            </div>
        `).fadeIn(300);
        $startChatBtn.fadeOut(100, function() {
            $queryInput.val('');
            $queryInput.prop('placeholder', 'Type your question here...');
            $inputSection.fadeIn(300);
        });
    }
    
    function showInitializingMessage(hostName, hostLogo) {
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

    function showFailureMessage(message) {
        $welcomeMessage.stop().fadeOut(100, function() {
            $welcomeMessage.html(`
                <div class="align-items-center mb-2">
                    <span class="mb-4 welcome-title-intro text-danger">
                        <i class="fas fa-exclamation-circle"></i> Error
                    </span>
                    <p class="text-danger">${message}</p>
                    <button class="btn btn-outline-primary retry-btn">Try Again</button>
                </div>
            `).fadeIn(300);

            $('.retry-btn').on('click', function() {
                $startChatBtn.trigger('click');
            });
        });
        
        $startChatBtn.prop('disabled', false);
        $startChatBtn.html('<i class="bi bi-chat-dots-fill me-2"></i>Start Chat with this Website');
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
        hostLogo: favicon
    };
}
