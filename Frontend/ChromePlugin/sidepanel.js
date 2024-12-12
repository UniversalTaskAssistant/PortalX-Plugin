import { ChatManager } from './modules/chatManager.js';
import { WebsiteManager } from './modules/websiteManager.js';

$(document).ready(function() {
    // Initialize WebsiteManager
    const websiteManager = new WebsiteManager();
    // Initialize ChatManager
    const chatManager = new ChatManager();
    // Initialize tooltips
    function initializeTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    initializeTooltips();

    // Add handler for the start crawl button
    $('#startCrawlBtn').on('click', async function() {
        const addHttps = (url) => {
            if (!url) return '';
            if (!url.startsWith('http://') && !url.startsWith('https://')) {
                return `https://${url}`;
            }
            return url;
        };
        const domainName = addHttps($('#websiteDomain').val()?.trim() || '');
        const hostName = $('#hostName').val()?.trim() || '';
        const domainLimit = addHttps($('#subdomainLimit').val()?.trim() || '');
        
        if (!hostName) {
            alert('Please enter a host name (company name)');
            return;
        }

        // Check if website already exists in history
        const existingEntry = $('.website-entry').filter(function() {
            const entryDomain = $(this).find('.website-domain').text().replace(/\/$/, '');
            const entryHost = $(this).find('.host-name').text();
            const domainToCompare = domainName.replace(/\/$/, '');
            return entryDomain === domainToCompare && entryHost === hostName;
        });
        // Show notification using Bootstrap modal or alert
        if (existingEntry.length > 0) {
            if ($(".alert-existing-website").length === 0) {
                const notification = `
                    <div class="mb-4 alert alert-warning alert-dismissible fade show alert-existing-website" role="alert" style="display: none;">
                        This website has already been analyzed. Please check the websites list.
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>`;
                $('#crawlParametersModal .modal-body').prepend(notification);
                $('.alert-existing-website').fadeIn(300);
            }
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
                    web_url: chatManager.currentChatWebsite.startUrl
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