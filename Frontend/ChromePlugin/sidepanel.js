$(document).ready(function() {
    const $crawlButton = $('#crawlButton');
    const $queryButton = $('#queryButton');
    const $responseDiv = $('#response');
    const $queryInput = $('#queryInput');
    const $welcomeMessage = $('.welcome-msg');
    const $newConversationBtn = $('#newConversationBtn');
    const $historyConversationsBtn = $('#historyConversationsBtn');
    let currentUrl = '';
    let chatHistory = [];
    let conversationId = `conv-${Math.random().toString(36).substring(2, 10)}`;

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
                    conversation_id: conversationId,
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

    // New conversation handler
    $newConversationBtn.on('click', function() {
        // Generate new conversation ID
        conversationId = `conv-${Math.random().toString(36).substring(2, 10)}`;
        // Remove only the message containers
        $('.message-container').remove();
        $('.welcome-msg').fadeIn(300);
        $queryInput.val('');
    });

    // History conversations handler
    $historyConversationsBtn.on('click', async function() {
        try {
            // Fetch chat history from server
            const response = await fetch('http://127.0.0.1:7777/get_chat_history', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: 'test1'
                })
            });
            chatHistory = await response.json();
            // Clear and populate the chat history list
            const $chatHistoryList = $('#chatHistoryList');
            $chatHistoryList.empty();
            chatHistory.forEach(chat => {
                // Get the first user message as preview
                const firstMessage = chat.conversation.find(msg => msg.rule === 'user')?.content || 'Empty conversation';
                const chatEntry = `
                    <div class="chat-history-entry p-3" data-chat-id="${chat.conversation_id}">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <span class="preview-text">${firstMessage}</span>
                        </div>
                        <small class="text-muted">${chat.timestamp}</small>
                    </div>
                `;
                $chatHistoryList.append(chatEntry);
            });
            // Show the modal
            const chatHistoryModal = new bootstrap.Modal('#chatHistoryModal');
            chatHistoryModal.show();
        } catch (error) {
            console.error('Error fetching chat history:', error);
            // Handle error appropriately
        }
    });

    // Handle chat history entry click
    $(document).on('click', '.chat-history-entry', function() {
        const chatId = $(this).data('chat-id');
        // Find the chat in our loaded history
        const selectedChat = chatHistory.find(chat => chat.conversation_id === chatId);
        if (selectedChat) {
            // Update current conversation ID
            conversationId = chatId;
            // Clear current messages
            $('.message-container').remove();
            $('.welcome-msg').hide();
            // Display all messages from the conversation
            selectedChat.conversation.forEach(msg => {
                addMessage(msg.content, msg.rule === 'user');
            });
            // Close the modal
            $('#chatHistoryModal').modal('hide');
        }
    });

    // Add this function to format the crawl time
    function formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diffInMinutes = Math.floor((now - date) / (1000 * 60));
        
        if (diffInMinutes < 1) return 'just now';
        if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
        if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes/60)}h ago`;
        return `${Math.floor(diffInMinutes/1440)}d ago`;
    }

    // Add this function to update the history list
    function updateHistoryList() {
        $.ajax({
            url: 'http://localhost:7777/get_websites',
            method: 'GET',
            success: function(websites) {
                const $historyList = $('#history-list');
                // $historyList.empty();
                
                websites.forEach(site => {
                    const websiteEntry = `
                        <div class="website-entry">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <h6 class="mb-0">${site.company_name}</h6>
                                <small class="text-muted">${formatTimestamp(site.crawl_time)}</small>
                            </div>
                            <span class="url-text mb-3">${site.start_urls[0]}</span>
                            <div class="d-flex align-items-center">
                                <span class="badge ${site.crawl_finished ? 'bg-success' : 'bg-warning'} me-2">
                                    ${site.crawl_finished ? 'Analyzed' : 'In Progress'}
                                </span>
                                <span class="stats-text">${site.visited_urls.length} pages crawled</span>
                            </div>
                        </div>
                    `;
                    $historyList.append(websiteEntry);
                });
            },
            error: function(xhr, status, error) {
                console.error('Error fetching website history:', error);
            }
        });
    }

    // Update history when history tab is shown
    $('#history-tab').on('shown.bs.tab', function() {
        updateHistoryList();
    });
    
    // Add search functionality
    $('#websiteSearch').on('input', function() {
        const searchTerm = $(this).val().toLowerCase();
        $('.website-entry').each(function() {
            const text = $(this).text().toLowerCase();
            $(this).toggle(text.includes(searchTerm));
        });
    });
}); 