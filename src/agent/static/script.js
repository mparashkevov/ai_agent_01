document.addEventListener('DOMContentLoaded', () => {
    const state = {
        sessionId: null,
        isGenerating: false,
        socket: null
    };

    const elements = {
        chatHistory: document.getElementById('chat_history'),
        promptInput: document.getElementById('prompt'),
        sendBtn: document.getElementById('send'),
        sessionIdDisplay: document.getElementById('session_id'),
        newSessionBtn: document.getElementById('new_session'),
        clearSessionBtn: document.getElementById('clear_session')
    };

    // --- UI Helpers ---

    function scrollToBottom() {
        // Only scroll if we were already near bottom or it's a new message
        const area = document.querySelector('.chat-area');
        area.scrollTop = area.scrollHeight;
    }

    function updateSessionUI(id) {
        state.sessionId = id;
        elements.sessionIdDisplay.textContent = id || '(new)';
        if (!id) {
            elements.chatHistory.innerHTML = `
                <div class="msg bot">
                    <div class="msg-content">Hello! I'm your AI Agent. How can I help you today?</div>
                </div>
            `;
        }
    }

    function createMessageElement(role, text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `msg ${role}`;

        // Simple markdown-ish parsing for code blocks could go here or use a library
        // For now, we will handle newlines
        const contentDiv = document.createElement('div');
        contentDiv.className = 'msg-content';
        contentDiv.innerHTML = text.replace(/\n/g, '<br/>'); // simplistic

        msgDiv.appendChild(contentDiv);
        return msgDiv;
    }

    function appendMessage(role, text) {
        const msg = createMessageElement(role, text);
        elements.chatHistory.appendChild(msg);
        scrollToBottom();
        return msg.querySelector('.msg-content'); // Return content div for streaming updates
    }

    // --- Actions ---

    async function startNewSession() {
        if (state.socket) state.socket.close();
        updateSessionUI(null);
    }

    async function clearSession() {
        if (!state.sessionId) return;
        try {
            await fetch(`/sessions/${state.sessionId}/clear`, { method: 'POST' });
            updateSessionUI(null);
        } catch (e) {
            console.error('Failed to clear session', e);
            alert('Error clearing session');
        }
    }

    async function sendMessage() {
        const text = elements.promptInput.value.trim();
        if (!text || state.isGenerating) return;

        state.isGenerating = true;
        elements.promptInput.value = '';
        elements.sendBtn.disabled = true;

        // Adjust textarea height reset
        elements.promptInput.style.height = 'auto';

        appendMessage('user', text);
        const botContentDiv = appendMessage('bot', '...');

        try {
            const proto = (location.protocol === 'https:') ? 'wss:' : 'ws:';
            const wsUrl = `${proto}//${location.host}/ws/chat`;
            const ws = new WebSocket(wsUrl);
            state.socket = ws;

            let currentResponse = '';
            let placeholderRemoved = false;

            ws.onopen = () => {
                const payload = {
                    prompt: text,
                    session_id: state.sessionId
                };
                ws.send(JSON.stringify(payload));
            };

            ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);

                if (msg.type === 'chunk') {
                    if (!placeholderRemoved) {
                        botContentDiv.innerHTML = ''; // Remove '...'
                        placeholderRemoved = true;
                    }
                    currentResponse += msg.data;
                    // Simple streaming update
                    botContentDiv.innerText = currentResponse; // Using innerText to be safe for now, or use a markdown parser
                    scrollToBottom();
                } else if (msg.type === 'done') {
                    state.sessionId = msg.session_id;
                    elements.sessionIdDisplay.textContent = msg.session_id;
                    if (!placeholderRemoved) {
                        botContentDiv.innerHTML = msg.response || '(empty)';
                    }
                    ws.close();
                } else if (msg.type === 'error') {
                    botContentDiv.innerHTML += `<br/><i>Error: ${msg.error}</i>`;
                    ws.close();
                }
            };

            ws.onerror = () => {
                botContentDiv.innerHTML += '<br/><i>[Connection Error]</i>';
                state.isGenerating = false;
                elements.sendBtn.disabled = false;
            };

            ws.onclose = () => {
                state.isGenerating = false;
                elements.sendBtn.disabled = false;
            };

        } catch (e) {
            botContentDiv.innerHTML = `Error: ${e.message}`;
            state.isGenerating = false;
            elements.sendBtn.disabled = false;
        }
    }

    // --- Event Listeners ---

    elements.sendBtn.addEventListener('click', sendMessage);
    elements.newSessionBtn.addEventListener('click', startNewSession);
    elements.clearSessionBtn.addEventListener('click', clearSession);

    elements.promptInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auto-resize textarea
    elements.promptInput.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        if (this.value === '') this.style.height = 'auto';
    });

    // Enable send button only when there is text
    elements.promptInput.addEventListener('input', () => {
        elements.sendBtn.disabled = elements.promptInput.value.trim().length === 0 || state.isGenerating;
    });

});
