"""RAG pipeline: vector search + optional web and LinkedIn search.

This module wires up parallel searches and context aggregation.
"""
from typing import List, Dict, Any
import asyncio


async def web_search(query: str) -> List[Dict[str, Any]]:
    # Placeholder for a web search. Replace with bing/google/custom search providers.
    await asyncio.sleep(0.01)
    return [{"source": "web", "snippet": f"Result for {query}"}]


async def linkedin_search(query: str) -> List[Dict[str, Any]]:
    # Placeholder for a LinkedIn search. Replace with scraping/API logic (observe ToS!).
    await asyncio.sleep(0.01)
    return [{"source": "linkedin", "snippet": f"LinkedIn result for {query}"}]


async def run_rag(query: str, vector_store, embedding_fn, top_k: int = 5, use_web: bool = False, use_linkedin: bool = False):
    """Run parallel searches: vector DB + optional web + optional LinkedIn.

    Returns aggregated list of context items.
    """
    # compute query embedding (embedding_fn may be sync or async)
    if asyncio.iscoroutinefunction(embedding_fn):
        q_emb = await embedding_fn([query])
    else:
        q_emb = embedding_fn([query])
    # the embedding function returns list of embeddings for now
    q_emb = q_emb[0]

    # run vector search and optional web/linkedin in parallel
    tasks = [asyncio.to_thread(vector_store.search, q_emb, top_k)]
    if use_web:
        tasks.append(web_search(query))
    if use_linkedin:
        tasks.append(linkedin_search(query))

    results = await asyncio.gather(*tasks)

    # first entry is vector results
    vector_results = results[0]
    other = []
    if use_web:
        other.extend(results[1 if not use_linkedin else 1:2])
    if use_linkedin:
        # careful with indexes
        if use_web:
            other.extend(results[2:3])
        else:
            other.extend(results[1:2])

    # flatten and normalize
    aggregated = []
    for v in vector_results:
        aggregated.append({"source": "vector", "score": v.get("score"), "metadata": v.get("metadata")})
    for o in other:
        aggregated.extend(o if isinstance(o, list) else [o])

    return aggregated
