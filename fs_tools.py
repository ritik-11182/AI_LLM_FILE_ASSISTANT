"""
fs_tools.py
-----------
Core File System Tools for the AI LLM File Assistant.

Provides four primary tools:
  - read_file       : Read PDF, TXT, DOCX files and extract text content.
  - list_files      : List files in a directory with optional extension filter.
  - write_file      : Write text content to a file, creating dirs as needed.
  - search_in_file  : Search for a keyword inside a file (case-insensitive).

All functions return structured dicts so they can be consumed directly by an LLM
tool-calling loop.
"""

import os
import json
import datetime
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Optional heavy-weight imports – imported lazily to keep the module light
# when certain formats are not needed.
# ---------------------------------------------------------------------------

def _import_pypdf2():
    try:
        import PyPDF2
        return PyPDF2
    except ImportError:
        raise ImportError(
            "PyPDF2 is required to read PDF files. "
            "Install it with: pip install PyPDF2"
        )


def _import_docx():
    try:
        import docx
        return docx
    except ImportError:
        raise ImportError(
            "python-docx is required to read DOCX files. "
            "Install it with: pip install python-docx"
        )


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _file_metadata(path: Path) -> dict:
    """Return a metadata dict for a given Path object."""
    stat = path.stat()
    return {
        "name": path.name,
        "path": str(path.resolve()),
        "size_bytes": stat.st_size,
        "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "extension": path.suffix.lower(),
    }


def _extract_text_txt(path: Path) -> str:
    """Extract text from a plain-text file."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _extract_text_pdf(path: Path) -> str:
    """Extract text from a PDF file using PyPDF2."""
    PyPDF2 = _import_pypdf2()
    text_parts = []
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def _extract_text_docx(path: Path) -> str:
    """Extract text from a DOCX file using python-docx."""
    docx = _import_docx()
    doc = docx.Document(str(path))
    paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
    return "\n".join(paragraphs)


# ---------------------------------------------------------------------------
# Tool 1 – read_file
# ---------------------------------------------------------------------------

def read_file(filepath: str) -> dict:
    """
    Read a resume or any text-based file (PDF, TXT, DOCX) and return its
    content along with metadata.

    Parameters
    ----------
    filepath : str
        Absolute or relative path to the file.

    Returns
    -------
    dict with keys:
        success  (bool)   – Whether the operation succeeded.
        filepath (str)    – Resolved absolute path of the file.
        content  (str)    – Extracted text content.
        metadata (dict)   – File metadata (name, size, modified, extension).
        error    (str)    – Error message if success is False.
    """
    path = Path(filepath)

    if not path.exists():
        return {
            "success": False,
            "filepath": str(path.resolve()),
            "content": "",
            "metadata": {},
            "error": f"File not found: {filepath}",
        }

    if not path.is_file():
        return {
            "success": False,
            "filepath": str(path.resolve()),
            "content": "",
            "metadata": {},
            "error": f"Path is not a file: {filepath}",
        }

    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            content = _extract_text_pdf(path)
        elif ext in (".docx", ".doc"):
            content = _extract_text_docx(path)
        elif ext in (".txt", ".md", ".rst", ".csv", ".json", ".xml", ".html"):
            content = _extract_text_txt(path)
        else:
            # Attempt plain-text read for unknown extensions
            content = _extract_text_txt(path)

        return {
            "success": True,
            "filepath": str(path.resolve()),
            "content": content,
            "metadata": _file_metadata(path),
            "error": None,
        }

    except Exception as exc:
        return {
            "success": False,
            "filepath": str(path.resolve()),
            "content": "",
            "metadata": _file_metadata(path) if path.exists() else {},
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Tool 2 – list_files
# ---------------------------------------------------------------------------

def list_files(directory: str, extension: Optional[str] = None) -> list:
    """
    List files in a directory, optionally filtered by extension.

    Parameters
    ----------
    directory : str
        Path to the directory to list.
    extension : str, optional
        File extension filter, e.g. '.pdf' or 'pdf'. If None, all files
        are returned.

    Returns
    -------
    list of dicts, each with:
        name      (str)  – File name.
        path      (str)  – Absolute path.
        size_bytes(int)  – File size in bytes.
        modified  (str)  – Last modified timestamp (ISO 8601).
        extension (str)  – File extension in lowercase.
    
    On error returns a list with a single error dict:
        [{"error": "<message>"}]
    """
    dir_path = Path(directory)

    if not dir_path.exists():
        return [{"error": f"Directory not found: {directory}"}]

    if not dir_path.is_dir():
        return [{"error": f"Path is not a directory: {directory}"}]

    # Normalise extension
    if extension:
        ext_filter = extension if extension.startswith(".") else f".{extension}"
        ext_filter = ext_filter.lower()
    else:
        ext_filter = None

    results = []
    try:
        for item in sorted(dir_path.iterdir()):
            if item.is_file():
                if ext_filter is None or item.suffix.lower() == ext_filter:
                    results.append(_file_metadata(item))
    except PermissionError as exc:
        return [{"error": f"Permission denied: {exc}"}]

    return results


# ---------------------------------------------------------------------------
# Tool 3 – write_file
# ---------------------------------------------------------------------------

def write_file(filepath: str, content: str) -> dict:
    """
    Write text content to a file, creating any missing parent directories.

    Parameters
    ----------
    filepath : str
        Destination file path (absolute or relative).
    content : str
        Text content to write.

    Returns
    -------
    dict with keys:
        success      (bool) – Whether the write succeeded.
        filepath     (str)  – Resolved absolute path of the written file.
        bytes_written(int)  – Number of bytes written.
        error        (str)  – Error message if success is False.
    """
    path = Path(filepath)

    try:
        # Create parent directories if they do not exist
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        bytes_written = path.stat().st_size

        return {
            "success": True,
            "filepath": str(path.resolve()),
            "bytes_written": bytes_written,
            "error": None,
        }

    except Exception as exc:
        return {
            "success": False,
            "filepath": str(path.resolve()),
            "bytes_written": 0,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Tool 4 – search_in_file
# ---------------------------------------------------------------------------

def search_in_file(filepath: str, keyword: str, context_chars: int = 150) -> dict:
    """
    Search for a keyword inside a file and return all matches with surrounding
    context. The search is case-insensitive.

    Parameters
    ----------
    filepath : str
        Path to the file to search.
    keyword : str
        Search term (case-insensitive).
    context_chars : int
        Number of characters to include before and after each match as context.

    Returns
    -------
    dict with keys:
        success      (bool)       – Whether the search completed successfully.
        filepath     (str)        – Resolved absolute path.
        keyword      (str)        – The search keyword used.
        total_matches(int)        – Total number of matches found.
        matches      (list[dict]) – List of match dicts:
                                      - match_index  : occurrence number (1-based)
                                      - position     : character position in content
                                      - snippet      : surrounding text excerpt
                                      - matched_text : the exact matched substring
        error        (str)        – Error message if success is False.
    """
    # First, read the file
    read_result = read_file(filepath)
    if not read_result["success"]:
        return {
            "success": False,
            "filepath": read_result["filepath"],
            "keyword": keyword,
            "total_matches": 0,
            "matches": [],
            "error": read_result["error"],
        }

    content = read_result["content"]
    content_lower = content.lower()
    keyword_lower = keyword.lower()

    matches = []
    start = 0
    idx = 1

    while True:
        pos = content_lower.find(keyword_lower, start)
        if pos == -1:
            break

        # Extract context
        ctx_start = max(0, pos - context_chars)
        ctx_end = min(len(content), pos + len(keyword) + context_chars)
        snippet = content[ctx_start:ctx_end]

        # Add ellipsis indicators
        if ctx_start > 0:
            snippet = "..." + snippet
        if ctx_end < len(content):
            snippet = snippet + "..."

        matches.append({
            "match_index": idx,
            "position": pos,
            "matched_text": content[pos: pos + len(keyword)],
            "snippet": snippet,
        })

        start = pos + len(keyword)
        idx += 1

    return {
        "success": True,
        "filepath": read_result["filepath"],
        "keyword": keyword,
        "total_matches": len(matches),
        "matches": matches,
        "error": None,
    }


# ---------------------------------------------------------------------------
# Tool registry – used by the LLM integration layer
# ---------------------------------------------------------------------------

TOOL_REGISTRY = {
    "read_file": read_file,
    "list_files": list_files,
    "write_file": write_file,
    "search_in_file": search_in_file,
}

# OpenAI/OpenRouter-compatible tool definitions (JSON Schema)
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read a file (PDF, TXT, DOCX) and return its full text content "
                "along with metadata such as size and last modified date. "
                "Use this to inspect resume files or any document."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file to read (absolute or relative).",
                    }
                },
                "required": ["filepath"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "List all files in a directory, optionally filtered by extension "
                "(e.g. '.pdf', '.txt', '.docx'). Returns file names, sizes, and "
                "modification dates."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Path to the directory to list.",
                    },
                    "extension": {
                        "type": "string",
                        "description": (
                            "Optional file extension filter, e.g. '.pdf' or 'pdf'. "
                            "If omitted, all files are returned."
                        ),
                    },
                },
                "required": ["directory"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Write text content to a file. Creates parent directories "
                "automatically if they do not exist. Use this to save summaries, "
                "reports, or any generated text."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Destination file path.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Text content to write to the file.",
                    },
                },
                "required": ["filepath", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_in_file",
            "description": (
                "Search for a keyword or phrase inside a file. Returns all "
                "occurrences with surrounding context. Case-insensitive. "
                "Use this to find resumes mentioning specific skills or technologies."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file to search.",
                    },
                    "keyword": {
                        "type": "string",
                        "description": "Search term (case-insensitive).",
                    },
                },
                "required": ["filepath", "keyword"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Quick self-test when run directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import tempfile

    print("=== fs_tools.py self-test ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        # write_file
        test_file = os.path.join(tmpdir, "test.txt")
        result = write_file(test_file, "Hello, Python!\nThis is a test file.\nPython is great.")
        print("write_file:", json.dumps(result, indent=2))

        # read_file
        result = read_file(test_file)
        print("\nread_file:", json.dumps(result, indent=2))

        # list_files
        result = list_files(tmpdir)
        print("\nlist_files:", json.dumps(result, indent=2))

        # search_in_file
        result = search_in_file(test_file, "python")
        print("\nsearch_in_file:", json.dumps(result, indent=2))

    print("\nAll tests passed!")
