# Copilot Sandbox & RepoMap POC

A proof-of-concept demonstrating:
1. **Isolated Execution Sandbox (`RepoSandbox`)**: Clones target Git repositories into a temporary workspace and runs isolated builds, tests, or compilation verification inside Docker containers.
2. **Production Graph-Ranked Repo-Map (`ProductionRepoMapEngine`)**: Parses codebase abstract syntax trees (ASTs) using Tree-Sitter (supporting C# and Python), computes file importance using PageRank on reference-definition graphs, and generates a token-budgeted repository map with TikToken.

---

## Features

- **Docker-Isolated Verification**: Mounts cloned code into container runtimes (e.g. `mcr.microsoft.com/dotnet/sdk:8.0`, Python, etc.) to securely test build commands without polluting the host environment.
- **AST Tagging with Tree-Sitter**: Identifies definitions (`class`, `interface`, `method`, `func`) and references (`call`) using S-expression queries.
- **SQLite Tag Caching (`TagCache`)**: Caches MD5 file hashes and AST tags to avoid re-parsing unchanged files.
- **PageRank Symbol Graph**: Builds a directed multi-graph connecting caller files to definition files with NetworkX and ranks files by structural centrality.
- **Token-Budgeted Packing**: Formats top-ranked files and declarations within a customizable token limit using TikToken (`cl100k_base`).

---

## Project Structure

```
repo-sandbox/
├── src/
│   └── sandbox/
│       ├── __init__.py           # Package exports
│       ├── repo_sandbox.py       # Git clone & Docker sandbox runner
│       ├── ast_tagger.py         # Tree-Sitter C# & Python AST tagger
│       ├── tag_cache.py          # SQLite-backed tag cache
│       └── repo_map_engine.py    # NetworkX PageRank & repo-map generator
├── run_test.py                   # End-to-end integration test
├── pyproject.toml                # uv / PEP 621 project configuration
└── .gitignore
```

---

## Getting Started

### Prerequisites
- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (recommended package manager)
- Docker Desktop (running)
- Git

### Installation

```bash
uv sync
```

### Running the Test

Run the full end-to-end test (clones sample repo, executes Docker build check, and outputs the graph-ranked repo map):

```bash
uv run run_test.py
```
