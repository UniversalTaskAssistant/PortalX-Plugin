$(document).ready(() => {
    console.log("Popup Document Ready fired");
    initializePopup();
});

function initializePopup() {
    const $messagesContainer = $('#messagesContainer');
    const $queryInput = $('#queryInput');
    const $sendButton = $('#sendButton');
    const $newChatBtn = $('#newChatBtn');
    const $minimizeBtn = $('.minimize-btn');
    const $welcomeMessage = $('.welcome-message');


    // Event handlers
    $sendButton.on('click', sendMessage);

    $queryInput.on('keypress', (e) => {
        if (e.which === 13 && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    $newChatBtn.on('click', () => {
        $('.message-container').remove();
        $welcomeMessage.fadeIn(200);
    });

    $minimizeBtn.on('click', () => {
        // Send message to parent window to minimize
        window.parent.postMessage('minimize', '*');
    });

    // Handle sending messages
    function sendMessage() {
        const query = $queryInput.val().trim();
        if (!query) return;

        // Remove welcome message and add user message after fade completes
        $('.welcome-message').fadeOut(100, function() {
            // Add user message
            addMessage(query, 'user');
        });

        // Clear input
        $queryInput.val('');

        // TODO: Send query to backend and handle response
        // For now, just add a mock response
        setTimeout(() => {
            addMessage('This is a mock response. The actual integration with the backend will be implemented later.', 'assistant');
        }, 1000);
    }

    // Add a message to the chat
    function addMessage(text, type) {
        const $messageContainer = $('<div>', {
            class: `message-container ${type === 'assistant' ? 'assistant-container' : ''}`
        });

        if (type === 'assistant') {
            // Add assistant icon
            const $iconDiv = $('<div>', {
                class: 'assistant-icon'
            }).append(
                $('<img>', {
                    src: '../img/logo2.png',
                    alt: 'Assistant'
                })
            );
            $messageContainer.append($iconDiv);
        }

        const $message = $('<div>')
            .addClass(`message ${type}`)
            .html(text);
        
        $messageContainer.append($message);
        $messagesContainer.append($messageContainer);
        $messagesContainer.scrollTop($messagesContainer[0].scrollHeight);
    }
} 