# paper-tools: AI Agent Usage Guide

## Overview

`paper-tools` is a Python library for automating paper-writing tasks. It provides:
- **InspireHEP API client** for literature queries, BibTeX retrieval, citation analysis
- **LMDB-backed databases** for persistent local storage of InspireHEP records and embeddings
- **LaTeX processing** (parse, extract sections/paragraphs, validate well-formedness)
- **LLM integration** for AI-assisted writing tasks
- **Faiss-based semantic search** over paper abstracts

## Installation

```bash
pip install -e .
# Also install missing deps not yet in pyproject.toml:
pip install pipe faiss-cpu FlagEmbedding numpy openai langchain-openai langchain-core networkx thefuzz
```

## Module Reference

### 1. `paper_tools.latex_tools` — LaTeX Processing

Core class: `LatexSnippet(text: str)`

```python
from paper_tools.latex_tools import LatexSnippet, is_latex_well_formed, extract_sections, split_to_paragraphs

snippet = LatexSnippet(latex_string)
snippet.is_well_formed()      # bool — does the LaTeX parse cleanly?
snippet.get_paragraphs()      # list[str] — paragraphs with comments stripped
snippet.get_sections()        # list[str] — text between \section commands
snippet.get_maintext()        # str — all body text, comments + preamble removed
snippet.comments_removed()    # str — text with % comments removed
snippet.nontext_removed()     # str — text with preamble macros removed

# Convenience functions:
is_latex_well_formed(text)    # bool
extract_sections(text)        # list[str]
split_to_paragraphs(text)     # list[str]
extract_head_lines(text, n)   # str — first n lines
```

Key visitors: `NontextVisitor`, `CommentVisitor`, `SectionVisitor` (used internally with `get_intervals`).

### 2. `paper_tools.inspirehep_tools` — InspireHEP Integration

#### InspireHEPClient — API client with rate limiting

```python
from paper_tools.inspirehep_tools import InspireHEPClient

client = InspireHEPClient()

# Get a single record
record = client.get_literature("1234567")  # by InspireHEP ID

# Get multiple records in batch (max 50 per call)
records = client.get_literature_batched(["1234567", "7654321"])

# Resolve BibTeX keys to InspireHEP IDs
id_map = client.get_id_by_texkey(["PhysRevLett.116.061102"])

# Find papers by author BAI
paper_ids = client.get_id_by_author("A.Einstein.1")

# Get BibTeX for an ID
bibtex = client.get_bibtex("1234567")

# Get all citations to a paper
citing_ids = client.all_cites_to("1234567")

# Batch citation lookup
citing_ids = client.all_cites_to_batched(["1234567", "7654321"])
```

#### InspireHEPDatabase — Local LMDB storage with semantic search

```python
from paper_tools.config import get_data_dir
from paper_tools.inspirehep_tools import InspireHEPDatabase

db = InspireHEPDatabase(str(get_data_dir()), readonly=True)

# Access records and BibTeX as dict-like objects
record = db.record["1234567"]        # dict from InspireHEP JSON
bibtex = db.bibtex["1234567"]        # str BibTeX entry

# Check if a record exists
"1234567" in db.record

# Iterate all keys
for rec_id in db.record:
    print(rec_id)

# Semantic search over abstracts (requires model + embeddings)
db.load_model()     # Loads BAAI/bge-large-en-v1.5
db.index_embeddings()
scores, ids = db.search_abstract(["black hole perturbations"], k=10)
```

#### LMDB Wrappers

```python
from paper_tools.inspirehep_tools import InspireHEPRecordLmdbWrapper, EmbeddingLmdbWrapper
from paper_tools.lmdb_wrapper import LmdbWrapperBase

# Customize for your own data types by subclassing LmdbWrapperBase
# and overriding pack_value / unpack_value
```

#### BFS Literature Download

```python
from paper_tools.inspirehep_tools import inspirehep_bfs_literature_batch

collection = {}
inspirehep_bfs_literature_batch(collection, roots=["1234567"], max_size=100, mode="refs")
# mode: "refs" (follow references), "cites" (follow citations), "both"
```

### 3. `paper_tools.pipe_usage` — Query Operators (pipe-based)

Filter/sort/transform InspireHEP record collections with pipeline operators:

```python
import pipe
from paper_tools.pipe_usage import (
    filter_by_abstract, filter_by_author, filter_by_title,
    filter_by_year, filter_after, filter_before,
    sort_by_citations, get_title, get_id, get_authors
)

# Example:
results = list(collection.items()
    | filter_by_abstract('quasinormal mode')
    | sort_by_citations()
    | pipe.take(5)
    | get_title
)
```

**Note:** The module-level code in `pipe_usage.py` has undefined variables and will crash on import. The decorators themselves work correctly when imported. See "Known Issues" section.

### 4. `paper_tools.llm_wrapper` — LLM Integration

```python
from paper_tools.llm_wrapper import CustomDeepseekChat

chat = CustomDeepseekChat(
    model="deepseek-chat",
    api_key="...",
    base_url="https://api.deepseek.com/v1"
)
# Usage is standard LangChain ChatOpenAI interface
```

### 5. `paper_tools.config` — Configuration

```python
from paper_tools.config import get_data_dir
path = get_data_dir()  # Returns Path to OS-appropriate data directory
# Override via env var: PAPER_TOOLS_DATA_PATH
```

## Common Workflows

### Workflow 1: Find papers citing a known paper, store locally

```python
from paper_tools.inspirehep_tools import InspireHEPClient, InspireHEPDatabase
from paper_tools.config import get_data_dir

client = InspireHEPClient()
citing_ids = client.all_cites_to("1234567")
records = client.get_literature_batched(citing_ids)
bibtexs = client.get_bibtex_batched(citing_ids)

db = InspireHEPDatabase(str(get_data_dir()), readonly=False)
for rec_id, rec in records.items():
    db.record[rec_id] = rec
```

### Workflow 2: Validate and clean a LaTeX paper

```python
from paper_tools.latex_tools import LatexSnippet

with open("paper.tex") as f:
    tex = f.read()

snip = LatexSnippet(tex)
assert snip.is_well_formed(), "LaTeX has syntax errors"

main_text = snip.get_maintext()
paragraphs = snip.get_paragraphs()
```

### Workflow 3: Semantic literature search

```python
db = InspireHEPDatabase(str(get_data_dir()), init_model=True)
db.index_embeddings()
scores, paper_ids = db.search_abstract(["gravitational wave black hole merger"], k=20)
for s, pid in zip(scores[0], paper_ids[0]):
    title = db.record[pid]["metadata"]["titles"][0]["title"]
    print(f"{s:.3f} | {title}")
```

## Known Issues / Bugs

| # | File | Line | Issue |
|---|------|------|-------|
| 1 | `inspirehep_tools.py` | 255 | `fuzz` undefined — needs `from thefuzz import fuzz` |
| 2 | `inspirehep_tools.py` | 289 | `nx` undefined — needs `import networkx as nx` |
| 3 | `inspirehep_tools.py` | 419 | `client` undefined in `inspirehep_bfs_literature` (non-batched) |
| 4 | `pipe_usage.py` | 110 | Module-level code references undefined `wrapper`, crashes on import |
| 5 | `pyproject.toml` | 8 | Missing deps: `pipe`, `numpy`, `faiss`, `FlagEmbedding`, `openai`, `langchain-openai`, `langchain-core`, `networkx`, `thefuzz` |
| 6 | `__init__.py` | 1 | Only exports `inspirehep_tools`; `latex_tools` etc. not exported |
| 7 | `inspirehep_tools.py` | 72 | `calls` may be empty — no error handling for API failures |
| 8 | `latex_tools.py` | 163-164 | `get_maintext` re-parses cleaned text, losing original positions |
| 9 | `latex_tools.py` | 156 | `get_sections` missing the last section (no end bound) |
