# 🤖 AI LLM File Assistant

> An intelligent file management assistant powered by **OpenRouter** (multi-model LLM gateway) and Python tool-calling. The LLM understands natural language queries and autonomously reads, lists, writes, and searches files — including PDF, TXT, and DOCX resume files.

---

## 📁 Project Structure

```
AI_LLM_File_Assistant/
├── fs_tools.py              # Part A – Core file-system tools (read, list, write, search)
├── llm_file_assistant.py    # Part B – LLM integration & interactive CLI
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
├── .gitignore
├── README.md
└── resumes/                 # 10 sample resume files (TXT)
    ├── resume_alice_johnson.txt
    ├── resume_bob_martinez.txt
    ├── resume_carol_chen.txt
    ├── resume_david_kim.txt
    ├── resume_eva_patel.txt
    ├── resume_frank_nguyen.txt
    ├── resume_grace_liu.txt
    ├── resume_henry_thompson.txt
    ├── resume_iris_okonkwo.txt
    └── resume_james_rivera.txt
```

---

## ✨ Features

### Part A – Core File System Tools (`fs_tools.py`)

| Tool | Description |
|------|-------------|
| `read_file(filepath)` | Reads **PDF**, **TXT**, **DOCX** files and returns text + metadata |
| `list_files(directory, extension)` | Lists files with optional extension filter; returns name, size, modified date |
| `write_file(filepath, content)` | Writes text to a file; creates parent directories automatically |
| `search_in_file(filepath, keyword)` | Case-insensitive keyword search with surrounding context snippets |

### Part B – LLM Integration (`llm_file_assistant.py`)

- 🔄 **Agentic loop** – LLM iteratively calls tools until it has enough information to answer
- 🗣️ **Natural language interface** – plain English queries
- 💬 **Conversation memory** – multi-turn chat maintains context
- ⚡ **OpenRouter** – access GPT-4o, Claude, Mistral, and many more via one API key
- 🎛️ **Model switching** – change model via environment variable (`OPENROUTER_MODEL`)

---

## 🚀 Setup

### 1. Clone / Download the project

```bash
git clone https://github.com/your-username/AI_LLM_File_Assistant.git
cd AI_LLM_File_Assistant
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up your API key

Copy the example env file and fill in your OpenRouter API key:

```bash
cp .env.example .env
```

Edit `.env`:

```env
OPENROUTER_API_KEY=sk-or-v1-your-actual-key-here
OPENROUTER_MODEL=openai/gpt-4o-mini
```

> **Get a free OpenRouter API key** at [https://openrouter.ai/keys](https://openrouter.ai/keys)  
> Many models (e.g. `mistralai/mistral-7b-instruct`) are **free** on OpenRouter.

---

## 💻 Usage

### Interactive CLI

```bash
python llm_file_assistant.py
```

You'll see a welcome banner and a prompt:

```
You: List all resume files in the resumes folder
You: Read resumes/resume_alice_johnson.txt
You: Find all resumes mentioning Python experience
You: Summarise resumes/resume_bob_martinez.txt and save it to summaries/bob_summary.txt
You: help
You: quit
```

### Available CLI Commands

| Command | Action |
|---------|--------|
| `help` | Show usage instructions |
| `model` | Display the current model |
| `clear` | Clear conversation history |
| `quit` / `exit` | Exit the assistant |

---

## 🔧 Tool Details

### `read_file(filepath: str) → dict`

```python
from fs_tools import read_file

result = read_file("resumes/resume_alice_johnson.txt")
# Returns:
# {
#   "success": True,
#   "filepath": "/abs/path/to/file.txt",
#   "content": "Alice Johnson\nSenior Software Engineer\n...",
#   "metadata": {"name": "resume_alice_johnson.txt", "size_bytes": 2048, "modified": "...", "extension": ".txt"},
#   "error": None
# }
```

Supported formats: `.pdf`, `.txt`, `.docx`, `.md`, `.csv`, `.json`, and more.

---

### `list_files(directory: str, extension: str = None) → list`

```python
from fs_tools import list_files

files = list_files("resumes", ".txt")
# Returns list of dicts:
# [{"name": "resume_alice_johnson.txt", "path": "...", "size_bytes": 2048, "modified": "...", "extension": ".txt"}, ...]
```

---

### `write_file(filepath: str, content: str) → dict`

```python
from fs_tools import write_file

result = write_file("summaries/alice_summary.txt", "Alice Johnson - Senior Engineer with 7 years...")
# Returns:
# {"success": True, "filepath": "...", "bytes_written": 512, "error": None}
```

---

### `search_in_file(filepath: str, keyword: str) → dict`

```python
from fs_tools import search_in_file

result = search_in_file("resumes/resume_alice_johnson.txt", "Python")
# Returns:
# {
#   "success": True,
#   "keyword": "Python",
#   "total_matches": 8,
#   "matches": [
#     {"match_index": 1, "position": 142, "matched_text": "Python", "snippet": "...experienced in Python, Go..."},
#     ...
#   ]
# }
```

---

## 🧪 Running the Self-Test

```bash
python fs_tools.py
```

This runs a built-in self-test using a temporary directory to verify all four tools work correctly without any API key.

---

## 📝 Example Queries & What Happens

| Query | Tools Called |
|-------|-------------|
| `"List all resumes in the resumes folder"` | `list_files("resumes")` |
| `"Read Alice's resume"` | `list_files` → `read_file` |
| `"Find resumes mentioning Python experience"` | `list_files` → `search_in_file` × N |
| `"Create a summary file for Bob's resume"` | `read_file` → `write_file` |
| `"Which candidates have AWS certifications?"` | `list_files` → `search_in_file` × N |
| `"Read all PDF resumes in the folder"` | `list_files(ext=".pdf")` → `read_file` × N |

---

## 🌐 Supported OpenRouter Models

Change `OPENROUTER_MODEL` in your `.env`:

| Model Slug | Provider | Notes |
|------------|----------|-------|
| `openai/gpt-4o-mini` | OpenAI | **Default** – fast and cheap |
| `openai/gpt-4o` | OpenAI | Most capable GPT |
| `anthropic/claude-3-5-sonnet` | Anthropic | Excellent reasoning |
| `mistralai/mistral-7b-instruct` | Mistral | Often **free** |
| `google/gemini-flash-1.5` | Google | Fast Gemini |
| `meta-llama/llama-3.1-8b-instruct` | Meta | Free tier available |

Browse all models at [openrouter.ai/models](https://openrouter.ai/models).

---

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| `OPENROUTER_API_KEY is not set` | Create a `.env` file from `.env.example` |
| `ImportError: PyPDF2` | Run `pip install PyPDF2` |
| `ImportError: docx` | Run `pip install python-docx` |
| `Connection error` | Check internet connection |
| `API error 401` | Verify your API key is correct |
| `API error 402` | Add credits to your OpenRouter account |

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `requests` | HTTP calls to OpenRouter API |
| `python-dotenv` | Load `.env` file |
| `PyPDF2` | Extract text from PDF files |
| `python-docx` | Extract text from DOCX files |

---

## 🏗️ Architecture

```
User (CLI)
    │
    ▼
llm_file_assistant.py
    │  (natural language query)
    ▼
OpenRouter API  ──── LLM (GPT-4o-mini / Claude / etc.)
    │                          │
    │    ◄── tool_calls ───────┘
    ▼
fs_tools.py
    ├── read_file()       → PyPDF2 / python-docx / open()
    ├── list_files()      → os.scandir / pathlib
    ├── write_file()      → open(mode='w')
    └── search_in_file()  → string search + context extraction
    │
    ▼
Tool results (JSON) ──► back to LLM ──► final answer
```

---

## 📄 License

MIT License – free to use, modify, and distribute.
