(function() {
    // Configuration
    const config = {
        serverUrl: 'http://localhost:7777',
        assetsUrl: 'http://localhost:7777/ChromePlugin'
    };

    // Helper function to get website info from URL
    function getWebsiteInfoFromUrl(url) {
        const urlObj = new URL(url);
        const title = urlObj.hostname;
        const domainName = urlObj.hostname;
        const hostName = domainName.replace('www.', '').split('.')[0];
        const subdomain = urlObj.pathname.split('/')[1] ?
            `${domainName}/${urlObj.pathname.split('/')[1]}/` :
            domainName + '/';
        const favicon = `https://www.google.com/s2/favicons?domain=${domainName}`;
            
        return {
            url: url, 
            title: title, 
            domainName: domainName, 
            hostName: hostName, 
            subdomain: subdomain,
            hostLogo: favicon
        };
    }

    // Get website info from script tag
    const scriptTag = document.currentScript;
    const websiteUrl = scriptTag.getAttribute('data-website');
    const websiteInfo = getWebsiteInfoFromUrl(websiteUrl);

    // Make websiteInfo available globally
    window.UTAWebConfig = {
        websiteInfo: websiteInfo
    };

    function loadResource(type, url) {
        return new Promise((resolve, reject) => {
            if (type === 'css') {
                const link = document.createElement('link');
                link.rel = 'stylesheet';
                link.href = url;
                link.onload = resolve;
                link.onerror = reject;
                document.head.appendChild(link);
            } else if (type === 'js') {
                const script = document.createElement('script');
                script.src = url;
                script.onload = resolve;
                script.onerror = reject;
                document.body.appendChild(script);
            }
        });
    }

    // Load resources in sequence
    async function initializeWidget() {
        try {
            // Load CSS files from ChromePlugin directory
            await Promise.all([
                loadResource('css', `${config.assetsUrl}/floatButton/floatButton.css`),
                loadResource('css', `${config.assetsUrl}/floatButton/popup.css`)
            ]);

            // Load jQuery and Bootstrap
            await Promise.all([
                loadResource('js', 'https://code.jquery.com/jquery-3.7.1.min.js'),
                loadResource('js', 'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js')
            ]);

            // Load widget scripts from API/src directory
            await loadResource('js', `${config.serverUrl}/Frontend/API/src/floatButton-widget.js`);
            await loadResource('js', `${config.serverUrl}/Frontend/API/src/popup-widget.js`);
        } catch (error) {
            console.error('Error loading UTAWeb widget:', error);
        }
    }

    // Initialize widget when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeWidget);
    } else {
        initializeWidget();
    }
})(); 