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
        
        this.initializeEventListeners();
        this.updateCurrentTab();
    }

    // Initialization
    initializeEventListeners() {
        // Listen for tab changes
        chrome.tabs.onActivated.addListener(() => this.updateCurrentTab());

        // Listen for tab updates
        chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
            chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
                if (tabs[0] && tabs[0].id === tabId) {
                    this.updateCurrentTab();
                }
            });
        });
    }
    
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

    // Get all websites data from the server
    async getWebsites() {
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
            return { success: true, message: 'Crawling completed successfully!' };
        } catch (error) {
            return { success: false, message: `Error during crawling: ${error.message}` };
        }
    }

    // Update the tab for current website
    updateCurrentTab() {
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
                
                this.updateAnalysisSection();
                console.log('Current URL updated:', currentUrl);
            }
        });
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

    // Update the analysis section
    updateAnalysisSection() {
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
    }

}
