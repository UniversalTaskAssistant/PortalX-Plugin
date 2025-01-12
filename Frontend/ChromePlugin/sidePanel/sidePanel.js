import { ChatManager } from './chatManager.js';
import { WebsiteManager } from './websiteManager.js';
import { SERVER_CONFIG } from '../serverConfig.js';

// Add server URL constant at the top
let serverUrl = SERVER_CONFIG.URL;

$(document).ready(function() {
    // Initialize WebsiteManager with serverUrl
    const websiteManager = new WebsiteManager(serverUrl);
    // Initialize ChatManager with serverUrl
    const chatManager = new ChatManager(serverUrl);
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

    // Website Analysis
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
        const domainLimit = domainName + '/' + $('#subdomainPath').val()?.trim() || '';

        if (!websiteManager.validateCrawlParameters(domainName, hostName, domainLimit)) {
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

    // Chatting
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
                url: `${serverUrl}/query`,
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