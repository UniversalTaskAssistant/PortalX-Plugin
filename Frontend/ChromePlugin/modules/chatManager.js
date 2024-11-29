export class ChatManager {
    constructor() {
        this.$responseDiv = $('#response');
        this.$queryButton = $('#queryButton');
        this.$queryInput = $('#queryInput');
        this.$welcomeMessage = $('.welcome-msg');
        this.conversationId = this.generateConversationId();
        this.chatHistory = [];
        
        this.initializeEventListeners();
    }

    generateConversationId() {
        return `conv-${Math.random().toString(36).substring(2, 10)}`;
    }

    initializeEventListeners() {
        this.$queryButton.on('click', () => this.handleQuery());
        this.$queryInput.on('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.$queryButton.click();
            }
        });
    }

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

    async loadChatHistory(userId) {
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

    loadConversation(chatId) {
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
}
