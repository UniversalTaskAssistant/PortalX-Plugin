export class UIManager {
    constructor() {
        this.$crawlButton = $('#crawlButton');
        this.$newConversationBtn = $('#newConversationBtn');
        this.$historyConversationsBtn = $('#historyConversationsBtn');
        this.$websiteDetailsModal = $('#websiteDetailsModal');
        this.$startChatBtn = $('.start-chat-btn');
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
