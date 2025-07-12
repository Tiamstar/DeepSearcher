# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Python Environment & Dependencies
```bash
# Install dependencies with uv
uv sync

# Install with all optional dependencies
uv sync --extra all

# Install development dependencies
uv sync --group dev
```

### Code Quality & Linting
```bash
# Format and lint check (no changes)
make lint

# Format and fix issues
make format

# Or run directly with uv
uv run ruff format
uv run ruff check --fix
```

### Testing
```bash
# Run tests
uv run pytest

# Run specific test file
uv run pytest tests/agent/test_chain_of_rag.py

# Run with coverage
uv run pytest --cov=deepsearcher
```

### Running the Application
```bash
# MCP System (main entry point)
python mcp_main.py --mode interactive
python mcp_main.py --mode api --host 0.0.0.0 --port 8000
python mcp_main.py --mode single --query "Generate a Python HTTP server"

# DeepSearcher CLI
uv run deepsearcher --help
uv run deepsearcher query --input "search query"

# API Server
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Documentation
```bash
# Serve documentation locally
mkdocs serve

# Build documentation
mkdocs build
```

## Architecture Overview

### Core Components

**DeepSearcher Engine**: The foundational RAG (Retrieval-Augmented Generation) system that powers intelligent search and document processing. Key modules:
- `deepsearcher/agent/`: RAG agents (chain_of_rag, naive_rag, deep_search)
- `deepsearcher/embedding/`: Multiple embedding providers (OpenAI, Milvus, Voyage, etc.)
- `deepsearcher/llm/`: LLM integrations (OpenAI, DeepSeek, Anthropic, etc.)
- `deepsearcher/vector_db/`: Vector database backends (Milvus, Qdrant, Azure Search)
- `deepsearcher/loader/`: File and web content loaders

**MCP Multi-Agent System**: Multi-agent collaboration system built on top of DeepSearcher:
- `mcp_orchestrator/`: Coordinator and workflow manager
- `mcp_agents/`: Specialized agents (project_manager, search, code_generator, code_checker, final_generator)
- `shared/`: Common interfaces and services

**Legacy HuaweiRAG**: Original Huawei-specific RAG implementation being phased out in favor of the MCP system.

### Configuration System

The system uses a unified configuration in `config/config.yaml` with provider-based architecture:
- Switch providers by commenting/uncommenting sections
- Support for multiple LLM providers (DeepSeek, OpenAI, SiliconFlow, etc.)
- Configurable embedding models and vector databases
- Agent-specific LLM overrides supported

### Key Design Patterns

**Provider Pattern**: All services (LLM, embedding, vector_db, etc.) use a provider pattern for easy switching between implementations.

**Agent Architecture**: MCP agents inherit from `MCPAgent` base class and implement standardized request handling.

**Configuration Inheritance**: Agents can override global LLM settings with agent-specific configurations.

## Working with the Codebase

### Adding New Providers
1. Create new provider class inheriting from base class in respective module
2. Implement required abstract methods
3. Add provider configuration to `config/config.yaml`
4. Update provider factory/registry

### Adding New Agents
1. Create agent class inheriting from `MCPAgent` in `mcp_agents/`
2. Implement `initialize()` and `handle_request()` methods
3. Register agent in `mcp_orchestrator/mcp_coordinator.py`
4. Add agent configuration to `config/config.yaml`

### Testing Strategy
- Unit tests for each component in `tests/` directory
- Integration tests for end-to-end workflows
- Agent-specific tests for MCP system
- Use pytest fixtures for common setup

### Code Style
- Python 3.10+ required
- Ruff for formatting and linting (line length: 100)
- Type hints encouraged
- Async/await patterns for I/O operations
- Structured logging with proper context

## Environment Setup

### Required Environment Variables
```bash
# LLM API Keys (choose based on provider)
DEEPSEEK_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# Embedding Provider Keys
SILICONFLOW_API_KEY=your_key_here
VOYAGE_API_KEY=your_key_here

# Optional Services
FIRECRAWL_API_KEY=your_key_here
```

### Development Setup
```bash
# Clone and setup
git clone https://github.com/zilliztech/deep-searcher.git
cd deep-searcher

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --extra all --group dev

# Copy environment template
cp .env.example .env
# Edit .env with your API keys
```

## Common Tasks

### Running Code Generation
```bash
# Interactive mode
python mcp_main.py --mode interactive

# Single request
python mcp_main.py --mode single --query "Create a FastAPI endpoint for user authentication"

# API mode
python mcp_main.py --mode api
```

### Working with Vector Database
```bash
# Load documents into vector database
python deepsearcher/offline_loading.py

# Query vector database
python deepsearcher/online_query.py
```

### Code Quality Checks
The system includes integrated code checking with:
- **ESLint**: For TypeScript/JavaScript/ArkTS code
- **CppCheck**: For C/C++ code analysis
- **SonarQube**: For comprehensive code quality analysis (optional)