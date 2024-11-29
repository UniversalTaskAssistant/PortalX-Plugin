import { ChatManager } from './modules/chatManager.js';
import { WebsiteManager } from './modules/websiteManager.js';

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
    let currentWebsiteInfo = {
        url: '',
        title: '',
        domainName: '',
        hostName: '',
        subdomain: ''
    };
    let websitesData = new Map(); // Store website data with URL as key

    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Initialize WebsiteManager
    const websiteManager = new WebsiteManager();

    // Modify the crawl button click handler
    $crawlButton.on('click', function() {
        const currentInfo = websiteManager.getCurrentWebsiteInfo();
        // Pre-fill the domain field
        $('#websiteDomain').val(currentInfo.domainName);
        $('#hostName').val(currentInfo.hostName);
        $('#subdomainLimit').val(currentInfo.subdomain);
        // Show the modal
        const modal = new bootstrap.Modal('#crawlParametersModal');
        modal.show();
    });

    // Add handler for the start crawl button
    $('#startCrawlBtn').on('click', async function() {
        const modal = bootstrap.Modal.getInstance('#crawlParametersModal');
        const companyName = $('#hostName').val().trim();
        const domainLimit = $('#subdomainLimit').val().trim();
        
        try {
            modal.hide();
            $crawlButton.prop('disabled', true)
                .html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Crawling...');
                
            const result = await websiteManager.startCrawl(companyName, domainLimit);
            chatManager.addMessage(result.message);
        } catch (error) {
            chatManager.addMessage(`Error during crawling: ${error.message}`);
        } finally {
            $crawlButton.prop('disabled', false)
                       .html('<i class="bi bi-spider me-2"></i>Analyze');
        }
    });

    // Initialize ChatManager
    const chatManager = new ChatManager();
    
    // Update the new conversation handler
    $newConversationBtn.on('click', function() {
        chatManager.startNewChat('', '');
    });

    // Update history conversations handler
    $historyConversationsBtn.on('click', async function() {
        try {
            const chatHistory = await chatManager.loadChatHistory('test1');
            const $chatHistoryList = $('#chatHistoryList');
            $chatHistoryList.empty();
            
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
                $chatHistoryList.append(chatEntry);
            });
            
            const chatHistoryModal = new bootstrap.Modal('#chatHistoryModal');
            chatHistoryModal.show();
        } catch (error) {
            console.error('Error fetching chat history:', error);
        }
    });

    // Update chat history entry click handler
    $(document).on('click', '.chat-history-entry', function() {
        const chatId = $(this).data('chat-id');
        if (chatManager.loadConversation(chatId)) {
            $('#chatHistoryModal').modal('hide');
        }
    });

    // Update history list
    async function updateHistoryList() {
        try {
            const websites = await websiteManager.getWebsites();
            const $historyList = $('#history-list');
            $historyList.empty();
            
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
                $historyList.append(websiteEntry);
            });
        } catch (error) {
            console.error('Error updating history list:', error);
        }
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

    // Update website entry click handler
    $(document).on('click', '.website-entry', function() {
        const url = $(this).data('url');
        const websiteData = websiteManager.getWebsiteData(url);
        if (!websiteData) return;
        
        const $modal = $('#websiteDetailsModal');
        
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
        const modal = new bootstrap.Modal($modal);
        modal.show();
    });

    // Add event listener for modal hidden event
    $('#websiteDetailsModal').on('hidden.bs.modal', function () {
        // Ensure the button loses focus after modal is hidden
        $('.start-chat-btn').blur();
    });

    // Add separate click handler for start chat button
    $('.start-chat-btn').on('click', function() {
        // Small delay to ensure modal is fully closed before starting chat
        setTimeout(startNewChat, 100);
    });

    // StartNewChat function
    function startNewChat() {
        const companyInfo = $('.start-chat-btn').closest('.modal-content').find('.company-name');
        const companyName = companyInfo.find('span').text();
        const companyLogo = companyInfo.find('img').attr('src');
        chatManager.startNewChat(companyName, companyLogo);
        $('#chat-tab').tab('show');
    }

}); 