"""Retired FAISS upload.

The previous script copied embeddings/faiss.index into Qdrant. Those vectors
belong to a different model and distance. build_index.py embeds with the local
TEI server and uploads the cosine collection directly.
"""

import sys


def main() -> None:
    sys.exit(
        "Refusing to copy faiss.index into Qdrant. "
        "Run python build_index.py to embed with the local TEI server."
    )


if __name__ == "__main__":
    main()
