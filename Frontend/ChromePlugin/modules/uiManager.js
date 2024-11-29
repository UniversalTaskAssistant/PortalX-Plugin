export class UIManager {
    constructor() {
        this.$crawlButton = $('#crawlButton');
        this.$newConversationBtn = $('#newConversationBtn');
        this.$historyConversationsBtn = $('#historyConversationsBtn');
        this.$chatHistoryList = $('#chatHistoryList');
        this.$historyList = $('#history-list');
        this.$websiteSearch = $('#websiteSearch');
        this.$websiteDetailsModal = $('#websiteDetailsModal');
        this.$startChatBtn = $('.start-chat-btn');
        
        this.initializeTooltips();
        this.addSearchFunctionality();
    }

    initializeTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    addSearchFunctionality() {
        this.$websiteSearch.on('input', function() {
            const searchTerm = $(this).val().toLowerCase();
            $('.website-entry').each(function() {
                const text = $(this).text().toLowerCase();
                $(this).toggle(text.includes(searchTerm));
            });
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

    updateHistoryList(websites, websiteManager) {
        this.$historyList.empty();
        websites.forEach(site => {
            const faviconUrl = websiteManager.getFaviconUrl(site.start_urls[0]);
            const websiteEntry = `
                <div class="website-entry" data-url="${site.start_urls[0]}">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <div class="d-flex align-items-center">
                            <img src="${faviconUrl}" alt="" class="website-favicon me-2">
                            <h6 class="mb-0">${site.company_name}</h6>
                        </div>
                        <small class="text-muted">${websiteManager.formatTimestamp(site.crawl_time)}</small>
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
            this.$historyList.append(websiteEntry);
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
