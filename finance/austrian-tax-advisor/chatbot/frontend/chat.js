/**
 * Austrian Tax Advisor — Chat Frontend Logic
 * Vanilla JS, no framework. Handles messaging, markdown rendering, history.
 */

(function () {
    "use strict";

    // DOM elements
    const chatArea = document.getElementById("chat-area");
    const messagesContainer = document.getElementById("messages");
    const welcomeEl = document.getElementById("welcome");
    const userInput = document.getElementById("user-input");
    const sendBtn = document.getElementById("send-btn");
    const newChatBtn = document.getElementById("new-chat-btn");

    // Conversation state (per session)
    let conversationHistory = [];
    let isLoading = false;

    // --- Markdown to HTML (simple parser, no library) ---

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    function markdownToHtml(md) {
        let html = md;

        // Code blocks (```...```)
        html = html.replace(/```(\w*)\n([\s\S]*?)```/g, function (_, lang, code) {
            return '<pre><code class="lang-' + lang + '">' + escapeHtml(code.trim()) + "</code></pre>";
        });

        // Inline code
        html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

        // Tables
        html = html.replace(
            /(?:^\|.+\|$\n?)+/gm,
            function (table) {
                const rows = table.trim().split("\n");
                if (rows.length < 2) return table;

                let result = "<table>";
                rows.forEach(function (row, i) {
                    // Skip separator row
                    if (/^\|[\s\-:|]+\|$/.test(row)) return;

                    const tag = i === 0 ? "th" : "td";
                    const cells = row
                        .split("|")
                        .filter(function (c) { return c.trim() !== ""; })
                        .map(function (c) { return c.trim(); });

                    result += "<tr>";
                    cells.forEach(function (cell) {
                        result += "<" + tag + ">" + cell + "</" + tag + ">";
                    });
                    result += "</tr>";
                });
                result += "</table>";
                return result;
            }
        );

        // Headers
        html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
        html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
        html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");

        // Bold
        html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

        // Italic
        html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");

        // Unordered lists
        html = html.replace(/^[\-\*] (.+)$/gm, "<li>$1</li>");
        html = html.replace(/(<li>.*<\/li>\n?)+/g, "<ul>$&</ul>");

        // Ordered lists
        html = html.replace(/^\d+\. (.+)$/gm, "<li>$1</li>");

        // Line breaks → paragraphs
        html = html.replace(/\n\n/g, "</p><p>");
        html = html.replace(/\n/g, "<br>");

        // Wrap in paragraph if not already wrapped
        if (!html.startsWith("<")) {
            html = "<p>" + html + "</p>";
        }

        return html;
    }

    // --- UI Functions ---

    function addMessage(role, content, toolsUsed) {
        if (welcomeEl) {
            welcomeEl.style.display = "none";
        }

        const messageDiv = document.createElement("div");
        messageDiv.className = "message " + role;

        const avatar = document.createElement("div");
        avatar.className = "message-avatar";
        avatar.textContent = role === "user" ? "Du" : "AT";

        const contentDiv = document.createElement("div");
        contentDiv.className = "message-content";

        if (role === "bot") {
            contentDiv.innerHTML = markdownToHtml(content);
        } else {
            contentDiv.textContent = content;
        }

        // Show tools used badges
        if (toolsUsed && toolsUsed.length > 0) {
            const toolsDiv = document.createElement("div");
            toolsDiv.className = "tools-used";
            toolsUsed.forEach(function (tool) {
                const badge = document.createElement("span");
                badge.className = "tool-badge";
                badge.textContent = tool.replace(/_/g, " ");
                toolsDiv.appendChild(badge);
            });
            contentDiv.appendChild(toolsDiv);
        }

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);

        scrollToBottom();
    }

    function showThinking() {
        const thinkingDiv = document.createElement("div");
        thinkingDiv.className = "thinking";
        thinkingDiv.id = "thinking-indicator";
        thinkingDiv.innerHTML =
            '<div class="thinking-dots"><span></span><span></span><span></span></div>' +
            "<span>Berechne...</span>";
        messagesContainer.appendChild(thinkingDiv);
        scrollToBottom();
    }

    function hideThinking() {
        const indicator = document.getElementById("thinking-indicator");
        if (indicator) {
            indicator.remove();
        }
    }

    function scrollToBottom() {
        chatArea.scrollTop = chatArea.scrollHeight;
    }

    function setLoading(loading) {
        isLoading = loading;
        sendBtn.disabled = loading;
        userInput.disabled = loading;
    }

    function resetChat() {
        conversationHistory = [];
        messagesContainer.innerHTML = "";
        if (welcomeEl) {
            welcomeEl.style.display = "block";
        }
        userInput.value = "";
        userInput.focus();
    }

    // --- API Communication ---

    async function sendMessage(text) {
        if (!text.trim() || isLoading) return;

        // Add user message to UI
        addMessage("user", text.trim());
        conversationHistory.push({ role: "user", content: text.trim() });

        setLoading(true);
        showThinking();

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: text.trim(),
                    conversation_history: conversationHistory.slice(-20),
                }),
            });

            hideThinking();

            if (!response.ok) {
                const errorData = await response.json().catch(function () {
                    return { detail: "Serverfehler" };
                });
                addMessage("bot", "Fehler: " + (errorData.detail || "Unbekannter Fehler"));
                return;
            }

            const data = await response.json();
            addMessage("bot", data.response, data.tools_used);
            conversationHistory.push({ role: "assistant", content: data.response });
        } catch (err) {
            hideThinking();
            addMessage(
                "bot",
                "Verbindungsfehler. Bitte prüfen Sie, ob der Server läuft."
            );
        } finally {
            setLoading(false);
            userInput.focus();
        }
    }

    // --- Event Listeners ---

    sendBtn.addEventListener("click", function () {
        sendMessage(userInput.value);
        userInput.value = "";
        autoResize();
    });

    userInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage(userInput.value);
            userInput.value = "";
            autoResize();
        }
    });

    newChatBtn.addEventListener("click", resetChat);

    // Auto-resize textarea
    function autoResize() {
        userInput.style.height = "auto";
        userInput.style.height = Math.min(userInput.scrollHeight, 120) + "px";
    }

    userInput.addEventListener("input", autoResize);

    // Quickstart buttons
    document.querySelectorAll(".quickstart-btn").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var question = btn.getAttribute("data-question");
            userInput.value = question;
            sendMessage(question);
            userInput.value = "";
        });
    });

    // Focus input on load
    userInput.focus();
})();
