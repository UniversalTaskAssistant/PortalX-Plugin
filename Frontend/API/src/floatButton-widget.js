$(document).ready(() => {
    initializeFloatButton();
});

function initializeFloatButton() {
    try {
        let isPopupOpen = false;
        const websiteInfo = window.parent.PortalXConfig.websiteInfo;  // Get websiteInfo
        console.log('PortalX: FloatButton loaded', websiteInfo);    // Debug log


        // ****** Float Button ******
        // Create float button
        const $floatButton = $('<button>')
            .addClass('portalx-float-button')
            .appendTo('body');

        // Float button hover effect
        $floatButton
        .on('mouseenter', () => {
            if (!isPopupOpen) {
                $defaultLogo.addClass('slide-out');
                $favicon.show().addClass('slide-in');
            }
        })
        .on('mouseleave', () => {
            if (!isPopupOpen) {
                $defaultLogo.removeClass('slide-out');
                $favicon.removeClass('slide-in').hide();
            }
        });

        // Float button click effect
        $floatButton.on('click', (event) => {
            event.stopPropagation();
            if ($popup.is(':hidden')) {
                isPopupOpen = true;
                $popup.show();
                setTimeout(() => $popup.addClass('show'), 0);
                $defaultLogo.addClass('slide-out');
                $favicon.show().addClass('slide-in');
            } else {
                isPopupOpen = false;
                $popup.removeClass('show');
                setTimeout(() => $popup.hide(), 300);
                $defaultLogo.removeClass('slide-out');
                $favicon.removeClass('slide-in').hide();
            }
        });


        // ****** Logo and Favicon ******
        // Add PortalX logo image
        const $defaultLogo = $('<img>')
            .attr('src', `${window.parent.PortalXConfig.config.serverUrl}/Frontend/API/img/logo2.png`)
            .addClass('portalx-default-logo')
            .appendTo($floatButton);

        // Add client logo image 
        const $favicon = $('<img>')
            .addClass('portalx-favicon-logo')
            .hide()
            .appendTo($floatButton)
            .attr('src', window.parent.PortalXConfig.websiteInfo.hostLogo);


        // ****** Popup Page ******
        // Create popup
        const $popup = $('<iframe>')
            .addClass('portalx-popup-iframe')
            .attr('src', `${window.parent.PortalXConfig.config.serverUrl}/Frontend/API/src/popup-widget.html`)
            .hide()
            .appendTo('body');

        // Send both websiteInfo and serverUrl
        $popup.on('load', () => {
            console.log('PortalX: Iframe loaded');
            $popup[0].contentWindow.postMessage({
                type: 'websiteInfo',
                data: {
                    websiteInfo: websiteInfo,
                    serverUrl: window.parent.PortalXConfig.config.serverUrl
                }
            }, '*');
        });

        // Close popup when clicking outside
        $(document).on('click', (event) => {
            if (!$(event.target).closest('.portalx-popup-iframe, .portalx-float-button').length) {
                isPopupOpen = false;
                $popup.removeClass('show');
                setTimeout(() => $popup.hide(), 300);
                $defaultLogo.removeClass('slide-out');
                $favicon.removeClass('slide-in').hide();
            }
        });

        // Listen for minimize message from popup
        window.addEventListener('message', (event) => {
            if (event.data === 'minimize') {
                isPopupOpen = false;
                $popup.removeClass('show');
                setTimeout(() => $popup.hide(), 300);
                $defaultLogo.removeClass('slide-out');
                $favicon.removeClass('slide-in').hide();
            }
        });

    } catch (error) {
        console.error("Error initializing PortalX float button:", error);
    }
}
