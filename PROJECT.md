# Paper Tools

## Goal
Automate tedious aspects of academic paper writing via programmatic tooling. Provides APIs for:
- Querying InspireHEP for literature metadata, BibTeX, citation graphs
- Processing LaTeX documents (parse, extract sections/paragraphs, validate)
- LMDB-backed persistent storage for InspireHEP records and embeddings
- Semantic search over abstracts using FAISS embeddings

## Next Steps
- Fix identified bugs (missing imports, undefined variables, broken module-level code)
- Complete dependency listing in pyproject.toml
- Write comprehensive test suite
- Extend LaTeX tools with citation extraction, reference validation, spell-checking hooks
- Add arXiv API support alongside InspireHEP
- Develop opencode skills/tools wrapping the codebase for AI-agent usage
