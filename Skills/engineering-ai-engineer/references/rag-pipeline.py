"""RAG sketch — chunk → embed → store → retrieve → rerank → answer (with citations).

Vector store interface is left abstract; swap for Qdrant/Chroma/pgvector/Pinecone.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol


# ─── Types ────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Doc:
    id: str
    text: str
    metadata: dict


@dataclass(frozen=True)
class Chunk:
    id: str            # "<doc_id>:<chunk_index>"
    doc_id: str
    text: str
    metadata: dict


@dataclass(frozen=True)
class Retrieved:
    chunk: Chunk
    score: float


class VectorStore(Protocol):
    def upsert(self, chunks: Iterable[Chunk], embeddings: list[list[float]]) -> None: ...
    def search(self, query_embedding: list[float], k: int) -> list[Retrieved]: ...


class Embedder(Protocol):
    name: str          # e.g. "openai-text-embedding-3-large"
    version: str       # bump on model change to force re-index
    def embed(self, texts: list[str]) -> list[list[float]]: ...


# ─── Chunking ─────────────────────────────────────────────────────────────
def chunk_document(doc: Doc, *, max_tokens: int = 400, overlap: int = 50) -> list[Chunk]:
    """Token-aware sliding window. Replace with semantic splitter where it helps."""
    tokens = doc.text.split()          # placeholder: use real tokenizer
    chunks: list[Chunk] = []
    i = 0
    while i < len(tokens):
        window = tokens[i:i + max_tokens]
        chunks.append(Chunk(
            id=f"{doc.id}:{len(chunks)}",
            doc_id=doc.id,
            text=" ".join(window),
            metadata=doc.metadata,
        ))
        i += max_tokens - overlap
    return chunks


# ─── Index ────────────────────────────────────────────────────────────────
def index_documents(docs: list[Doc], embedder: Embedder, store: VectorStore) -> None:
    chunks: list[Chunk] = []
    for d in docs:
        chunks.extend(chunk_document(d))
    embeddings = embedder.embed([c.text for c in chunks])
    store.upsert(chunks, embeddings)
    # Persist a manifest: {embedder: name, version, chunked_at, doc_count}
    # so you know when an index is stale relative to its embedder.


# ─── Retrieve + rerank ────────────────────────────────────────────────────
def retrieve(query: str, *, embedder: Embedder, store: VectorStore, k: int = 20) -> list[Retrieved]:
    qv = embedder.embed([query])[0]
    return store.search(qv, k=k)


def rerank_with_llm(query: str, candidates: list[Retrieved], *, top: int = 5) -> list[Retrieved]:
    """Optional: LLM or cross-encoder reranker. Skip when candidates are already strong."""
    return candidates[:top]   # placeholder


# ─── Answer with citations ────────────────────────────────────────────────
def build_prompt(query: str, ctx: list[Retrieved]) -> str:
    sources = "\n\n".join(
        f"[{i+1}] (id={r.chunk.id}) {r.chunk.text}" for i, r in enumerate(ctx)
    )
    return (
        "Answer the user's question using ONLY the numbered sources.\n"
        "Cite sources inline like [1], [2]. If the answer isn't in the sources, say so.\n\n"
        f"Sources:\n{sources}\n\nQuestion: {query}"
    )
