# paper-tools

A Python library for automating tedious aspects of academic paper writing.

- Query [InspireHEP](https://inspirehep.net) for literature metadata, BibTeX, and citation graphs
- Process LaTeX documents (parse, extract sections/paragraphs, validate)
- LMDB-backed persistent local storage for records, BibTeX, and embeddings
- Semantic search over abstracts via Faiss + BAAI/bge-large-en-v1.5
- Functional pipe operators for filtering, sorting, and transforming record collections
- Citation graph construction and PageRank analytics

## Installation

```bash
pip install -e .
```

## Modules

| Module | Purpose |
|--------|---------|
| `paper_tools.inspirehep_tools` | InspireHEP API client (rate-limited), LMDB record/bibtex/embedding wrappers, database manager, BFS literature downloader |
| `paper_tools.latex_tools` | LaTeX parsing (pylatexenc), comment/preamble removal, section/paragraph extraction, well-formedness check |
| `paper_tools.lmdb_wrapper` | Generic LMDB dict-like base class with customizable serialization |
| `paper_tools.pipe_usage` | Functional pipe operators for filtering/sorting/transforming record collections |
| `paper_tools.analytic` | Citation graph construction and PageRank over InspireHEP collections |
| `paper_tools.config` | OS-appropriate data directory resolution |

## Quick Example

```python
from paper_tools.inspirehep_tools import InspireHEPClient, InspireHEPDatabase
from paper_tools.config import get_data_dir

client = InspireHEPClient()
record = client.get_literature("451647")
bibtex = client.get_bibtex("451647")

db = InspireHEPDatabase(str(get_data_dir()), readonly=False)
db.record["451647"] = record

# Semantic search
db.load_model()
db.index_embeddings()
scores, ids = db.search_abstract(["black hole perturbations"], k=10)
```

For the full API reference, workflows, and known issues, see **[AGENTS_GUIDE.md](AGENTS_GUIDE.md)**.

## License

MIT — see `LICENSE`.
