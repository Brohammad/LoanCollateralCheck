"""Utility script to ingest documents into the vector store.

Usage:
    python scripts/ingest_documents.py --source ./docs --store pinecone
    python scripts/ingest_documents.py --source ./docs --store chroma
    python scripts/ingest_documents.py --source ./docs --store memory
"""
import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.gemini_client import get_gemini_client
from app.vector_store import InMemoryVectorStore, PineconeAdapter, ChromaAdapter


def read_documents(source_path: str):
    """Read all text files from a directory."""
    documents = []
    source = Path(source_path)

    if source.is_file():
        with open(source, "r", encoding="utf-8") as f:
            documents.append({"id": source.name, "text": f.read(), "metadata": {"source": str(source)}})
    elif source.is_dir():
        for file_path in source.rglob("*.txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                documents.append(
                    {"id": str(file_path.relative_to(source)), "text": f.read(), "metadata": {"source": str(file_path)}}
                )
        for file_path in source.rglob("*.md"):
            with open(file_path, "r", encoding="utf-8") as f:
                documents.append(
                    {"id": str(file_path.relative_to(source)), "text": f.read(), "metadata": {"source": str(file_path)}}
                )
    else:
        print(f"Error: {source_path} is not a valid file or directory")
        sys.exit(1)

    return documents


def main():
    parser = argparse.ArgumentParser(description="Ingest documents into vector store")
    parser.add_argument("--source", required=True, help="Path to documents (file or directory)")
    parser.add_argument(
        "--store", choices=["memory", "pinecone", "chroma"], default="memory", help="Vector store type"
    )
    args = parser.parse_args()

    # Initialize vector store
    if args.store == "memory":
        vector_store = InMemoryVectorStore()
        print("Using in-memory vector store")
    elif args.store == "pinecone":
        vector_store = PineconeAdapter()
        print("Using Pinecone vector store")
    elif args.store == "chroma":
        vector_store = ChromaAdapter()
        print("Using Chroma vector store")

    # Read documents
    print(f"Reading documents from {args.source}...")
    documents = read_documents(args.source)
    print(f"Found {len(documents)} documents")

    if not documents:
        print("No documents found!")
        sys.exit(1)

    # Get embeddings
    print("Generating embeddings...")
    client = get_gemini_client()
    texts = [doc["text"] for doc in documents]
    embeddings = client.embed(texts)

    # Add to vector store
    print("Adding to vector store...")
    ids = [doc["id"] for doc in documents]
    metadatas = [doc["metadata"] for doc in documents]
    vector_store.add(ids, embeddings, metadatas)

    print(f"Successfully ingested {len(documents)} documents!")


if __name__ == "__main__":
    main()
