$(document).ready(() => {
    console.log("jQuery Document Ready fired");
    initializeFloatButton();
});

function initializeFloatButton() {
    console.log("Initializing float button...");

    try {
        // Create float button
        const $floatButton = $('<button>')
            .addClass('float-button')
            .appendTo('body');

        // Add logo image
        const $defaultLogo = $('<img>')
            .attr('src', chrome.runtime.getURL('../img/logo2.png'))
            .addClass('default-logo')
            .appendTo($floatButton);

        // Add favicon image (initially hidden)
        const $favicon = $('<img>')
            .addClass('favicon-logo')
            .hide()
            .appendTo($floatButton);

        // Get favicon from the current page
        const currentFavicon = $('link[rel="icon"]').attr('href') || 
                             $('link[rel="shortcut icon"]').attr('href') ||
                             window.location.origin + '/favicon.ico';
        
        if (currentFavicon) {
            $favicon.attr('src', currentFavicon);
        }

        // Add hover effects
        $floatButton
            .on('mouseenter', () => {
                $defaultLogo.hide();
                $favicon.show();
            })
            .on('mouseleave', () => {
                $favicon.hide();
                $defaultLogo.show();
            });

        // Create popup
        const $popup = $('<iframe>')
            .addClass('popup')
            .attr('src', chrome.runtime.getURL('floatButton/popup.html'))
            .hide()
            .appendTo('body');
        console.log("Popup iframe added to DOM");

        // Add click handler for the float button
        $floatButton.on('click', (event) => {
            event.stopPropagation();
            if ($popup.is(':hidden')) {
                $popup.show();
                $defaultLogo.hide();
                $favicon.show();
            } else {
                $popup.hide();
                $favicon.hide();
                $defaultLogo.show();
            }
        });

        // Close popup when clicking outside
        $(document).on('click', (event) => {
            if (!$(event.target).closest('.popup, .float-button').length) {
                $popup.hide();
                $favicon.hide();
                $defaultLogo.show();
            }
        });

        // Listen for minimize message from popup
        window.addEventListener('message', (event) => {
            if (event.data === 'minimize') {
                $popup.hide();
                $favicon.hide();
                $defaultLogo.show();
            }
        });

    } catch (error) {
        console.error("Error initializing float button:", error);
    }
}
