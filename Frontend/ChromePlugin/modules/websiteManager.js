export class WebsiteManager {
    constructor() {
        this.currentWebsiteInfo = {
            url: '',
            title: '',
            domainName: '',
            hostName: '',
            subdomain: ''
        };
        this.websitesData = new Map();
        
        this.updateCurrentWebsiteInfo();
        this.initializeEventListeners();
        this.initializeWebsiteSearch();
        this.initializeCrawlButton();
        this.initializeWebsiteEntryHandler();
    }

    // ****************************
    // ****** INITIALIZATION ******
    // Initialize event listeners
    initializeEventListeners() {
        // Listen for tab changes
        chrome.tabs.onActivated.addListener(() => this.updateCurrentWebsiteInfo());
        // Listen for tab updates
        chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
            chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
                if (tabs[0] && tabs[0].id === tabId) {
                    this.updateCurrentWebsiteInfo();
                }
            });
        });

        // Add history tab listener
        $(document).on('click', '.history-tab', () => this.updateWebsitesHistoryList());

        // Add change website button listener
        $('#changeWebsiteBtn').on('click', () => {
            $('#history-tab').tab('show');
            this.updateWebsitesHistoryList();
        });
    }
    
    // Initialize the website search
    initializeWebsiteSearch() {
        $('#websiteSearch').on('input', function() {
            const searchTerm = $(this).val().toLowerCase();
            $('.website-entry').each(function() {
                const text = $(this).text().toLowerCase();
                $(this).toggle(text.includes(searchTerm));
            });
        });
    }

    // Initialize the crawl settings button
    initializeCrawlButton() {
        const self = this;  // Store reference to class instance
        $('#crawlButton').on('click', function() {
            const currentInfo = self.getCurrentWebsiteInfo();
            $('#websiteDomain').val(currentInfo.domainName);
            $('#hostName').val(currentInfo.hostName);
            $('#subdomainLimit').val(currentInfo.subdomain);
            new bootstrap.Modal('#crawlParametersModal').show();
        });
    }

    // Website entry click handler to show the website details modal
    initializeWebsiteEntryHandler() {
        $(document).on('click', '.website-entry', (event) => {
            const url = $(event.currentTarget).data('url');
            const websiteData = this.getWebsiteData(url);
            if (!websiteData) return;
            const $modal = $('#websiteDetailsModal');
            
            // Update modal content
            const faviconUrl = this.getFaviconUrl(websiteData.start_urls[0]);
            $modal.find('.company-name').html(`
                <img src="${faviconUrl}" alt="">
                <span>${websiteData.company_name}</span>
            `);
            
            $modal.find('.start-url')
                .text(websiteData.start_urls[0])
                .attr('href', websiteData.start_urls[0]);
            $modal.find('.pages-count').text(websiteData.visited_urls.length);
            $modal.find('.domains-count').text(Object.keys(websiteData.domain_urls).length);
            
            this.updateModalDomainsList($modal, websiteData);
            this.updateModalFailedUrlsList($modal, websiteData);
            
            // Show modal using Bootstrap
            const modal = new bootstrap.Modal($modal);
            modal.show();
        });
    }

    // Update the current website info
    updateCurrentWebsiteInfo() {
        chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
            if (tabs[0]) {
                const currentUrl = tabs[0].url;
                const urlObj = new URL(currentUrl);
                // Extract domain, host, and subdomain
                const domainName = urlObj.hostname;
                const hostName = domainName.replace('www.', '').split('.')[0];
                const subdomain = urlObj.pathname.split('/')[1] ?
                    `${domainName}/${urlObj.pathname.split('/')[1]}/` :
                    domainName + '/';
                this.currentWebsiteInfo = {
                    url: currentUrl,
                    title: tabs[0].title || urlObj.hostname,
                    domainName: domainName,
                    hostName: hostName,
                    subdomain: subdomain
                };
                // Update the html current website tab
                this.updateCurrentWebsiteBar();
                console.log('Current URL updated:', currentUrl);
            }
        });
    }
    
    // **********************
    // ****** GET DATA ******
    // Get the website data
    getWebsiteData(url) {
        return this.websitesData.get(url);
    }

    // Get the current website info
    getCurrentWebsiteInfo() {
        return this.currentWebsiteInfo;
    }

    // Get the favicon URL
    getFaviconUrl(url) {
        try {
            const domain = new URL(url).hostname;
            return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
        } catch (e) {
            return null;
        }
    }

    // *************************
    // ****** START CRAWL ******
    // Start crawling the current website
    async startCrawl(companyName, domainLimit) {
        try {
            const response = await $.ajax({
                url: 'http://localhost:7777/crawl',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    web_url: this.currentWebsiteInfo.url,
                    company_name: companyName,
                    domain_limit: domainLimit
                })
            });
            return { 
                success: true, 
                message: 'Check website analysis in the <a href="#" class="history-tab">Websites section</a>'
            };
        } catch (error) {
            return { success: false, message: `Error during crawling: ${error.message}` };
        }
    }

    // Load all crawled websites data from the server
    async loadAllWebsitesHistory() {
        try {
            const websites = await $.ajax({
                url: 'http://localhost:7777/get_websites',
                method: 'GET'
            });
            // Clear and update the websites data
            this.websitesData.clear();
            websites.forEach(site => {
                this.websitesData.set(site.start_urls[0], site);
            });

            return websites;
        } catch (error) {
            console.error('Error fetching website history:', error);
            throw error;
        }
    }

    // *******************************
    // ******* UPDATE SECTIONS *******
    // Update the current website tab
    updateCurrentWebsiteBar() {
        const faviconUrl = this.getFaviconUrl(this.currentWebsiteInfo.url);
        const $currentWebsite = $('.current-website');
        $currentWebsite.empty();
        $currentWebsite.append(`
            <div class="d-flex align-items-center">
                <img src="${faviconUrl}" alt="" class="website-favicon me-2">
                <div class="website-info-text">
                    <div class="website-title text-truncate">${this.currentWebsiteInfo.title}</div>
                </div>
            </div>
        `);
        console.log(this.currentWebsiteInfo);
        $('.current-website-domain')
            .text(this.currentWebsiteInfo.domainName)
            .attr('href', `https://${this.currentWebsiteInfo.domainName}`);
    }

    // Update the history list
    async updateWebsitesHistoryList() {
        try {
            const websites = await this.loadAllWebsitesHistory();
            let historyList = $('#history-list');
            historyList.empty();
            websites.forEach(site => {
                const faviconUrl = this.getFaviconUrl(site.start_urls[0]);
                const websiteEntry = `
                    <div class="website-entry" data-url="${site.start_urls[0]}">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <div class="d-flex align-items-center">
                                <img src="${faviconUrl}" alt="" class="website-favicon me-2">
                                <h6 class="mb-0">${site.company_name}</h6>
                            </div>
                            <small class="text-muted">${this.formatTimestamp(site.crawl_time)}</small>
                        </div>
                        <span class="url-text mb-3">${site.start_urls[0]}</span>
                        <div class="d-flex align-items-center">
                            <span class="badge ${site.crawl_finished ? 'bg-success' : 'bg-warning'} me-2">
                                ${site.crawl_finished ? 'Analyzed' : 'In Progress'}
                            </span>
                            <span class="stats-text">${site.visited_urls.length} pages analyzed</span>
                        </div>
                    </div>
                `;
                historyList.append(websiteEntry);
                $('#history-tab').tab('show');
            });
        } catch (error) {
            console.error('Error updating history list:', error);
        }
    }

    // Format the timestamp
    formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diffInMinutes = Math.floor((now - date) / (1000 * 60));
        
        if (diffInMinutes < 1) return 'just now';
        if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
        if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes/60)}h ago`;
        return `${Math.floor(diffInMinutes/1440)}d ago`;
    }

    // Update the domains list in the modal
    updateModalDomainsList($modal, websiteData) {
        const $domainsList = $modal.find('.domains-list').empty();
        Object.entries(websiteData.domain_urls).forEach(([domain, count]) => {
            $domainsList.append(`
                <div class="domain-item d-flex justify-content-between align-items-center mb-1">
                    <span class="domain-name">${domain}</span>
                    <span class="domain-count badge">${count} pages</span>
                </div>
            `);
        });
    }

    // Update the failed URLs list in the modal
    updateModalFailedUrlsList($modal, websiteData) {
        const $failedList = $modal.find('.failed-urls-list').empty();
        if (websiteData.failed_urls?.length > 0) {
            const initialDisplay = 3;
            const totalUrls = websiteData.failed_urls.length;
            
            websiteData.failed_urls.slice(0, initialDisplay).forEach(([url, reason]) => {
                $failedList.append(`
                    <div class="failed-url-item mb-1">
                        <div class="text-truncate">${url}</div>
                        <small class="text-danger">${reason}</small>
                    </div>
                `);
            });
            
            if (totalUrls > initialDisplay) {
                this.addShowMoreButton($failedList, websiteData.failed_urls.slice(initialDisplay));
            }
        } else {
            $failedList.append('<p class="text-muted mb-0">No failed URLs</p>');
        }
    }

    // Add the show more button to the failed URLs list
    addShowMoreButton($failedList, remainingUrls) {
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
}
