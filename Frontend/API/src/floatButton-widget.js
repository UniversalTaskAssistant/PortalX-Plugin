$(document).ready(() => {
    initializeFloatButton();
});

function initializeFloatButton() {
    try {
        let isPopupOpen = false;
        const serverUrl = 'http://localhost:7777';

        // Create float button
        const $floatButton = $('<button>')
            .addClass('uta-float-button')
            .appendTo('body');

        // Add logo image
        const $defaultLogo = $('<img>')
            .attr('src', `${serverUrl}/Frontend/API/img/logo2.png`)
            .addClass('uta-default-logo')
            .appendTo($floatButton);

        // Add favicon image (initially hidden)
        const $favicon = $('<img>')
            .addClass('uta-favicon-logo')
            .hide()
            .appendTo($floatButton);

        // Get favicon from the current page
        const currentFavicon = $('link[rel="icon"]').attr('href') || 
                             $('link[rel="shortcut icon"]').attr('href') ||
                             `${serverUrl}/Frontend/API/img/logo2.png`;
        if (currentFavicon) {
            $favicon.attr('src', currentFavicon);
        }

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

        // Create popup
        const $popup = $('<iframe>')
            .addClass('uta-popup-iframe')
            .attr('src', `${serverUrl}/Frontend/API/src/popup-widget.html`)
            .hide()
            .appendTo('body');

        // Add click handler for the float button
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

        // Close popup when clicking outside
        $(document).on('click', (event) => {
            if (!$(event.target).closest('.uta-popup-iframe, .uta-float-button').length) {
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
        console.error("Error initializing UTAWeb float button:", error);
    }
}
