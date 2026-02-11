"""
LangFlow Custom Component: RAG Retriever
Performs parallel searches and aggregates results
"""

from typing import List, Dict, Optional
from langflow.custom import Component
from langflow.io import MessageTextInput, Output, StrInput, IntInput
from langflow.schema import Data
import asyncio
import logging
import hashlib

logger = logging.getLogger(__name__)


class RAGRetrieverComponent(Component):
    """
    Custom LangFlow component for RAG retrieval.
    
    Performs vector similarity search and optional web search,
    merges results, and manages context window.
    """
    
    display_name = "RAG Retriever"
    description = "Retrieves relevant context using vector search and web search"
    icon = "search"
    
    inputs = [
        MessageTextInput(
            name="query",
            display_name="Query",
            info="Search query to retrieve context for",
            required=True
        ),
        StrInput(
            name="chromadb_path",
            display_name="ChromaDB Path",
            info="Path to ChromaDB collection",
            required=True
        ),
        StrInput(
            name="collection_name",
            display_name="Collection Name",
            info="ChromaDB collection name",
            value="loan_documents",
            advanced=True
        ),
        IntInput(
            name="top_k",
            display_name="Top K Results",
            info="Number of results to retrieve",
            value=5,
            advanced=True
        ),
        IntInput(
            name="max_tokens",
            display_name="Max Context Tokens",
            info="Maximum tokens for context window",
            value=4000,
            advanced=True
        ),
        StrInput(
            name="serp_api_key",
            display_name="SERP API Key",
            info="API key for web search (optional)",
            password=True,
            advanced=True
        ),
        StrInput(
            name="db_path",
            display_name="Database Path",
            info="Path to SQLite database for caching",
            advanced=True
        )
    ]
    
    outputs = [
        Output(
            name="context",
            display_name="Retrieved Context",
            method="retrieve_context"
        ),
        Output(
            name="sources",
            display_name="Source Documents",
            method="get_sources"
        ),
        Output(
            name="retrieval_data",
            display_name="Retrieval Metadata",
            method="get_retrieval_data"
        )
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._context = ""
        self._sources = []
        self._metadata = {}
    
    async def retrieve_context_async(self) -> str:
        """Perform retrieval asynchronously."""
        try:
            # Check cache first
            from_cache = False
            if self.db_path:
                cached_result = await self._check_cache()
                if cached_result:
                    self._context = cached_result["context"]
                    self._sources = cached_result["sources"]
                    from_cache = True
                    logger.info("Retrieved context from cache")
                    return self._context
            
            # Parallel search tasks
            tasks = []
            
            # Task 1: Vector search
            tasks.append(self._vector_search())
            
            # Task 2: Web search (if API key provided)
            if self.serp_api_key:
                tasks.append(self._web_search())
            
            # Execute searches in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            vector_results = results[0] if len(results) > 0 and not isinstance(results[0], Exception) else []
            web_results = results[1] if len(results) > 1 and not isinstance(results[1], Exception) else []
            
            # Merge and deduplicate
            merged_results = self._merge_results(vector_results, web_results)
            
            # Build context within token limit
            self._context = self._build_context(merged_results)
            self._sources = self._extract_sources(merged_results)
            
            # Cache results
            if self.db_path:
                await self._cache_results()
            
            logger.info(
                f"Retrieved context: {len(self._context)} chars, "
                f"{len(self._sources)} sources"
            )
            
            return self._context
            
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            self._context = ""
            self._sources = []
            return ""
    
    async def _vector_search(self) -> List[Dict]:
        """Perform vector similarity search."""
        try:
            import chromadb
            
            # Initialize ChromaDB
            client = chromadb.PersistentClient(path=self.chromadb_path)
            collection = client.get_collection(name=self.collection_name)
            
            # Query
            results = collection.query(
                query_texts=[self.query],
                n_results=self.top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted = []
            if results and results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    formatted.append({
                        "text": doc,
                        "source": results["metadatas"][0][i].get("source", "unknown"),
                        "score": 1.0 - results["distances"][0][i],  # Convert distance to similarity
                        "type": "vector"
                    })
            
            logger.info(f"Vector search returned {len(formatted)} results")
            return formatted
            
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []
    
    async def _web_search(self) -> List[Dict]:
        """Perform web search using SERP API."""
        try:
            import aiohttp
            
            url = "https://serpapi.com/search"
            params = {
                "q": self.query,
                "api_key": self.serp_api_key,
                "num": 3,  # Limit web results
                "engine": "google"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract organic results
                        results = []
                        for item in data.get("organic_results", [])[:3]:
                            results.append({
                                "text": f"{item.get('title', '')}\n{item.get('snippet', '')}",
                                "source": item.get("link", ""),
                                "score": 0.8,  # Default score for web results
                                "type": "web"
                            })
                        
                        logger.info(f"Web search returned {len(results)} results")
                        return results
            
            return []
            
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return []
    
    def _merge_results(
        self,
        vector_results: List[Dict],
        web_results: List[Dict]
    ) -> List[Dict]:
        """Merge and deduplicate results."""
        all_results = vector_results + web_results
        
        # Sort by score
        all_results.sort(key=lambda x: x["score"], reverse=True)
        
        # Deduplicate by content similarity
        unique_results = []
        seen_hashes = set()
        
        for result in all_results:
            # Simple deduplication by text hash
            text_hash = hashlib.md5(result["text"].encode()).hexdigest()
            
            if text_hash not in seen_hashes:
                seen_hashes.add(text_hash)
                unique_results.append(result)
        
        return unique_results
    
    def _build_context(self, results: List[Dict]) -> str:
        """Build context string within token limit."""
        context_parts = []
        total_tokens = 0
        
        for i, result in enumerate(results):
            # Estimate tokens (1 token ≈ 4 chars)
            result_tokens = len(result["text"]) // 4
            
            if total_tokens + result_tokens > self.max_tokens:
                break
            
            # Format with source attribution
            source_label = f"[{i+1}]"
            context_parts.append(f"{source_label} {result['text']}")
            total_tokens += result_tokens
        
        return "\n\n".join(context_parts)
    
    def _extract_sources(self, results: List[Dict]) -> List[str]:
        """Extract source URLs/references."""
        sources = []
        for result in results:
            if result["source"] not in sources:
                sources.append(result["source"])
        return sources
    
    async def _check_cache(self) -> Optional[Dict]:
        """Check if results are cached."""
        try:
            from database.db_manager import DatabaseManager
            
            db = DatabaseManager(self.db_path)
            cached = db.get_cached_search(self.query, "rag")
            db.close()
            
            if cached:
                return {
                    "context": cached[0].get("context", ""),
                    "sources": cached[0].get("sources", [])
                }
        except Exception as e:
            logger.error(f"Cache check error: {e}")
        
        return None
    
    async def _cache_results(self):
        """Cache retrieval results."""
        try:
            from database.db_manager import DatabaseManager
            
            db = DatabaseManager(self.db_path)
            db.cache_search_results(
                query=self.query,
                search_type="rag",
                results=[{
                    "context": self._context,
                    "sources": self._sources
                }],
                ttl_seconds=3600  # 1 hour
            )
            db.close()
        except Exception as e:
            logger.error(f"Cache save error: {e}")
    
    def retrieve_context(self) -> str:
        """Main output: retrieved context."""
        return asyncio.run(self.retrieve_context_async())
    
    def get_sources(self) -> List[str]:
        """Output: source documents."""
        return self._sources
    
    def get_retrieval_data(self) -> Data:
        """Output: complete retrieval metadata."""
        return Data(
            data={
                "query": self.query,
                "context_length": len(self._context),
                "num_sources": len(self._sources),
                "sources": self._sources,
                "token_estimate": len(self._context) // 4
            }
        )
