let conversationId = generateConversationId();
let websiteInfo = {}; 

$(document).ready(() => {
    initializePopup();
    setChat();
    setStart();
    setAnalyze();
});

function initializePopup() {
    const $newChatBtn = $('#newChatBtn');
    const $minimizeBtn = $('.minimize-btn');
    const $welcomeMessage = $('.welcome-message');

    // Get current tab's domain and update favicon
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
        websiteInfo = getWebsiteInfoFromUrl(tabs[0].url);
        websiteInfo.hostLogo = tabs[0].favIconUrl;
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
    const $recomQuestion = $('.recommendation-item');

    $sendButton.on('click', sendMessage);
    $queryInput.on('keypress', (e) => {
        if (e.which === 13 && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    $(document).on('click', '.recommendation-item', (e) => {
        const question = $(e.target).text();
        $queryInput.val(question);
        sendMessage();
    });


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
                    web_url: addHttps(websiteInfo.domainName),
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
                    data: JSON.stringify({ web_url: addHttps(websiteInfo.domainName) }),
                    success: (response) => {
                        if (response.status === 'success') {
                            $welcomeMessage.stop().fadeOut(100, function() {
                                startNewChat(websiteInfo.hostName, websiteInfo.hostLogo);
                                showRecommendedQuestions(response.recommended_questions);
                            });
                        } else if (response.status === 'not_found') {
                            $startChatBtn.text('Website not analyzed yet');
                            showAnalyzingMessage();
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
        $welcomeMessage.hide().html(`
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
        
        $startChatBtn.prop('disabled', false);
        $startChatBtn.html('<i class="bi bi-chat-dots-fill me-2"></i>Start chat with this website');
    }

    function showAnalyzingMessage() {
        $welcomeMessage.hide();
        $('.message-container').remove();

        $('#messagesContainer').append(`
            <div class="message-container assistant-container">
                <div class="assistant-icon">
                    <img src="../img/logo2.png" alt="Assistant">
                </div>
                <div class="message assistant">
                    This website hasn't been analyzed yet. Would you like me to analyze it for you?
                    <div style="margin-top: 12px;">
                        <button id="startAnalyzeBtn" class="modal-btn">
                            <i class="bi bi-ui-checks-grid"></i>Analyze Website
                        </button>
                    </div>
                </div>
            </div>
        `);
    }

    function showRecommendedQuestions(questions) {
        /*
        questions:
        <div class="recommendation">
            <p class="recommendation-item">What should I bring to my first appointment?</p>
            <p class="recommendation-item">How can I book an appointment online?</p>
            <p class="recommendation-item">Where are your clinic locations?</p>
        </div>
        */
        $welcomeMessage.append(questions);
    }
}

function setAnalyze() {
    $(document).on('click', '#startAnalyzeBtn', async () => {
        try {
            const response = await $.ajax({
                url: 'http://localhost:7777/crawl',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    domainName: addHttps(websiteInfo.domainName),
                    hostName: websiteInfo.hostName,
                    domainLimit: addHttps(websiteInfo.subdomain)
                })
            });
            
            // If the request is successful, show the analyzing message
            showAnalyzingMessage();
            $('#startChatBtn').text('Analyze a few pages and you can start chatting');
            
        } catch (error) {
            console.error('Failed to start analysis:', error);
            showAnalysisFailureMessage('Failed to start website analysis. Please try again.');
        }
    });

    $(document).on('click', '.refresh-btn', async () => {
        try {
            const response = await $.ajax({
                url: 'http://localhost:7777/get_website_info',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    domainName: addHttps(websiteInfo.domainName)
                })
            });

            console.log(response);

            if (response.status === 'success') {
                const websiteData = response.data;
                // Update stats using the same format as websiteManager
                $('.pages-count').text(websiteData.visited_urls.length);
                $('.domains-count').text(Object.keys(websiteData.domain_urls).length);
                $('.failed-urls-count').text(websiteData.failed_urls?.length || 0);

                // Enable chat button if more than 10 pages analyzed
                if (websiteData.visited_urls.length >= 10) {
                    $('#startChatBtn')
                        .prop('disabled', false)
                        .html('<i class="bi bi-chat-dots-fill me-2"></i>Start chat with this website')
                        .removeClass('btn-secondary')
                        .addClass('btn-primary');
                }
            } else {
                console.error('Failed to get website info:', response.message);
            }
        } catch (error) {
            console.error('Error fetching website info:', error);
        }
    });

    function showAnalysisFailureMessage(message) {
        $('.welcome-message').hide();
        $('.message-container').remove();

        $('#messagesContainer').append(`
            <div class="message-container assistant-container">
                <div class="assistant-icon">
                    <img src="../img/logo2.png" alt="Assistant">
                </div>
                <div class="message assistant">
                    <div class="align-items-center">
                        <span class="text-danger">
                            <i class="fas fa-exclamation-circle"></i> Error
                        </span>
                        <p class="text-danger">${message}</p>
                        <button id="retryAnalyzeBtn" class="btn btn-outline-primary">Try Again</button>
                    </div>
                </div>
            </div>
        `);

        $('#retryAnalyzeBtn').on('click', function() {
            $('#startAnalyzeBtn').trigger('click');
        });
    }

    function showAnalyzingMessage() {
        $('.welcome-message').hide();
        $('.message-container').remove();

        // Update the current message to show loading state
        $('#messagesContainer').append(`
            <div class="message-container assistant-container">
                <div class="assistant-icon">
                    <img src="../img/logo2.png" alt="Assistant">
                </div>
                <div class="message assistant">
                    <div class="analysis-container">
                        <div class="mb-3">
                            Starting website analysis
                            <div class="thinking-indicator mt-1">
                                <span class="dot-1">.</span><span class="dot-2">.</span><span class="dot-3">.</span>
                                <span class="dot-4">.</span><span class="dot-5">.</span><span class="dot-6">.</span>
                            </div>
                        </div>
                        <div class="analysis-stats">
                            <div class="website-info mb-3">
                                <img src="${websiteInfo.hostLogo}" alt="Logo">
                                <span>${websiteInfo.hostName}</span>
                                <div class="spinner-border spinner-border-sm text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                                </div>
                                <button class="refresh-btn" title="Refresh website info">
                                    <i class="bi bi-arrow-clockwise"></i>
                                </button>
                            </div>
                            <div class="stats-grid">
                                <div class="stat-item">
                                    <div class="stat-value pages-count">0</div>
                                    <div class="stat-label">Pages</div>
                                </div>
                                <div class="stat-item">
                                    <div class="stat-value domains-count">0</div>
                                    <div class="stat-label">Domains</div>
                                </div>
                                <div class="stat-item">
                                    <div class="stat-value failed-urls-count">0</div>
                                    <div class="stat-label">Fails</div>
                                </div>
                            </div>
                        </div>
                    </div>  
                </div>
            </div>
        `);
    }
}


// ******* Helper Functions ******
// Generate a unique conversation id
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

function addHttps(url) {
    if (!url) return '';
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        return `https://${url}`;
    }
    return url;
}
