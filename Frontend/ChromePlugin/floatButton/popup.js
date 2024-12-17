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

    // Handle sending messages
    function sendMessage() {
        const query = $queryInput.val().trim();
        if (!query) return;

        // Add user message
        addMessage(query, 'user');
        
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
        const $message = $('<div>')
            .addClass(`message ${type}`)
            .text(text);
        
        $messagesContainer.append($message);
        $messagesContainer.scrollTop($messagesContainer[0].scrollHeight);
    }

    // Event handlers
    $sendButton.on('click', sendMessage);

    $queryInput.on('keypress', (e) => {
        if (e.which === 13 && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    $newChatBtn.on('click', () => {
        $messagesContainer.empty();
        // Re-add welcome message
        addWelcomeMessage();
    });

    $minimizeBtn.on('click', () => {
        // Send message to parent window to minimize
        window.parent.postMessage('minimize', '*');
    });

    function addWelcomeMessage() {
        const welcomeHtml = `
            <div class="welcome-message">
                <div class="welcome-icon">
                    <img src="../img/logo2.png" alt="Logo" class="welcome-logo">
                </div>
                <h5 class="welcome-title">Ask anything about this website</h5>
                <div class="features-grid">
                    <div class="feature-item">
                        <i class="bi bi-search"></i>
                        <span>Smart Search</span>
                    </div>
                    <div class="feature-item">
                        <i class="bi bi-chat-dots"></i>
                        <span>Interactive Chat</span>
                    </div>
                    <div class="feature-item">
                        <i class="bi bi-lightning"></i>
                        <span>Quick Answers</span>
                    </div>
                </div>
            </div>
        `;
        $messagesContainer.html(welcomeHtml);
    }
} 