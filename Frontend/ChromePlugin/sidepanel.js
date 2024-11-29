import { ChatManager } from './modules/chatManager.js';
import { WebsiteManager } from './modules/websiteManager.js';
import { UIManager } from './modules/uiManager.js';

$(document).ready(function() {
    // Initialize UIManager
    const uiManager = new UIManager();
    // Initialize WebsiteManager
    const websiteManager = new WebsiteManager();
    // Initialize ChatManager
    const chatManager = new ChatManager();

    // Add handler for the start crawl button
    $('#startCrawlBtn').on('click', async function() {
        const companyName = $('#companyName').val()?.trim() || '';
        const domainLimit = $('#subdomainLimit').val()?.trim() || '';
        if (!companyName) {
            alert('Please enter a company name');
            return;
        }
        try {
            uiManager.hideModal('#crawlParametersModal');
            uiManager.$crawlButton.prop('disabled', true)
                .html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Crawling...');
                
            const result = await websiteManager.startCrawl(companyName, domainLimit);
            chatManager.addMessage(result.message);
        } catch (error) {
            chatManager.addMessage(`Error during crawling: ${error.message}`);
        } finally {
            uiManager.$crawlButton.prop('disabled', false)
                       .html('<i class="bi bi-spider me-2"></i>Analyze');
        }
    });

    // Update the new conversation handler
    uiManager.$newConversationBtn.on('click', function() {
        chatManager.startNewChat('', '');
    });

    // Update history conversations handler
    uiManager.$historyConversationsBtn.on('click', async function() {
        try {
            const chatHistory = await chatManager.loadAllChatHistory('test1');
            chatManager.updateChatHistoryList(chatHistory);
            uiManager.showModal('#chatHistoryModal');
        } catch (error) {
            console.error('Error fetching chat history:', error);
        }
    });

    // Update chat history entry click handler
    $(document).on('click', '.chat-history-entry', function() {
        const chatId = $(this).data('chat-id');
        if (chatManager.loadChat(chatId)) {
            uiManager.hideModal('#chatHistoryModal');
        }
    });

    // Update history list
    async function updateHistoryList() {
        try {
            const websites = await websiteManager.loadAllWebsitesHistory();
            websiteManager.updateWebsitesHistoryList(websites);
        } catch (error) {
            console.error('Error updating history list:', error);
        }
    }

    // Update history when history tab is shown
    $('#history-tab').on('shown.bs.tab', function() {
        updateHistoryList();
    });

    // Update website entry click handler
    $(document).on('click', '.website-entry', function() {
        const url = $(this).data('url');
        const websiteData = websiteManager.getWebsiteData(url);
        if (!websiteData) return;
        
        const $modal = uiManager.$websiteDetailsModal;
        
        // Update modal content
        const faviconUrl = websiteManager.getFaviconUrl(websiteData.start_urls[0]);
        $modal.find('.company-name').html(`
            <img src="${faviconUrl}" alt="">
            <span>${websiteData.company_name}</span>
        `);
        
        $modal.find('.start-url')
            .text(websiteData.start_urls[0])
            .attr('href', websiteData.start_urls[0]);
        $modal.find('.pages-count').text(websiteData.visited_urls.length);
        $modal.find('.domains-count').text(Object.keys(websiteData.domain_urls).length);
        
        // Update domains list
        const $domainsList = $modal.find('.domains-list').empty();
        Object.entries(websiteData.domain_urls).forEach(([domain, count]) => {
            $domainsList.append(`
                <div class="domain-item d-flex justify-content-between align-items-center mb-1">
                    <span class="domain-name">${domain}</span>
                    <span class="domain-count badge">${count} pages</span>
                </div>
            `);
        });
        
        // Update failed URLs list with show more functionality
        const $failedList = $modal.find('.failed-urls-list').empty();
        if (websiteData.failed_urls && websiteData.failed_urls.length > 0) {
            const initialDisplay = 3;
            const totalUrls = websiteData.failed_urls.length;
            
            // Add first 3 URLs
            websiteData.failed_urls.slice(0, initialDisplay).forEach(([url, reason]) => {
                $failedList.append(`
                    <div class="failed-url-item mb-1">
                        <div class="text-truncate">${url}</div>
                        <small class="text-danger">${reason}</small>
                    </div>
                `);
            });
            
            // Add show more button if there are more than 3 URLs
            if (totalUrls > initialDisplay) {
                const remainingUrls = websiteData.failed_urls.slice(initialDisplay);
                const $remainingUrlsDiv = $('<div>').addClass('remaining-urls d-none');
                
                remainingUrls.forEach(([url, reason]) => {
                    $remainingUrlsDiv.append(`
                        <div class="failed-url-item mb-1">
                            <div class="text-truncate">${url}</div>
                            <small class="text-danger">${reason}</small>
                        </div>
                    `);
                });
                
                const $showMoreBtn = $(`
                    <button class="btn btn-link btn-sm text-decoration-none show-more-btn">
                        <i class="bi bi-plus-circle me-1"></i>
                        Show ${remainingUrls.length} more
                    </button>
                `);
                
                $showMoreBtn.on('click', function() {
                    const $btn = $(this);
                    const $remaining = $failedList.find('.remaining-urls');
                    
                    if ($remaining.hasClass('d-none')) {
                        $remaining.removeClass('d-none');
                        $btn.html('<i class="bi bi-dash-circle me-1"></i>Show less');
                    } else {
                        $remaining.addClass('d-none');
                        $btn.html(`<i class="bi bi-plus-circle me-1"></i>Show ${remainingUrls.length} more`);
                    }
                });
                
                $failedList.append($remainingUrlsDiv);
                $failedList.append($showMoreBtn);
            }
        } else {
            $failedList.append('<p class="text-muted mb-0">No failed URLs</p>');
        }
        
        // Show modal
        uiManager.showModal($modal);
    });

    // Add event listener for modal hidden event
    uiManager.$websiteDetailsModal.on('hidden.bs.modal', function () {
        // Ensure the button loses focus after modal is hidden
        uiManager.$startChatBtn.blur();
    });

    // Add separate click handler for start chat button
    uiManager.$startChatBtn.on('click', function() {
        // Small delay to ensure modal is fully closed before starting chat
        setTimeout(startNewChat, 100);
    });

    // StartNewChat function
    function startNewChat() {
        const companyInfo = uiManager.$startChatBtn.closest('.modal-content').find('.company-name');
        const companyName = companyInfo.find('span').text();
        const companyLogo = companyInfo.find('img').attr('src');
        chatManager.startNewChat(companyName, companyLogo);
        $('#chat-tab').tab('show');
    }
}); 