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
        
        this.initializeEventListeners();
    }

    // ****************************
    // ****** INITIALIZATION ******
    // Initialize event listeners
    initializeEventListeners() {
        // Query button click handler
        this.$queryButton.on('click', () => this.handleQuery());

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
    addMessage(text, isUser = false) {
        if (this.$welcomeMessage.is(':visible')) {
            this.$welcomeMessage.hide();
        }
        const $messageContainer = $('<div>', {
            class: 'message-container'
        });
        const $messageDiv = $('<div>', {
            class: `message ${isUser ? 'user' : 'assistant'}`,
            text: text
        });
        $messageContainer.append($messageDiv);
        this.$responseDiv.append($messageContainer);
        $messageDiv[0].scrollIntoView({ behavior: 'smooth' });
    }

    // Handle the user query and send it to the server
    async handleQuery() {
        const query = this.$queryInput.val().trim();
        if (!query) {
            this.addMessage('Please enter a question', true);
            return;
        }
        try {
            this.$queryButton.prop('disabled', true)
                .addClass('loading')
                .html('<span class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></span>');
            this.$queryInput.prop('disabled', true);
            
            this.addMessage(query, true);
            
            const response = await $.ajax({
                url: 'http://localhost:7777/query',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    user_id: 'test1',
                    conversation_id: this.conversationId,
                    query: query,
                    web_url: 'https://www.tum.de/en/'
                })
            });
            this.addMessage(response.answer);
            this.$queryInput.val('');
        } catch (error) {
            this.addMessage(`Error getting response: ${error.message}`);
        } finally {
            this.$queryButton.prop('disabled', false)
                .removeClass('loading')
                .html('<i class="bi bi-send-fill"></i>');
            this.$queryInput.prop('disabled', false);
        }
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
                <h5>Hello! Ask me anything about</h5>
                <h5 class="text-muted"><img src="${companyLogo}" alt="Logo" class="me-2" style="width: 20px; height: 20px;">${companyName}</h5>
            </div>
        `).show();
        this.$queryInput.val('');
    }

    // Start a new chat with company info
    startNewChatWithCompanyInfo() {
        const companyInfo = this.$startChatBtn.closest('.modal-content').find('.company-name');
        const companyName = companyInfo.find('span').text();
        const companyLogo = companyInfo.find('img').attr('src');
        this.startNewChat(companyName, companyLogo);
        $('#chat-tab').tab('show');
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
}
