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
            .html('+')
            .appendTo('body');
        console.log("Float button added to DOM");

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
                $floatButton.html('×');
            } else {
                $popup.hide();
                $floatButton.html('+');
            }
        });

        // Close popup when clicking outside
        $(document).on('click', (event) => {
            if (!$(event.target).closest('.popup, .float-button').length) {
                $popup.hide();
                $floatButton.html('+');
            }
        });

        // Listen for minimize message from popup
        window.addEventListener('message', (event) => {
            if (event.data === 'minimize') {
                $popup.hide();
                $floatButton.html('+');
            }
        });

    } catch (error) {
        console.error("Error initializing float button:", error);
    }
}
