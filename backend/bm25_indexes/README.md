# BM25 indexes (Other Acts)

Built offline by `../build_bm25_indexes.py`. Live retrieval does not load these yet.

Expected files after a full build:

- `other-acts-en.pkl` / `other-acts-en.meta.json`
- `other-acts-bn.pkl` / `other-acts-bn.meta.json`

Row ids inside each pickle match Qdrant point ids in the active serving collection.
