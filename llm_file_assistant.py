"""
llm_file_assistant.py
---------------------
LLM-powered File Assistant using OpenRouter as the API gateway.

This module sets up an interactive chat loop where the LLM can call the
four file-system tools defined in fs_tools.py based on natural language
queries from the user.

Usage:
    python llm_file_assistant.py

Environment Variables:
    OPENROUTER_API_KEY  – Your OpenRouter API key (required).
    OPENROUTER_MODEL    – Model slug to use (default: openai/gpt-4o-mini).

Example queries:
    "List all resumes in the resumes folder"
    "Read the file resumes/resume_alice.txt"
    "Find resumes mentioning Python experience"
    "Create a summary file for resume_john_doe.txt"
"""

import os
import json
import sys
import textwrap
from typing import Any

import requests
from dotenv import load_dotenv

# Import our custom tools
from fs_tools import TOOL_DEFINITIONS, TOOL_REGISTRY

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()  # Load .env file if present

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL   = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

SYSTEM_PROMPT = """You are an intelligent File Assistant that helps users manage and \
analyse resume files and other documents.

You have access to four powerful file-system tools:
1. **read_file**      – Read PDF, TXT, or DOCX files and extract their content.
2. **list_files**     – List files in a directory, optionally filtered by extension.
3. **write_file**     – Create or overwrite a file with given text content.
4. **search_in_file** – Search for keywords inside a file (case-insensitive).

Guidelines:
- Always use the tools to answer questions about files; never guess or fabricate content.
- When asked to summarise a resume, first read it, then write a concise summary.
- When asked to find resumes mentioning a skill, list all resumes first, then search each one.
- Be concise but informative in your final responses.
- If a tool call fails, report the error clearly and suggest what the user can do.
- Relative paths are resolved from the current working directory where the script is run.
"""

# ---------------------------------------------------------------------------
# OpenRouter API client
# ---------------------------------------------------------------------------

class OpenRouterClient:
    """Thin wrapper around the OpenRouter /chat/completions endpoint."""

    def __init__(self, api_key: str, model: str, base_url: str = OPENROUTER_BASE_URL):
        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is not set. "
                "Please set it in your .env file or as an environment variable."
            )
        self.api_key  = api_key
        self.model    = model
        self.base_url = base_url
        self.headers  = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
            "HTTP-Referer":  "https://github.com/ai-llm-file-assistant",  # Optional
            "X-Title":       "AI LLM File Assistant",                      # Optional
        }

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
    ) -> dict:
        """Send a chat completion request and return the response dict."""
        payload: dict[str, Any] = {
            "model":    self.model,
            "messages": messages,
        }
        if tools:
            payload["tools"]       = tools
            payload["tool_choice"] = tool_choice

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json=payload,
            timeout=120,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"OpenRouter API error {response.status_code}: {response.text}"
            )

        return response.json()


# ---------------------------------------------------------------------------
# Tool execution helper
# ---------------------------------------------------------------------------

def execute_tool_call(tool_name: str, tool_args: dict) -> str:
    """
    Look up and call the appropriate tool from TOOL_REGISTRY.
    Returns a JSON string to be fed back into the conversation as a tool message.
    """
    if tool_name not in TOOL_REGISTRY:
        result = {"error": f"Unknown tool: {tool_name}"}
    else:
        try:
            result = TOOL_REGISTRY[tool_name](**tool_args)
        except Exception as exc:
            result = {"error": f"Tool execution failed: {exc}"}

    return json.dumps(result, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Agentic loop
# ---------------------------------------------------------------------------

def run_agent(client: OpenRouterClient, user_query: str, messages: list[dict]) -> str:
    """
    Run a single agentic turn: send the user query, execute any tool calls
    the LLM makes, feed results back, and return the final text response.

    Parameters
    ----------
    client      : OpenRouterClient instance.
    user_query  : The user's natural language request.
    messages    : Conversation history (modified in-place).

    Returns
    -------
    str – The LLM's final text response.
    """
    # Append the new user message
    messages.append({"role": "user", "content": user_query})

    max_iterations = 10  # Safety guard against infinite loops

    for iteration in range(max_iterations):
        response = client.chat(messages, tools=TOOL_DEFINITIONS)
        choice   = response["choices"][0]
        message  = choice["message"]

        # Add the assistant message to history
        messages.append(message)

        finish_reason = choice.get("finish_reason", "")

        # ----- No more tool calls → return the final answer -----
        if finish_reason == "stop" or not message.get("tool_calls"):
            return message.get("content", "(No response)")

        # ----- Process tool calls -----
        tool_calls = message["tool_calls"]
        print(f"\n  🔧 LLM is calling {len(tool_calls)} tool(s)...")

        for tc in tool_calls:
            tool_name = tc["function"]["name"]
            raw_args  = tc["function"].get("arguments", "{}")

            try:
                tool_args = json.loads(raw_args)
            except json.JSONDecodeError:
                tool_args = {}

            print(f"     → {tool_name}({json.dumps(tool_args)})")

            tool_result = execute_tool_call(tool_name, tool_args)

            # Feed tool result back into the conversation
            messages.append({
                "role":         "tool",
                "tool_call_id": tc["id"],
                "content":      tool_result,
            })

    return "(Max tool-call iterations reached — please try a simpler query.)"


# ---------------------------------------------------------------------------
# Interactive CLI
# ---------------------------------------------------------------------------

BANNER = r"""
╔══════════════════════════════════════════════════════════╗
║          🤖  AI LLM File Assistant  📄                   ║
║  Powered by OpenRouter · Tools: read, list, write, search ║
╚══════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
Commands:
  help          Show this help message
  model         Show the current model
  clear         Clear the conversation history
  quit / exit   Exit the assistant

Example queries:
  "List all files in the resumes folder"
  "Read resumes/resume_alice.txt"
  "Find resumes mentioning Python experience"
  "Summarise resumes/resume_bob.txt and save it to summaries/bob_summary.txt"
"""


def interactive_loop():
    """Start an interactive CLI session with the LLM File Assistant."""
    print(BANNER)

    if not OPENROUTER_API_KEY:
        print("❌  ERROR: OPENROUTER_API_KEY is not set.")
        print("   Create a .env file with: OPENROUTER_API_KEY=your_key_here")
        sys.exit(1)

    try:
        client = OpenRouterClient(
            api_key  = OPENROUTER_API_KEY,
            model    = OPENROUTER_MODEL,
            base_url = OPENROUTER_BASE_URL,
        )
    except ValueError as exc:
        print(f"❌  {exc}")
        sys.exit(1)

    print(f"✅  Connected to OpenRouter  |  Model: {OPENROUTER_MODEL}")
    print(f"📁  Working directory: {os.getcwd()}")
    print("Type 'help' for usage instructions or 'quit' to exit.\n")

    # Initialise conversation with system prompt
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye! 👋")
            break

        if not user_input:
            continue

        # ---- Built-in commands ----
        if user_input.lower() in ("quit", "exit"):
            print("Goodbye! 👋")
            break

        if user_input.lower() == "help":
            print(HELP_TEXT)
            continue

        if user_input.lower() == "model":
            print(f"  Current model: {OPENROUTER_MODEL}")
            continue

        if user_input.lower() == "clear":
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            print("  ✅  Conversation history cleared.")
            continue

        # ---- Run the agent ----
        print("\n  ⏳ Thinking...", flush=True)
        try:
            answer = run_agent(client, user_input, messages)
        except RuntimeError as exc:
            print(f"\n❌  API Error: {exc}\n")
            continue
        except requests.exceptions.ConnectionError:
            print("\n❌  Connection error. Check your internet connection.\n")
            continue
        except requests.exceptions.Timeout:
            print("\n❌  Request timed out. Try again.\n")
            continue

        # Pretty-print the response
        print("\nAssistant:")
        for line in answer.splitlines():
            print(textwrap.fill(line, width=90, subsequent_indent="  ") if line else "")
        print()


# ---------------------------------------------------------------------------
# Non-interactive / batch mode (for scripting / demo)
# ---------------------------------------------------------------------------

def run_query(query: str, working_dir: str | None = None) -> str:
    """
    Run a single query programmatically and return the assistant's answer.
    Useful for testing or embedding in other scripts.

    Parameters
    ----------
    query       : Natural language query string.
    working_dir : Optional directory to chdir into before running.

    Returns
    -------
    str – The assistant's response text.
    """
    if working_dir:
        os.chdir(working_dir)

    client = OpenRouterClient(
        api_key  = OPENROUTER_API_KEY,
        model    = OPENROUTER_MODEL,
        base_url = OPENROUTER_BASE_URL,
    )
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    return run_agent(client, query, messages)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    interactive_loop()
