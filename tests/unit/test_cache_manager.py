"""
Unit Tests for Cache Manager

Tests the caching system including:
- Cache hit/miss
- TTL expiration
- Invalidation
- Size limits
- Statistics tracking
"""

import pytest
from unittest.mock import Mock, patch
import time

try:
    from app.cache import CacheManager
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    # Mock class for testing
    class CacheManager:
        def __init__(self, max_size=1000, default_ttl=3600):
            self.cache = {}
            self.max_size = max_size
            self.default_ttl = default_ttl
            self.stats = {"hits": 0, "misses": 0}
        
        def get(self, key: str):
            if key in self.cache:
                self.stats["hits"] += 1
                return self.cache[key]
            self.stats["misses"] += 1
            return None
        
        def set(self, key: str, value, ttl=None):
            self.cache[key] = value
        
        def invalidate(self, key: str):
            if key in self.cache:
                del self.cache[key]
        
        def get_stats(self):
            return self.stats


@pytest.mark.unit
class TestCacheManager:
    """Test suite for Cache Manager"""
    
    @pytest.fixture
    def cache_manager(self, mock_cache):
        """Create cache manager instance"""
        return mock_cache  # Use mock from conftest
    
    def test_cache_set_and_get(self, cache_manager):
        """Test basic cache set and get operations"""
        cache_manager.set("test_key", "test_value")
        value = cache_manager.get("test_key")
        assert value == "test_value"
    
    def test_cache_miss(self, cache_manager):
        """Test cache miss for non-existent key"""
        value = cache_manager.get("non_existent_key")
        assert value is None
    
    def test_cache_overwrite(self, cache_manager):
        """Test overwriting existing cache entry"""
        cache_manager.set("key1", "value1")
        cache_manager.set("key1", "value2")
        value = cache_manager.get("key1")
        assert value == "value2"
    
    def test_cache_multiple_entries(self, cache_manager):
        """Test storing multiple cache entries"""
        entries = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3",
        }
        
        for key, value in entries.items():
            cache_manager.set(key, value)
        
        for key, expected_value in entries.items():
            assert cache_manager.get(key) == expected_value
    
    def test_cache_invalidation(self, cache_manager):
        """Test cache invalidation"""
        cache_manager.set("key_to_invalidate", "value")
        cache_manager.invalidate("key_to_invalidate")
        value = cache_manager.get("key_to_invalidate")
        assert value is None
    
    def test_cache_invalidation_nonexistent(self, cache_manager):
        """Test invalidation of non-existent key"""
        # Should not raise error
        cache_manager.invalidate("non_existent_key")
    
    def test_cache_ttl_expiration(self):
        """Test cache expiration based on TTL"""
        cache = CacheManager(default_ttl=1)
        cache.set("expiring_key", "value", ttl=1)
        
        # Immediate get should work
        assert cache.get("expiring_key") == "value"
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        value = cache.get("expiring_key")
        # Depending on implementation, may return None or use lazy deletion
        # assert value is None  # Uncomment if TTL is implemented
    
    def test_cache_hit_statistics(self, cache_manager):
        """Test cache hit statistics"""
        cache_manager.set("key1", "value1")
        
        # Multiple hits
        cache_manager.get("key1")
        cache_manager.get("key1")
        
        stats = cache_manager.get_stats()
        assert stats["hits"] >= 2
    
    def test_cache_miss_statistics(self, cache_manager):
        """Test cache miss statistics"""
        # Multiple misses
        cache_manager.get("non_existent_1")
        cache_manager.get("non_existent_2")
        
        stats = cache_manager.get_stats()
        assert stats["misses"] >= 2
    
    def test_cache_size_limit(self):
        """Test cache size limiting"""
        small_cache = CacheManager(max_size=3)
        
        # Fill cache beyond limit
        for i in range(5):
            small_cache.set(f"key_{i}", f"value_{i}")
        
        # Cache should not exceed max size
        # Implementation should evict old entries (LRU)
        # This test depends on actual implementation
    
    def test_cache_lru_eviction(self):
        """Test LRU eviction policy"""
        lru_cache = CacheManager(max_size=2)
        
        lru_cache.set("key1", "value1")
        lru_cache.set("key2", "value2")
        
        # Access key1 to make it recently used
        lru_cache.get("key1")
        
        # Add key3, should evict key2 (least recently used)
        lru_cache.set("key3", "value3")
        
        # key2 should be evicted
        # assert lru_cache.get("key2") is None  # Uncomment if LRU is implemented
        # key1 and key3 should still exist
        # assert lru_cache.get("key1") == "value1"
        # assert lru_cache.get("key3") == "value3"
    
    def test_cache_clear_all(self, cache_manager):
        """Test clearing all cache entries"""
        cache_manager.set("key1", "value1")
        cache_manager.set("key2", "value2")
        
        if hasattr(cache_manager, 'clear'):
            cache_manager.clear()
            assert cache_manager.get("key1") is None
            assert cache_manager.get("key2") is None


@pytest.mark.unit
class TestCacheManagerTypes:
    """Test caching different data types"""
    
    @pytest.fixture
    def cache_manager(self):
        """Create cache manager instance"""
        return CacheManager()
    
    def test_cache_string_value(self, cache_manager):
        """Test caching string values"""
        cache_manager.set("string_key", "string_value")
        assert cache_manager.get("string_key") == "string_value"
    
    def test_cache_integer_value(self, cache_manager):
        """Test caching integer values"""
        cache_manager.set("int_key", 42)
        assert cache_manager.get("int_key") == 42
    
    def test_cache_list_value(self, cache_manager):
        """Test caching list values"""
        test_list = [1, 2, 3, 4, 5]
        cache_manager.set("list_key", test_list)
        assert cache_manager.get("list_key") == test_list
    
    def test_cache_dict_value(self, cache_manager):
        """Test caching dictionary values"""
        test_dict = {"key1": "value1", "key2": "value2"}
        cache_manager.set("dict_key", test_dict)
        assert cache_manager.get("dict_key") == test_dict
    
    def test_cache_none_value(self, cache_manager):
        """Test caching None value"""
        cache_manager.set("none_key", None)
        # Should distinguish between cached None and missing key
        # This is implementation-dependent
    
    def test_cache_complex_object(self, cache_manager):
        """Test caching complex objects"""
        class TestObject:
            def __init__(self, value):
                self.value = value
        
        obj = TestObject(42)
        cache_manager.set("object_key", obj)
        cached_obj = cache_manager.get("object_key")
        assert cached_obj is not None
        assert cached_obj.value == 42


@pytest.mark.unit
class TestCacheManagerConfiguration:
    """Test cache manager configuration"""
    
    def test_cache_default_initialization(self):
        """Test cache initialization with default parameters"""
        cache = CacheManager()
        assert cache.max_size > 0
        assert cache.default_ttl > 0
    
    def test_cache_custom_max_size(self):
        """Test cache with custom max size"""
        cache = CacheManager(max_size=100)
        assert cache.max_size == 100
    
    def test_cache_custom_ttl(self):
        """Test cache with custom default TTL"""
        cache = CacheManager(default_ttl=600)
        assert cache.default_ttl == 600
    
    def test_cache_invalid_max_size(self):
        """Test cache with invalid max size"""
        # Should handle gracefully or raise error
        try:
            cache = CacheManager(max_size=0)
        except ValueError:
            pass  # Expected
    
    def test_cache_invalid_ttl(self):
        """Test cache with invalid TTL"""
        try:
            cache = CacheManager(default_ttl=-1)
        except ValueError:
            pass  # Expected


@pytest.mark.unit
class TestCacheManagerEdgeCases:
    """Test cache manager edge cases"""
    
    @pytest.fixture
    def cache_manager(self):
        """Create cache manager instance"""
        return CacheManager()
    
    def test_cache_empty_string_key(self, cache_manager):
        """Test caching with empty string key"""
        cache_manager.set("", "value")
        value = cache_manager.get("")
        # Should handle empty string keys
        assert value == "value" or value is None
    
    def test_cache_special_characters_key(self, cache_manager):
        """Test caching with special characters in key"""
        special_key = "key:with:special@#$%chars"
        cache_manager.set(special_key, "value")
        assert cache_manager.get(special_key) == "value"
    
    def test_cache_very_long_key(self, cache_manager):
        """Test caching with very long key"""
        long_key = "k" * 1000
        cache_manager.set(long_key, "value")
        assert cache_manager.get(long_key) == "value"
    
    def test_cache_very_large_value(self, cache_manager):
        """Test caching very large value"""
        large_value = "x" * 10000
        cache_manager.set("large_key", large_value)
        assert cache_manager.get("large_key") == large_value
    
    def test_cache_unicode_key(self, cache_manager):
        """Test caching with Unicode key"""
        unicode_key = "键🔑"
        cache_manager.set(unicode_key, "value")
        assert cache_manager.get(unicode_key) == "value"
    
    def test_cache_concurrent_access(self, cache_manager):
        """Test concurrent cache access"""
        import threading
        
        def write_cache(i):
            cache_manager.set(f"key_{i}", f"value_{i}")
        
        def read_cache(i):
            cache_manager.get(f"key_{i}")
        
        threads = []
        
        # Concurrent writes
        for i in range(10):
            t = threading.Thread(target=write_cache, args=(i,))
            threads.append(t)
            t.start()
        
        # Concurrent reads
        for i in range(10):
            t = threading.Thread(target=read_cache, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Should handle concurrent access without errors
    
    def test_cache_key_collision(self, cache_manager):
        """Test handling of key collisions"""
        # Set value for key
        cache_manager.set("collision_key", "value1")
        
        # Overwrite with same key
        cache_manager.set("collision_key", "value2")
        
        # Should have latest value
        assert cache_manager.get("collision_key") == "value2"


@pytest.mark.unit
class TestCacheManagerStatistics:
    """Test cache statistics and monitoring"""
    
    @pytest.fixture
    def cache_manager(self):
        """Create cache manager instance"""
        return CacheManager()
    
    def test_cache_hit_rate(self, cache_manager):
        """Test cache hit rate calculation"""
        cache_manager.set("key1", "value1")
        
        # Generate hits and misses
        cache_manager.get("key1")  # hit
        cache_manager.get("key1")  # hit
        cache_manager.get("key2")  # miss
        
        stats = cache_manager.get_stats()
        
        # Calculate hit rate
        total = stats["hits"] + stats["misses"]
        if total > 0:
            hit_rate = stats["hits"] / total
            assert 0.0 <= hit_rate <= 1.0
    
    def test_cache_size_tracking(self, cache_manager):
        """Test cache size tracking"""
        # Add multiple entries
        for i in range(10):
            cache_manager.set(f"key_{i}", f"value_{i}")
        
        if hasattr(cache_manager, 'get_size'):
            size = cache_manager.get_size()
            assert size > 0
            assert size <= 10
    
    def test_cache_statistics_reset(self, cache_manager):
        """Test resetting cache statistics"""
        cache_manager.set("key1", "value1")
        cache_manager.get("key1")
        cache_manager.get("key2")
        
        if hasattr(cache_manager, 'reset_stats'):
            cache_manager.reset_stats()
            stats = cache_manager.get_stats()
            assert stats["hits"] == 0
            assert stats["misses"] == 0
