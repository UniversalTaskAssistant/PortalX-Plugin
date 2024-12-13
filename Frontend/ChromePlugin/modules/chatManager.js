export class ChatManager {
    constructor() {
        this.$responseDiv = $('#response');
        this.$queryButton = $('#queryButton');
        this.$queryInput = $('#queryInput');
        this.$welcomeMessage = $('.welcome-msg');
        this.$chatHistoryList = $('#chatHistoryList');
        this.$newConversationBtn = $('#newConversationBtn');
        this.$historyConversationsBtn = $('#historyConversationsBtn');
        this.$chatHistoryModal = $('#chatHistoryModal');
        this.$startChatBtn = $('.start-chat-btn');

        this.conversationId = this.generateConversationId();
        this.chatHistory = [];

        this.currentChatWebsite = {
        };
        
        this.initializeEventListeners();
    }

    // ****************************
    // ****** INITIALIZATION ******
    // Initialize event listeners
    initializeEventListeners() {
        // Query input keypress handler
        this.$queryInput.on('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.$queryButton.click();
            }
        });

        // New conversation button click handler
        this.$newConversationBtn.on('click', () => {
            this.startNewChat('', '');
        });

        // History conversations handler
        this.$historyConversationsBtn.on('click', async () => {
            try {
                const chatHistory = await this.loadAllChatHistory('test1');
                this.updateChatHistoryList(chatHistory);
                const modal = new bootstrap.Modal(this.$chatHistoryModal);
                modal.show();
            } catch (error) {
                console.error('Error fetching chat history:', error);
            }
        });

        // Start chat button click handler
        this.$startChatBtn.on('click', () => {
            const hostInfo = this.$startChatBtn.closest('.modal-content').find('.company-name');
            const hostName = hostInfo.find('span').text();
            const hostLogo = hostInfo.find('img').attr('src');
            const domainUrl = this.$startChatBtn.closest('.modal-content').find('.domain-url').attr('href');
            this.currentChatWebsite = {
                domainUrl: domainUrl,
                name: hostName,
                logo: hostLogo
            };
            setTimeout(() => this.startRagChatForCurrentWebsite(true), 100);
        });

        // Chat history entry click handler
        $(document).on('click', '.chat-history-entry', (e) => {
            // Hide the chat history modal
            const modal = bootstrap.Modal.getInstance('#chatHistoryModal');
            modal.hide();

            // Load the selected chat info
            const chatId = $(e.currentTarget).data('chat-id');
            const selectedChat = this.chatHistory.find(chat => chat.conversation_id === chatId);
            this.conversationId = chatId;
            this.currentChatWebsite = {
                domainUrl: selectedChat.host_url,
                name: selectedChat.host_name,
                logo: selectedChat.host_logo
            };  

            // Initialize RAG for the selected chat and display it
            this.startRagChatForCurrentWebsite(false, selectedChat);
        });
    }

    // *******************************
    // ****** MESSAGES HANDLING ******
    // Add a message to the chat section
    addMessage(message, isUser = false) {
        if (this.$welcomeMessage.is(':visible')) {
            this.$welcomeMessage.hide();
        }
        
        const $messageContainer = $('<div>', {
            class: `message-container ${isUser ? '' : 'assistant-container'}`
        });

        if (!isUser) {
            // Add assistant icon
            const $iconDiv = $('<div>', {
                class: 'assistant-icon'
            }).append(
                $('<img>', {
                    src: 'img/logo2.png',
                    alt: 'Assistant'
                })
            );
            $messageContainer.append($iconDiv);
        }

        const $messageDiv = $('<div>', {
            class: `message ${isUser ? 'user' : 'assistant'}`
        }).html(message);
        
        $messageContainer.append($messageDiv);
        this.$responseDiv.append($messageContainer);
        
        // Scroll to the bottom of the response div
        this.$responseDiv.scrollTop(this.$responseDiv[0].scrollHeight);
    }

    // ***************************
    // ****** CHAT HANDLING ******
    // Generate a conversation ID
    generateConversationId() {
        return `conv-${Math.random().toString(36).substring(2, 10)}`;
    }

    // Start a new chat
    startNewChat(hostName, hostLogo) {
        this.conversationId = this.generateConversationId();
        $('.message-container').remove();
        this.$welcomeMessage.html(`
            <div class="align-items-center mb-2">
                <h5 class="mb-4">Hello! Ask me anything about</h5>
                <h5 class="text-muted"><img src="${hostLogo}" alt="Logo" class="me-2" style="width: 20px; height: 20px;">${hostName}</h5>
            </div>
        `).show();
        this.$queryInput.val('');
        this.$queryInput.prop('placeholder', 'Type your question here...');
    }

    // Update the selected website tab
    updateSelectedWebsiteTab(hostName, hostLogo, domainUrl) {
        const $selectedWebsite = $('.selected-website');
        $selectedWebsite.empty();
        $selectedWebsite.attr('data-url', domainUrl);
        $selectedWebsite.append(`
            <h6 class="text-muted"><img src="${hostLogo}" alt="Logo" class="me-2" style="width: 20px; height: 20px;">${hostName}</h6>
        `);
        $('#changeWebsiteBtn').text('Change');
    }

    // Initialize chat message for the selected website
    initializingMessage(hostName, hostLogo) {
        this.conversationId = this.generateConversationId();
        $('.message-container').remove();
        this.$welcomeMessage.html(`
            <div class="align-items-center mb-2">
                <h5 class="mb-4">Initializing chating system for</h5>
                <h5 class="text-muted mb-4"><img src="${hostLogo}" alt="Logo" class="me-2" style="width: 20px; height: 20px;">${hostName}</h5>
                <h5><span class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></span></h5>
            </div>
        `).show();
        this.$queryInput.val('');
        this.$queryInput.prop('placeholder', 'Waiting for initializing...');
    }

    // Start a new chat with host info
    startRagChatForCurrentWebsite(newChat = true, selectedChat = null) {
        $('#chat-tab').tab('show');

        // Disable input while initializing RAG
        this.setQueryButtonLoading(true);
        this.initializingMessage(this.currentChatWebsite.name, this.currentChatWebsite.logo);
        this.updateSelectedWebsiteTab(this.currentChatWebsite.name, this.currentChatWebsite.logo, this.currentChatWebsite.domainUrl);

        // Initialize RAG before starting the chat
        $.ajax({
            url: 'http://127.0.0.1:7777/initialize_rag',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ web_url: this.currentChatWebsite.domainUrl }),
            success: (response) => {
                if (response.status === 'success') {
                    this.setQueryButtonLoading(false);
                    if (newChat) {
                        this.startNewChat(this.currentChatWebsite.name, this.currentChatWebsite.logo);
                    }
                    else if (selectedChat) {
                        // Display the selected chat
                        $('.message-container').remove();
                        this.$welcomeMessage.hide();
                        selectedChat.conversation.forEach(msg => {
                            this.addMessage(msg.content, msg.rule === 'user');
                        });
                    }
                } else {
                    console.error('Failed to initialize RAG:', response.message);
                    this.addMessage("Failed to initialize chat capabilities. Please try again.");
                    this.setQueryButtonLoading(false);
                }
            },
            error: (xhr, status, error) => {
                console.error('Error initializing RAG:', error);
                this.addMessage("Failed to initialize chat capabilities. Please try again.");
                this.setQueryButtonLoading(false);
            }
        });
    }

    // Load all chat history for a user
    async loadAllChatHistory(userId) {
        try {
            const response = await fetch('http://127.0.0.1:7777/get_chat_history', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ user_id: userId })
            });
            this.chatHistory = await response.json();
            return this.chatHistory;
        } catch (error) {
            console.error('Error fetching chat history:', error);
            throw error;
        }
    }

    // Update the chat history list
    updateChatHistoryList(chatHistory) {
        if (chatHistory.length === 0) {
            return;
        }
        this.$chatHistoryList.empty();
        chatHistory.forEach(chat => {
            const firstMessage = chat.conversation.find(msg => msg.rule === 'user')?.content || 'Empty conversation';
            const hostLogoHtml = chat.host_logo ? 
                `<img src="${chat.host_logo}" alt="Host Logo" class="me-1" style="width: 16px; height: 16px;">` : '';
            const hostNameHtml = chat.host_name ? 
                `<span class="small">${chat.host_name}</span>` : '';
            
            const chatEntry = `
                <div class="chat-history-entry p-3" data-chat-id="${chat.conversation_id}">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <span class="preview-text">${firstMessage}</span>
                    </div>
                    <div class="d-flex align-items-center gap-1"">
                        <small class="text-muted">${chat.timestamp}</small>
                        ${hostLogoHtml ? `<span class="ms-2 border-start ps-2" style="margin-top: -1px;">${hostLogoHtml}${hostNameHtml}</span>` : ''}
                    </div>
                </div>
            `;
            this.$chatHistoryList.append(chatEntry);
        });
    }

    setQueryButtonLoading(isLoading) {
        if (isLoading) {
            this.$queryButton.prop('disabled', true)
                .addClass('loading')
                .html('<span class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></span>');
            this.$queryInput.prop('disabled', true);
            this.$newConversationBtn.prop('disabled', true);
        } else {
            this.$queryButton.prop('disabled', false)
                .removeClass('loading')
                .html('<i class="bi bi-send-fill"></i>');
            this.$queryInput.prop('disabled', false);
            this.$newConversationBtn.prop('disabled', false);
        }
    }

    getQueryInput() {
        return this.$queryInput.val().trim();
    }

    clearQueryInput() {
        this.$queryInput.val('');
    }

    addThinkingMessage() {
        const $thinkingContainer = $('<div>', {
            class: 'message-container assistant-container thinking-message'
        });

        const $iconDiv = $('<div>', {
            class: 'assistant-icon'
        }).append(
            $('<img>', {
                src: 'img/logo2.png',
                alt: 'Assistant'
            })
        );

        const $messageDiv = $('<div>', {
            class: 'message assistant'
        }).append(
            $('<div>', {
                class: 'thinking-indicator'
            }).html('Thinking <span class="dot-1">.</span><span class="dot-2">.</span><span class="dot-3">.</span><span class="dot-4">.</span><span class="dot-5">.</span><span class="dot-6">.</span>')
        );
        
        $thinkingContainer.append($iconDiv, $messageDiv);
        this.$responseDiv.append($thinkingContainer);
        this.$responseDiv.scrollTop(this.$responseDiv[0].scrollHeight);
    }

    removeThinkingMessage() {
        $('.thinking-message').remove();
    }
}
