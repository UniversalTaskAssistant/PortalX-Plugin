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
        const companyName = $('#hostName').val()?.trim() || '';
        const domainLimit = $('#subdomainLimit').val()?.trim() || '';
        if (!companyName) {
            alert('Please enter a host name (company name)');
            return;
        }
        try {
            $('#crawlParametersModal').modal('hide');
            $('#startCrawlBtn').prop('disabled', true)
                .html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Crawling...');
                
            const result = await websiteManager.startCrawl(companyName, domainLimit);
            chatManager.addMessage(result.message);
        } catch (error) {
            chatManager.addMessage(`Error during crawling: ${error.message}`);
        } finally {
            $('#startCrawlBtn').prop('disabled', false)
                       .html('<i class="bi bi-spider me-2"></i>Analyze');
        }
    });
}); 