import { ChatManager } from './modules/chatManager.js';
import { WebsiteManager } from './modules/websiteManager.js';

$(document).ready(function() {
    // Initialize WebsiteManager
    const websiteManager = new WebsiteManager();
    // Initialize ChatManager
    const chatManager = new ChatManager();
    // Initialize tooltips
    initTooltips();

    function initTooltips() {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => {
            return new bootstrap.Tooltip(tooltipTriggerEl, {
                trigger: 'hover'
            });
        });
        // Hide tooltip when clicking the button
        document.getElementById('refreshWebsitesBtn').addEventListener('click', function() {
            const tooltip = bootstrap.Tooltip.getInstance(this);
            if (tooltip) {
                tooltip.hide();
            }
        });
    }

    // Add handler for the start crawl button
    $('#startCrawlBtn').on('click', async function() {
        if (!websiteManager.validateCrawlParameters()) {
            return;
        }
        
        try {
            $('#crawlParametersModal').modal('hide');
            $('#startCrawlBtn').prop('disabled', true)
                .html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Crawling...');
                
            const result = await websiteManager.startCrawl(domainName, hostName, domainLimit);
            $('.message-container').remove();
            $('#welcome-message').hide();
            chatManager.addMessage(result.message);
        } catch (error) {
            chatManager.addMessage(`Error during crawling: ${error.message}`);
        } finally {
            $('#startCrawlBtn').prop('disabled', false)
                       .html('<i class="bi bi-spider me-2"></i>Analyze');
        }
    });

    // Add the query button click handler
    $('#queryButton').on('click', async function() {
        const query = chatManager.getQueryInput();
        if (!query) {
            chatManager.addMessage('Please enter a question', false);
            return;
        }
        try {
            chatManager.setQueryButtonLoading(true);
            chatManager.addMessage(query, true);
            // Add thinking message
            chatManager.addThinkingMessage();
            
            const response = await $.ajax({
                url: 'http://localhost:7777/query',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    user_id: 'test1',
                    conversation_id: chatManager.conversationId,
                    query: query,
                    web_url: chatManager.currentChatWebsite.domainUrl,
                    host_name: chatManager.currentChatWebsite.name,
                    host_logo: chatManager.currentChatWebsite.logo
                })
            });
            // Remove thinking message before showing the response
            chatManager.removeThinkingMessage();
            chatManager.addMessage(response.answer);
            chatManager.clearQueryInput();
        } catch (error) {
            chatManager.removeThinkingMessage();
            chatManager.addMessage(`Error getting response: ${error.message}`);
        } finally {
            chatManager.setQueryButtonLoading(false);
        }
    });
}); 