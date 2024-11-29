export class UIManager {
    constructor() {
        this.$crawlButton = $('#crawlButton');
        this.$newConversationBtn = $('#newConversationBtn');
        this.$historyConversationsBtn = $('#historyConversationsBtn');
        this.$chatHistoryList = $('#chatHistoryList');
        this.$websiteDetailsModal = $('#websiteDetailsModal');
        this.$startChatBtn = $('.start-chat-btn');
        
        this.initializeTooltips();
    }

    initializeTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

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

    showModal(modalId) {
        const modal = new bootstrap.Modal(modalId);
        modal.show();
    }

    hideModal(modalId) {
        const modal = bootstrap.Modal.getInstance(modalId);
        modal.hide();
    }
}
