# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Retrieval-Augmented Generation (RAG) system for querying course materials using ChromaDB vector storage, Anthropic's Claude API, and semantic search. The system uses tool-based search where Claude autonomously decides when to search the knowledge base.

**Tech Stack**: FastAPI backend, vanilla JS frontend, ChromaDB for vectors, sentence-transformers for embeddings

## Development Commands

### Running the Application
```bash
# Quick start (recommended)
./run.sh

# Manual start
cd backend
uv run uvicorn app:app --reload --port 8000
```

### Package Management
```bash
# Install dependencies
uv sync

# Add a new package
uv add <package-name>

# Add a development dependency
uv add --dev <package-name>
```

### Code Quality
```bash
# Format code (black + isort)
./scripts/format.sh

# Run linters (flake8 + mypy)
./scripts/lint.sh

# Run all quality checks (without auto-fixing)
./scripts/check.sh

# Individual tools
uv run black backend/          # Format code
uv run isort backend/          # Sort imports
uv run flake8 backend/         # Lint code
uv run mypy backend/           # Type check
```

**Quality Tools Configuration**:
- **black**: Line length 88, Python 3.13 target (configured in `pyproject.toml`)
- **isort**: Black-compatible profile (configured in `pyproject.toml`)
- **flake8**: Compatible with black, ignores E203/W503 (configured in `.flake8`)
- **mypy**: Lenient settings, ignores missing imports (configured in `pyproject.toml`)

### Environment Setup
Required `.env` file in root:
```
ANTHROPIC_API_KEY=your_key_here
```

**Important**: Claude Code Pro subscription ≠ Anthropic API access. You need separate API credits from https://console.anthropic.com/settings/billing

### Troubleshooting
```bash
# Port 8000 already in use
lsof -i :8000  # Find process ID
kill <PID>     # Kill the process

# Reset database (clears all courses)
rm -rf backend/chroma_db/

# Check if documents loaded on startup
# Server logs should show: "Loaded N courses with M chunks"
```

## Architecture

### Query Flow Summary

```
User Query → FastAPI → RAGSystem → AIGenerator
                                       ↓
                          [Claude API Call #1 with tools]
                          Claude decides: "I should search"
                                       ↓
                          ToolManager → CourseSearchTool
                                       ↓
                          VectorStore → ChromaDB (semantic search)
                                       ↓
                          Returns top 5 chunks with metadata
                                       ↓
                          [Claude API Call #2 with results]
                          Claude synthesizes answer from chunks
                                       ↓
                          SessionManager saves conversation
                                       ↓
                          Response + sources → Frontend
```

**Critical Detail**: Each query makes **two Claude API calls**:
1. First call (with tools): Claude decides whether to search
2. Second call (without tools): Claude synthesizes answer from search results

### Core RAG Pipeline Flow

1. **Document Processing** (`document_processor.py`): Parses structured course documents, extracts metadata (title, instructor, lessons), and chunks content with sentence-aware splitting
2. **Dual Vector Storage** (`vector_store.py`):
   - `course_catalog` collection: Course metadata with fuzzy name matching
   - `course_content` collection: Chunked lesson content for semantic search
   - Persists at `./backend/chroma_db/`
3. **Tool-Based Search** (`search_tools.py`): Claude autonomously calls `search_course_content` tool with optional `course_name` and `lesson_number` filters
4. **Response Generation** (`ai_generator.py`): Claude synthesizes answers using search results, with conversation history support

### Component Interactions

```
RAGSystem (orchestrator)
├── DocumentProcessor: Parses & chunks course files
├── VectorStore: Two-collection ChromaDB setup
│   ├── Course name resolution via semantic search
│   └── Content filtering by course_title & lesson_number
├── AIGenerator: Claude API with tool calling
├── SessionManager: Conversation history (max_history configurable)
└── ToolManager: Registers & executes search tools
```

### Key Design Decisions

**Two-Collection Strategy**:
- `course_catalog` uses course titles as IDs for fuzzy matching (e.g., "MCP" → "Introduction to MCP")
- `course_content` stores chunks with `course_title` and `lesson_number` metadata for filtering

**Chunking Strategy** (`document_processor.py:25-91`):
- Sentence-based chunking with configurable overlap (default: 800 chars, 100 overlap)
- First chunk of each lesson prefixed with "Lesson N content:" for context

**Tool Execution Flow** (`ai_generator.py:89-135`):
1. Claude makes initial request (possibly with tool calls)
2. Tools execute and return formatted results: `[Course - Lesson N]\n{content}`
3. Results added to message history
4. Claude generates final response

**Session Management**:
- Sessions auto-created if not provided in `/api/query`
- History limited to `max_history * 2` messages (default: 4 total)

### Configuration (`backend/config.py`)

All tunable parameters in `Config` dataclass:
- `CHUNK_SIZE`: 800 (text chunk size)
- `CHUNK_OVERLAP`: 100 (overlap between chunks)
- `MAX_RESULTS`: 5 (search results per query)
- `MAX_HISTORY`: 2 (conversation exchanges to remember)
- `ANTHROPIC_MODEL`: "claude-sonnet-4-20250514"
- `EMBEDDING_MODEL`: "all-MiniLM-L6-v2"

### Document Format

Course files in `docs/` must follow this structure:
```
Course Title: [title]
Course Link: [url]
Course Instructor: [name]

Lesson 1: [title]
Lesson Link: [url]
[content]

Lesson 2: [title]
...
```

### API Endpoints

- `POST /api/query`: Process query with RAG system
  - Request: `{"query": str, "session_id": str?}`
  - Response: `{"answer": str, "sources": List[str], "session_id": str}`
- `GET /api/courses`: Get course statistics
  - Response: `{"total_courses": int, "course_titles": List[str]}`

### Startup Behavior

On server start (`@app.on_event("startup")`), all documents in `docs/` are automatically:
1. Parsed for course metadata and lessons
2. Chunked into ~800 character segments
3. Embedded using sentence-transformers
4. Stored in ChromaDB collections

Duplicate courses are skipped based on course title. Check logs for: `"Loaded N courses with M chunks"`

### Data Models (`backend/models.py`)

- `Course`: title, course_link, instructor, lessons[]
- `Lesson`: lesson_number, title, lesson_link
- `CourseChunk`: content, course_title, lesson_number, chunk_index

## Important Implementation Notes

### Vector Search Logic
The `VectorStore.search()` method in `vector_store.py:61-100` handles:
1. Course name resolution via `_resolve_course_name()` using semantic search on catalog
2. Filter construction for course_title and/or lesson_number
3. Content search with ChromaDB's `where` filtering

### Preventing Duplicate Courses
`add_course_folder()` in `rag_system.py:52-100` checks `get_existing_course_titles()` before adding courses. Course titles are used as unique IDs.

### Tool Source Tracking
`CourseSearchTool` in `search_tools.py:20-114` stores `last_sources` during search, retrieved via `ToolManager.get_last_sources()` and returned in API responses.

### AI System Prompt
`AIGenerator.SYSTEM_PROMPT` in `ai_generator.py:8-30` enforces:
- One search maximum per query
- Direct answers without meta-commentary
- Search only for course-specific questions
- make sure to use uv to manage all dependencies