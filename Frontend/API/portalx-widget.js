(function() {
    class PortalXWidget {
        constructor() {
            this.config = {
                serverUrl: 'http://localhost:7777'
            };
            this.init();
        }

        init() {
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.initializeWidget());
            } else {
                this.initializeWidget();
            }
            this.setupWebsiteInfo();
        }

        setupWebsiteInfo() {
            const scriptTag = document.currentScript;
            const websiteUrl = scriptTag.getAttribute('data-website');
            const websiteInfo = this.getWebsiteInfoFromUrl(websiteUrl);
            // Make configuration available globally
            window.PortalXConfig = {
                websiteInfo,
                config: this.config
            };
        }

        getWebsiteInfoFromUrl(url) {
            const urlObj = new URL(url);
            const domainName = urlObj.hostname;
            return {
                url,
                title: domainName,
                domainName,
                hostName: domainName.replace('www.', '').split('.')[0],
                subdomain: this.getSubdomain(urlObj, domainName),
                hostLogo: `https://www.google.com/s2/favicons?domain=${domainName}`
            };
        }

        getSubdomain(urlObj, domainName) {
            return urlObj.pathname.split('/')[1] 
                ? `${domainName}/${urlObj.pathname.split('/')[1]}/`
                : `${domainName}/`;
        }

        loadResource(type, url) {
            return new Promise((resolve, reject) => {
                const element = this.createElement(type, url);
                element.onload = resolve;
                element.onerror = reject;
                this.appendElement(type, element);
            });
        }

        createElement(type, url) {
            if (type === 'css') {
                const link = document.createElement('link');
                link.rel = 'stylesheet';
                link.href = url;
                return link;
            } else if (type === 'js') {
                const script = document.createElement('script');
                script.src = url;
                return script;
            }
        }

        appendElement(type, element) {
            if (type === 'css') {
                document.head.appendChild(element);
            } else if (type === 'js') {
                document.body.appendChild(element);
            }
        }

        async initializeWidget() {
            await this.loadDependencies();
        }

        async loadDependencies() {
            const { serverUrl } = this.config;
            try {
                // Load CSS files in parallel
                await Promise.all([
                    this.loadResource('css', `${serverUrl}/Frontend/API/src/style/floatButton-widget.css`),
                    this.loadResource('css', `${serverUrl}/Frontend/API/src/style/popup-widget.css`)
                ]);

                // Load JS dependencies in parallel
                await Promise.all([
                    this.loadResource('js', 'https://code.jquery.com/jquery-3.7.1.min.js'),
                    this.loadResource('js', 'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js')
                ]);

                // Load and show up float button widget
                await this.loadResource('js', `${serverUrl}/Frontend/API/src/floatButton-widget.js`);
            } catch (error) {
                console.error('Error loading PortalX widget:', error);
            }
        }
    }

    // Initialize the widget
    new PortalXWidget();
})(); 