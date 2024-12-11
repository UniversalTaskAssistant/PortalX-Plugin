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
            setTimeout(() => this.startNewChatWithCompanyInfo(), 100);
        });

        // Chat history entry click handler
        $(document).on('click', '.chat-history-entry', (e) => {
            const chatId = $(e.currentTarget).data('chat-id');
            if (this.loadChat(chatId)) {
                const modal = bootstrap.Modal.getInstance('#chatHistoryModal');
                modal.hide();
            }
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
    startNewChat(companyName, companyLogo) {
        this.conversationId = this.generateConversationId();
        $('.message-container').remove();
        this.$welcomeMessage.html(`
            <div class="align-items-center mb-2">
                <h5 class="mb-4">Hello! Ask me anything about</h5>
                <h5 class="text-muted"><img src="${companyLogo}" alt="Logo" class="me-2" style="width: 20px; height: 20px;">${companyName}</h5>
            </div>
        `).show();
        this.$queryInput.val('');
        this.$queryInput.prop('placeholder', 'Type your question here...');
    }

    // Update the selected website tab
    updateSelectedWebsiteTab(companyName, companyLogo, startUrl) {
        const $selectedWebsite = $('.selected-website');
        $selectedWebsite.empty();
        $selectedWebsite.attr('data-url', startUrl);
        $selectedWebsite.append(`
            <h6 class="text-muted"><img src="${companyLogo}" alt="Logo" class="me-2" style="width: 20px; height: 20px;">${companyName}</h6>
        `);
        $('#changeWebsiteBtn').text('Change');
    }

    // Initialize chat message for the selected website
    initializingMessage(companyName, companyLogo) {
        this.conversationId = this.generateConversationId();
        $('.message-container').remove();
        this.$welcomeMessage.html(`
            <div class="align-items-center mb-2">
                <h5 class="mb-4">Initializing chating system for</h5>
                <h5 class="text-muted"><img src="${companyLogo}" alt="Logo" class="me-2" style="width: 20px; height: 20px;">${companyName}</h5>
                <h5><span class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></span></h5>
            </div>
        `).show();
        this.$queryInput.val('');
        this.$queryInput.prop('placeholder', 'Waiting for initializing...');
    }

    // Start a new chat with company info
    startNewChatWithCompanyInfo() {
        const companyInfo = this.$startChatBtn.closest('.modal-content').find('.company-name');
        const companyName = companyInfo.find('span').text();
        const companyLogo = companyInfo.find('img').attr('src');
        const startUrl = this.$startChatBtn.closest('.modal-content').find('.start-url').attr('href');
        this.currentChatWebsite = {
            startUrl: startUrl,
            name: companyName,
            logo: companyLogo
        };
        $('#chat-tab').tab('show');

        // Disable input while initializing RAG
        this.setQueryButtonLoading(true);
        this.initializingMessage(companyName, companyLogo);

        // Initialize RAG before starting the chat
        $.ajax({
            url: 'http://127.0.0.1:7777/initialize_rag',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ web_url: startUrl }),
            success: (response) => {
                if (response.status === 'success') {
                    this.setQueryButtonLoading(false);
                    this.startNewChat(companyName, companyLogo);
                    this.updateSelectedWebsiteTab(companyName, companyLogo, startUrl);
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

    // Load a chat by id (conversation id)
    loadChat(chatId) {
        const selectedChat = this.chatHistory.find(chat => chat.conversation_id === chatId);
        if (selectedChat) {
            this.conversationId = chatId;
            $('.message-container').remove();
            this.$welcomeMessage.hide();
            selectedChat.conversation.forEach(msg => {
                this.addMessage(msg.content, msg.rule === 'user');
            });
            return true;
        }
        return false;
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
        this.$chatHistoryList.empty();
        chatHistory.forEach(chat => {
            const firstMessage = chat.conversation.find(msg => msg.rule === 'user')?.content || 'Empty conversation';
            const chatEntry = `
                <div class="chat-history-entry p-3" data-chat-id="${chat.conversation_id}">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <span class="preview-text">${firstMessage}</span>
                    </div>
                    <small class="text-muted">${chat.timestamp}</small>
                </div>
            `;
            this.$chatHistoryList.append(chatEntry);
        });
    }

    // Add these as public methods to be called from sidepanel.js
    setQueryButtonLoading(isLoading) {
        if (isLoading) {
            this.$queryButton.prop('disabled', true)
                .addClass('loading')
                .html('<span class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></span>');
            this.$queryInput.prop('disabled', true);
        } else {
            this.$queryButton.prop('disabled', false)
                .removeClass('loading')
                .html('<i class="bi bi-send-fill"></i>');
            this.$queryInput.prop('disabled', false);
        }
    }

    getQueryInput() {
        return this.$queryInput.val().trim();
    }

    clearQueryInput() {
        this.$queryInput.val('');
    }
}
