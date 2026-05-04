# paper-tools: OpenCode Skill File

Use this skill when working with academic literature automation — querying InspireHEP, processing LaTeX documents, managing local citation databases, running semantic searches, or performing citation graph analytics.

---

## Overview

`paper-tools` is a Python library (`paper_tools` package) for automating paper-writing tasks:
- **InspireHEP API client** — literature queries, BibTeX retrieval, citation graph traversal (with rate limiting)
- **LMDB-backed databases** — persistent local storage of InspireHEP records, BibTeX entries, and embeddings (msgpack-serialized)
- **LaTeX processing** — parse, extract sections/paragraphs, validate well-formedness, strip comments/preamble
- **Faiss semantic search** — embed and search paper abstracts with `BAAI/bge-large-en-v1.5`
- **Pipe operators** — filter, sort, and transform record collections with functional pipeline syntax
- **Citation analytics** — build citation graphs and compute PageRank on record collections

---

## Module Reference

### 1. `paper_tools.inspirehep_tools` — InspireHEP Integration

All imports from this module: `"InspireHEPClient"`, `"InspireHEPDatabase"`, `"InspireHEPRecordLmdbWrapper"`, `"InspireHEPBibtexLmdbWrapper"`, `"EmbeddingLmdbWrapper"`, `"RateLimitedRequests"`, `"reference_ids"`, `"inspirehep_bfs_literature_batch"`.

#### `InspireHEPClient` — API client with rate limiting

```python
from paper_tools.inspirehep_tools import InspireHEPClient

client = InspireHEPClient()

# Single record
record = client.get_literature("1234567")           # → dict (InspireHEP JSON)

# Batched records (max 50 per call)
records = client.get_literature_batched(["id1","id2"])  # → dict[str, dict]

# Resolve BibTeX keys to IDs
id_map = client.get_id_by_texkey(["PhysRevLett.116.061102"])  # → dict[str, str]

# Find papers by author BAI
paper_ids = client.get_id_by_author("A.Einstein.1")  # → list[str]

# BibTeX entry
bibtex = client.get_bibtex("1234567")               # → str

# All citations to a paper (paginated)
citing_ids = client.all_cites_to("1234567")         # → list[str]

# Batch citation lookup (paginated, max 50 pages / 10000 results)
citing_ids = client.all_cites_to_batched(["id1","id2"])  # → list[str]

# Raw search
response = client.search("black holes")             # → requests.Response
```

#### `InspireHEPDatabase` — Local LMDB storage with semantic search

```python
from paper_tools.config import get_data_dir
from paper_tools.inspirehep_tools import InspireHEPDatabase

db = InspireHEPDatabase(str(get_data_dir()), readonly=True)

# Dict-like access
record = db.record["1234567"]      # → dict (msgpack-deserialized)
bibtex = db.bibtex["1234567"]      # → str
"1234567" in db.record             # → bool
for rec_id in db.record: ...       # iterate all keys

# Semantic search (Faiss)
db.load_model()                    # loads BAAI/bge-large-en-v1.5
db.update_embedding()              # build/refresh embeddings from records
db.index_embeddings()              # build Faiss index
scores, ids = db.search_abstract(["black hole perturbations"], k=10)
# scores: np.ndarray, ids: list[list[str]]

# Init with model loaded
db = InspireHEPDatabase(str(get_data_dir()), readonly=False, init_model=True)
```

#### LMDB Wrappers

```python
from paper_tools.inspirehep_tools import (
    InspireHEPRecordLmdbWrapper,  # dict ↔ msgpack
    InspireHEPBibtexLmdbWrapper,  # str ↔ bytes
    EmbeddingLmdbWrapper,         # np.ndarray(dtype=float16) ↔ bytes
)
from paper_tools.lmdb_wrapper import LmdbWrapperBase

# All support: __getitem__, __setitem__, __iter__, __contains__, __len__,
#   keys(), values(), items(), setitem_batched(), context manager
```

#### BFS Literature Download

```python
from paper_tools.inspirehep_tools import inspirehep_bfs_literature_batch

collection = {}
inspirehep_bfs_literature_batch(collection, roots=["1234567"], max_size=100, mode="refs")
# mode: "refs" (follow references), "cites" (follow citations), "both"
```

#### `reference_ids(record: dict) -> list[str]`
Extracts referenced InspireHEP IDs from a record's `metadata.references`.

---

### 2. `paper_tools.latex_tools` — LaTeX Processing

Core class: `LatexSnippet(text: str)`

Uses `pylatexenc` for parsing. Visitor pattern for extracting intervals.

```python
from paper_tools.latex_tools import (
    LatexSnippet, is_latex_well_formed, extract_sections,
    split_to_paragraphs, extract_latex, extract_head_lines, filter_empty
)

snippet = LatexSnippet(latex_string)

snippet.is_well_formed()       # → bool
snippet.comments_removed()     # → str — % comments stripped
snippet.nontext_removed()      # → str — preamble macros stripped
snippet.get_maintext()         # → str — comments + preamble removed
snippet.get_paragraphs()       # → list[str] — paragraphs with comments stripped
snippet.get_sections()         # → list[str] — text between \section commands

# Low-level interval querying
intervals = snippet.get_intervals(CommentVisitor, reverse=True)
subtexts = snippet.get_split_subtext(intervals)
```

**`is_well_formed()` limitation:**
- Returns `True` for unclosed environments (pylatexenc limitation)

---

### 3. `paper_tools.pipe_usage` — Query Pipeline Operators

Functional pipe operators for filtering/sorting/transforming record collections from `db.record.items()` or `collection.items()`.

```python
import pipe
from paper_tools.pipe_usage import (
    get_id, get_title, get_type, get_authors, get_citation_count,
    get_abstract, get_keywords,
    filter_by_year, filter_after, filter_before,
    filter_by_author, filter_by_title, filter_by_abstract,
    sort_by_citations, extract_fields, as_list, print_all,
)

# Example:
results = list(collection.items()
    | filter_by_abstract('quasinormal mode')
    | sort_by_citations()
    | pipe.take(5)
    | get_title
)
```

---

### 4. `paper_tools.analytic` — Citation Graph Analytics

```python
from paper_tools.analytic import InspireHEPAnalytics

analytics = InspireHEPAnalytics(collection)  # collection = dict[str, record]

graph = analytics.make_citation_graph()         # → dict[str, list[str]]
pagerank = analytics.compute_pagerank(alpha=0.85, max_iter=100)  # → dict[str, float]
```

Uses `networkx.DiGraph` internally. Only tracks papers present in the input collection.

---

### 5. `paper_tools.lmdb_wrapper` — Generic LMDB Base Class

```python
from paper_tools.lmdb_wrapper import LmdbWrapperBase

class MyWrapper(LmdbWrapperBase):
    def pack_value(self, value):
        return msgpack.packb(value)
    def unpack_value(self, value):
        return msgpack.unpackb(value)

db = MyWrapper("/path/to/db.lmdb", map_size=10737418240, readonly=False)
db["key"] = value                    # set
v = db["key"]                        # get (KeyError if missing)
"key" in db                          # check
len(db)                              # count
list(db) / db.keys()                 # iterate keys
list(db.values())                    # iterate values
list(db.items())                     # iterate key-value pairs
db.setitem_batched({"k1": v1, ...})  # batch write
```

---

### 6. `paper_tools.config` — Configuration

```python
from paper_tools.config import get_data_dir

path = get_data_dir()  # → pathlib.Path
# Resolves: env var PAPER_TOOLS_DATA_PATH > OS user data dir (appdirs)
# Creates directory if it doesn't exist
```

---

## Common Workflows

### Find papers citing a known paper, store locally

```python
from paper_tools.inspirehep_tools import InspireHEPClient, InspireHEPDatabase
from paper_tools.config import get_data_dir

client = InspireHEPClient()
citing_ids = client.all_cites_to("1234567")
records = client.get_literature_batched(citing_ids)

db = InspireHEPDatabase(str(get_data_dir()), readonly=False)
for rec_id, rec in records.items():
    db.record[rec_id] = rec
```

### Validate and clean a LaTeX paper

```python
from paper_tools.latex_tools import LatexSnippet

with open("paper.tex") as f:
    tex = f.read()

snip = LatexSnippet(tex)
if not snip.is_well_formed():
    print("Warning: LaTeX has parse issues")

main_text = snip.get_maintext()
paragraphs = snip.get_paragraphs()
```

### Semantic literature search

```python
db = InspireHEPDatabase(str(get_data_dir()), init_model=True)
db.update_embedding()  # only needed if records changed
db.index_embeddings()
scores, paper_ids = db.search_abstract(["gravitational wave black hole merger"], k=20)
for s, pid in zip(scores[0], paper_ids[0]):
    title = db.record[pid]["metadata"]["titles"][0]["title"]
    print(f"{s:.3f} | {title}")
```

### Citation graph analytics

```python
from paper_tools.analytic import InspireHEPAnalytics

analytics = InspireHEPAnalytics(collection)
pagerank = analytics.compute_pagerank()
top = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)[:10]
for pid, score in top:
    title = collection[pid]["metadata"]["titles"][0]["title"]
    print(f"{score:.4f} | {title}")
```

---

## Known Issues

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| 1 | `inspirehep_tools.py` | 200–231 | `all_cites_to_batched` limited to 50 pages (10000 results) due to InspireHEP pagination limit. Highly-cited papers may be truncated. |
| 2 | `get_bibtex_batched` | 141-148 | Now returns ``Dict[str, str]`` (ID → bibtex citation) rather than ``List[str]``. Callers that join results as flat strings need adjustment. |

---

## Installation

```bash
cd /root/Agents/Paper/Code
pip install -e .
```

```
