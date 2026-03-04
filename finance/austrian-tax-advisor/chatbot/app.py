"""FastAPI server for the Austrian Tax Advisor Chatbot."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import anthropic

from config import ANTHROPIC_API_KEY, MAX_CONVERSATION_TURNS, MAX_TOKENS, MODEL, TEMPERATURE
from knowledge import get_system_prompt
from tools import TOOLS, execute_tool

app = FastAPI(title="Österreichischer Steuerberater 2026", version="1.0.0")

# Serve static frontend files
FRONTEND_DIR = Path(__file__).parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# Anthropic client
client: Optional[anthropic.Anthropic] = None


def get_client() -> anthropic.Anthropic:
    """Lazy-init the Anthropic client."""
    global client
    if client is None:
        if not ANTHROPIC_API_KEY:
            raise HTTPException(
                status_code=500,
                detail="ANTHROPIC_API_KEY ist nicht gesetzt. Bitte .env konfigurieren.",
            )
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return client


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    response: str
    tools_used: List[str] = []


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the chat frontend."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse("<h1>Frontend nicht gefunden. Bitte chatbot/frontend/ prüfen.</h1>")


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "model": MODEL,
        "tools_available": len(TOOLS),
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle a chat message with Claude API + Tool Use."""
    api_client = get_client()

    # Build messages from conversation history
    messages: List[Dict[str, Any]] = []
    for msg in request.conversation_history[-MAX_CONVERSATION_TURNS * 2:]:
        messages.append({"role": msg.role, "content": msg.content})

    # Add the new user message
    messages.append({"role": "user", "content": request.message})

    system_prompt = get_system_prompt()
    tools_used: List[str] = []

    # Loop to handle tool use (Claude may call multiple tools)
    max_iterations = 5
    for _ in range(max_iterations):
        response = api_client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )

        # Check if Claude wants to use a tool
        if response.stop_reason == "tool_use":
            # Process all tool use blocks
            assistant_content = response.content
            messages.append({"role": "assistant", "content": assistant_content})

            tool_results = []
            for block in assistant_content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    tools_used.append(tool_name)

                    # Execute the tool
                    result = execute_tool(tool_name, tool_input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "user", "content": tool_results})
        else:
            # Claude is done — extract text response
            text_parts = []
            for block in response.content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)

            return ChatResponse(
                response="\n".join(text_parts),
                tools_used=tools_used,
            )

    # Fallback if max iterations reached
    return ChatResponse(
        response="Entschuldigung, die Berechnung war zu komplex. Bitte versuchen Sie es mit einer einfacheren Frage.",
        tools_used=tools_used,
    )


if __name__ == "__main__":
    import uvicorn
    from config import HOST, PORT
    uvicorn.run(app, host=HOST, port=PORT)
