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
        this.updateWebsitesHistoryList(false);
        this.initializeEventListeners();
        this.initializeWebsiteSearch();
        this.initializeAnalyzeSettingButton();
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

        // Add refresh button listener
        $('#refreshWebsitesBtn').on('click', () => this.updateWebsitesHistoryList());

        // Add change website button listener
        $('#changeWebsiteBtn').on('click', () => {
            $('#history-tab').tab('show');
            this.updateWebsitesHistoryList();
        });

        // Click on the selected website bar to show the website details modal
        $(document).on('click', '.selected-website', (e) => {
            this.updateWebInfoModal(e);
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
    initializeAnalyzeSettingButton() {
        const self = this;  // Store reference to class instance
        
        // Add handler for "Entire Site" button
        $('#entireSiteBtn').on('click', function() {
            $('#subdomainPath').val(''); // Clear the path part
        });

        // Add handler for website domain changes
        $('#websiteDomain').on('input', function() {
            const domainName = $(this).val();
            $('#domainPart').text(domainName + '/');
        });

        $('.analyze-setting-btn').on('click', function(e) {
            // Don't trigger if this is part of a form submission
            if ($(this).closest('form').length > 0) {
                return;
            }
            
            $('#crawlParametersModal .alert-existing-website').remove();
            const currentInfo = self.getCurrentWebsiteInfo();
            $('#websiteDomain').val(currentInfo.domainName);
            $('#hostName').val(currentInfo.hostName);
            $('#domainPart').text(currentInfo.domainName + '/');
            $('#subdomainPath').val(currentInfo.subdomain.split('/')[1] + '/'); 
            new bootstrap.Modal('#crawlParametersModal').show();
        });

        // Handle the URL input form separately
        $('.enter-website').off('submit').on('submit', function(e) {
            e.preventDefault();
            const inputUrl = $('#otherWebsiteInput').val();
            // URL validation regex pattern
            const urlPattern = /^(https?:\/\/)?([\w-]+\.)+[\w-]+(\/[\w-./?%&=]*)?$/;
            try {
                // First check if it matches basic URL pattern
                if (!urlPattern.test(inputUrl)) {
                    throw new Error('Invalid URL format');
                }
                
                // Try to add https:// if not present
                const urlToTest = inputUrl.startsWith('http') ? inputUrl : `https://${inputUrl}`;
                // Try to construct URL object (this will catch malformed URLs)
                new URL(urlToTest);
                const websiteInfo = self.getWebsiteInfoFromUrl(urlToTest);
                
                // Clear any previous error messages
                $('#urlError').remove();
                // Only show modal and set values if all validation passes
                $('#websiteDomain').val(websiteInfo.domainName);
                $('#hostName').val(websiteInfo.hostName);
                $('#domainPart').text(websiteInfo.domainName + '/');
                $('#subdomainPath').val(websiteInfo.subdomain.split('/')[1] + '/'); 
                new bootstrap.Modal('#crawlParametersModal').show();
            } catch (error) {
                // Remove any existing error message
                $('#urlError').remove();
                
                // Add error message below the input
                const errorMessage = `
                    <div id="urlError" class="alert alert-danger mt-2 mb-0 d-flex justify-content-between align-items-center" style="display: none;">
                        <small>Invalid URL format. Please enter a valid URL like "example.com" or "https://www.example.com"</small>
                        <button type="button" class="btn-close btn-close-sm" aria-label="Close" style="transform: scale(0.7); padding: 2px;"></button>
                    </div>`;
                $('.other-website').append(errorMessage);
                $('#urlError').fadeIn(300); // Smooth fade in animation over 300ms

                // Add click handler for close button
                $('#urlError .btn-close').on('click', function() {
                    $('#urlError').fadeOut(200, function() {
                        $(this).remove();
                    });
                });
            }
        });
    }

    // Website entry click handler to show the website details modal
    initializeWebsiteEntryHandler() {
        $(document).on('click', '.website-entry', (event) => {
            this.updateWebInfoModal(event)
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
    async startCrawl(domainName, hostName, domainLimit) {
        try {
            const response = await $.ajax({
                url: 'http://localhost:7777/crawl',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    domainName: domainName,
                    hostName: hostName,
                    domainLimit: domainLimit
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
    // Update the current website info
    updateCurrentWebsiteInfo() {
        chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
            if (tabs[0]) {
                const currentUrl = tabs[0].url;
                this.currentWebsiteInfo = this.getWebsiteInfoFromUrl(currentUrl);
                this.currentWebsiteInfo.title = tabs[0].title
                // Update the html current website tab
                this.updateCurrentWebsiteBar();
            }
        });
    }

    // Get the website info from the url
    getWebsiteInfoFromUrl(url) {
        const urlObj = new URL(url);
        const title = urlObj.hostname;
        const domainName = urlObj.hostname;
        const hostName = domainName.replace('www.', '').split('.')[0];
        const subdomain = urlObj.pathname.split('/')[1] ?
            `${domainName}/${urlObj.pathname.split('/')[1]}/` :
            domainName + '/';
        return {url: url, title: title, domainName: domainName, hostName: hostName, subdomain: subdomain};
    }

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
        $('.current-website-domain')
            .text(this.currentWebsiteInfo.domainName)
            .attr('href', `https://${this.currentWebsiteInfo.domainName}`);
    }

    // Update the history list
    async updateWebsitesHistoryList(switchTab = true) {
        try {
            const websites = await this.loadAllWebsitesHistory();
            let historyList = $('#history-list');
            $('.website-entry').remove();
            if (websites.length > 0) {
                $('.no-websites-message').hide();
                websites.forEach(site => {
                    const faviconUrl = this.getFaviconUrl(site.start_urls[0]);
                    const websiteEntry = `
                        <div class="website-entry card-box-shadow" data-url="${site.start_urls[0]}">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <div class="d-flex align-items-center">
                                    <img src="${faviconUrl}" alt="" class="website-favicon me-2">
                                    <h6 class="mb-0 host-name">${site.company_name}</h6>
                                </div>
                                <small class="text-muted">${this.formatTimestamp(site.crawl_time)}</small>
                            </div>
                            <span class="url-text mb-3 website-domain">${site.start_urls[0]}</span>
                            <div class="d-flex align-items-center">
                                <span class="badge ${site.crawl_finished ? 'website-status-bg-success' : 'website-status-bg-warning'} me-2">
                                    ${site.crawl_finished ? 'Analyzed' : 'In Progress'}
                                </span>
                                <span class="stats-text">${site.visited_urls.length} pages analyzed</span>
                            </div>
                        </div>
                    `;
                    historyList.append(websiteEntry);
                });
            } else {
                $('.no-websites-message').show();
            }
            if (switchTab) {
                $('#history-tab').tab('show');
            }
        } catch (error) {
            console.error('Error updating history list:', error);
        }
    }

    // *******************
    // ****** Modal ******
    // Format the timestamp
    updateWebInfoModal(event) {
        const url = $(event.currentTarget).attr('data-url');
        const websiteData = this.getWebsiteData(url);

        if (!websiteData) return;
        const $modal = $('#websiteDetailsModal');
        
        // Update modal content
        const faviconUrl = this.getFaviconUrl(websiteData.start_urls[0]);
        $modal.find('.company-name').html(`
            <img src="${faviconUrl}" alt="">
            <span>${websiteData.company_name}</span>
        `);
        
        $modal.find('.domain-url')
            .text(websiteData.start_urls[0])
            .attr('href', websiteData.start_urls[0]);
        $modal.find('.pages-count').text(websiteData.visited_urls.length);
        $modal.find('.domains-count').text(Object.keys(websiteData.domain_urls).length);
        $modal.find('.failed-urls-count').text(websiteData.failed_urls?.length || 0);
        $modal.find('.subdomain-limit').text(websiteData.domain_limit || 'None');
        
        this.updateModalDomainsList($modal, websiteData);
        this.updateModalFailedUrlsList($modal, websiteData);
        
        // Show modal using Bootstrap
        const modal = new bootstrap.Modal($modal);
        modal.show();
    }

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

    validateCrawlParameters(domainName, hostName, domainLimit) {
        if (!hostName) {
            alert('Please enter a host name (company name)');
            return false;
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
            return false;
        }
        return true;
    }
}
