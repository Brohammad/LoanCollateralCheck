"""
Unit tests for cost tracker
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

from cost_analysis.tracker import CostTracker
from cost_analysis.models import ModelType, RequestType


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_costs.db"
        yield str(db_path)


@pytest.fixture
def tracker(temp_db):
    """Create cost tracker instance"""
    return CostTracker(db_path=temp_db)


class TestCostTracker:
    """Test CostTracker functionality"""
    
    def test_initialization(self, tracker):
        """Test tracker initialization"""
        assert tracker is not None
        assert os.path.exists(tracker.db_path)
    
    def test_track_usage_basic(self, tracker):
        """Test basic usage tracking"""
        record = tracker.track_usage(
            model=ModelType.GEMINI_2_FLASH,
            request_type=RequestType.GENERATION,
            input_tokens=100,
            output_tokens=50,
        )
        
        assert record is not None
        assert record.usage.model == ModelType.GEMINI_2_FLASH
        assert record.usage.request_type == RequestType.GENERATION
        assert record.usage.input_tokens == 100
        assert record.usage.output_tokens == 50
        assert record.usage.total_tokens == 150
        assert record.total_cost == 0.0  # Free during preview
    
    def test_track_usage_with_user(self, tracker):
        """Test tracking with user information"""
        record = tracker.track_usage(
            model=ModelType.GEMINI_15_PRO,
            request_type=RequestType.GENERATION,
            input_tokens=1000,
            output_tokens=500,
            user_id="user123",
            session_id="session456",
        )
        
        assert record.user_id == "user123"
        assert record.session_id == "session456"
        assert record.total_cost > 0  # Should have cost
    
    def test_track_usage_with_metadata(self, tracker):
        """Test tracking with metadata"""
        metadata = {
            "agent": "planner",
            "task": "create_plan",
            "priority": "high",
        }
        
        record = tracker.track_usage(
            model=ModelType.GEMINI_15_FLASH,
            request_type=RequestType.CLASSIFICATION,
            input_tokens=200,
            output_tokens=50,
            metadata=metadata,
        )
        
        assert record.metadata == metadata
    
    def test_get_usage_summary_empty(self, tracker):
        """Test getting summary with no data"""
        summary = tracker.get_usage_summary()
        
        assert summary.total_requests == 0
        assert summary.total_tokens == 0
        assert summary.total_cost == 0.0
    
    def test_get_usage_summary_with_data(self, tracker):
        """Test getting summary with tracked data"""
        # Track multiple requests
        for i in range(5):
            tracker.track_usage(
                model=ModelType.GEMINI_15_PRO,
                request_type=RequestType.GENERATION,
                input_tokens=1000,
                output_tokens=500,
            )
        
        summary = tracker.get_usage_summary()
        
        assert summary.total_requests == 5
        assert summary.total_tokens == 7500  # (1000 + 500) * 5
        assert summary.total_cost > 0
        assert ModelType.GEMINI_15_PRO in summary.by_model
    
    def test_get_usage_summary_time_filter(self, tracker):
        """Test filtering summary by time"""
        now = datetime.utcnow()
        
        # Track request
        tracker.track_usage(
            model=ModelType.GEMINI_2_FLASH,
            request_type=RequestType.GENERATION,
            input_tokens=100,
            output_tokens=50,
        )
        
        # Get summary for last hour
        summary = tracker.get_usage_summary(
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
        )
        
        assert summary.total_requests == 1
        
        # Get summary for future time range (should be empty)
        summary = tracker.get_usage_summary(
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=2),
        )
        
        assert summary.total_requests == 0
    
    def test_get_usage_summary_user_filter(self, tracker):
        """Test filtering summary by user"""
        # Track for different users
        tracker.track_usage(
            model=ModelType.GEMINI_15_PRO,
            request_type=RequestType.GENERATION,
            input_tokens=1000,
            output_tokens=500,
            user_id="user1",
        )
        
        tracker.track_usage(
            model=ModelType.GEMINI_15_PRO,
            request_type=RequestType.GENERATION,
            input_tokens=1000,
            output_tokens=500,
            user_id="user2",
        )
        
        # Get summary for user1
        summary = tracker.get_usage_summary(user_id="user1")
        assert summary.total_requests == 1
        
        # Get summary for user2
        summary = tracker.get_usage_summary(user_id="user2")
        assert summary.total_requests == 1
        
        # Get summary for all users
        summary = tracker.get_usage_summary()
        assert summary.total_requests == 2
    
    def test_get_usage_summary_model_filter(self, tracker):
        """Test filtering summary by model"""
        # Track for different models
        tracker.track_usage(
            model=ModelType.GEMINI_15_PRO,
            request_type=RequestType.GENERATION,
            input_tokens=1000,
            output_tokens=500,
        )
        
        tracker.track_usage(
            model=ModelType.GEMINI_15_FLASH,
            request_type=RequestType.GENERATION,
            input_tokens=1000,
            output_tokens=500,
        )
        
        # Get summary for Pro
        summary = tracker.get_usage_summary(model=ModelType.GEMINI_15_PRO)
        assert summary.total_requests == 1
        
        # Get summary for Flash
        summary = tracker.get_usage_summary(model=ModelType.GEMINI_15_FLASH)
        assert summary.total_requests == 1
    
    def test_get_recent_requests(self, tracker):
        """Test getting recent requests"""
        # Track multiple requests
        for i in range(10):
            tracker.track_usage(
                model=ModelType.GEMINI_2_FLASH,
                request_type=RequestType.GENERATION,
                input_tokens=100 * (i + 1),
                output_tokens=50 * (i + 1),
            )
        
        # Get 5 most recent
        records = tracker.get_recent_requests(limit=5)
        assert len(records) == 5
        
        # Should be in descending order by timestamp
        for i in range(len(records) - 1):
            assert records[i].usage.timestamp >= records[i + 1].usage.timestamp
    
    def test_get_recent_requests_with_filters(self, tracker):
        """Test getting recent requests with filters"""
        # Track for different users and models
        tracker.track_usage(
            model=ModelType.GEMINI_15_PRO,
            request_type=RequestType.GENERATION,
            input_tokens=1000,
            output_tokens=500,
            user_id="user1",
        )
        
        tracker.track_usage(
            model=ModelType.GEMINI_15_FLASH,
            request_type=RequestType.GENERATION,
            input_tokens=1000,
            output_tokens=500,
            user_id="user2",
        )
        
        # Filter by user
        records = tracker.get_recent_requests(user_id="user1")
        assert len(records) == 1
        assert records[0].user_id == "user1"
        
        # Filter by model
        records = tracker.get_recent_requests(model=ModelType.GEMINI_15_FLASH)
        assert len(records) == 1
        assert records[0].usage.model == ModelType.GEMINI_15_FLASH
    
    def test_get_total_cost(self, tracker):
        """Test getting total cost"""
        # Initially should be 0
        total = tracker.get_total_cost()
        assert total == 0.0
        
        # Track some requests with costs
        for i in range(3):
            tracker.track_usage(
                model=ModelType.GEMINI_15_PRO,
                request_type=RequestType.GENERATION,
                input_tokens=1000,
                output_tokens=500,
            )
        
        # Should have non-zero cost
        total = tracker.get_total_cost()
        assert total > 0
    
    def test_get_total_cost_time_filter(self, tracker):
        """Test total cost with time filter"""
        now = datetime.utcnow()
        
        tracker.track_usage(
            model=ModelType.GEMINI_15_PRO,
            request_type=RequestType.GENERATION,
            input_tokens=1000,
            output_tokens=500,
        )
        
        # Cost within time range
        total = tracker.get_total_cost(
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
        )
        assert total > 0
        
        # Cost outside time range
        total = tracker.get_total_cost(
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=2),
        )
        assert total == 0
    
    def test_cleanup_old_records(self, tracker):
        """Test cleanup of old records"""
        # Track some requests
        for i in range(5):
            tracker.track_usage(
                model=ModelType.GEMINI_2_FLASH,
                request_type=RequestType.GENERATION,
                input_tokens=100,
                output_tokens=50,
            )
        
        # Cleanup (should delete nothing since records are new)
        deleted = tracker.cleanup_old_records(days=90)
        assert deleted == 0
        
        # Verify records still exist
        summary = tracker.get_usage_summary()
        assert summary.total_requests == 5
    
    def test_cost_calculation_gemini_2_flash(self, tracker):
        """Test cost calculation for Gemini 2.0 Flash"""
        record = tracker.track_usage(
            model=ModelType.GEMINI_2_FLASH,
            request_type=RequestType.GENERATION,
            input_tokens=1000,
            output_tokens=500,
        )
        
        # Should be free during preview
        assert record.input_cost == 0.0
        assert record.output_cost == 0.0
        assert record.total_cost == 0.0
    
    def test_cost_calculation_gemini_15_pro(self, tracker):
        """Test cost calculation for Gemini 1.5 Pro"""
        record = tracker.track_usage(
            model=ModelType.GEMINI_15_PRO,
            request_type=RequestType.GENERATION,
            input_tokens=1000000,  # 1M tokens
            output_tokens=1000000,  # 1M tokens
        )
        
        # $1.25 per 1M input, $5.00 per 1M output
        assert record.input_cost == 1.25
        assert record.output_cost == 5.00
        assert record.total_cost == 6.25
    
    def test_cost_calculation_gemini_15_flash(self, tracker):
        """Test cost calculation for Gemini 1.5 Flash"""
        record = tracker.track_usage(
            model=ModelType.GEMINI_15_FLASH,
            request_type=RequestType.GENERATION,
            input_tokens=1000000,  # 1M tokens
            output_tokens=1000000,  # 1M tokens
        )
        
        # $0.075 per 1M input, $0.30 per 1M output
        assert record.input_cost == 0.075
        assert record.output_cost == 0.30
        assert record.total_cost == 0.375
    
    def test_embedding_cost(self, tracker):
        """Test cost calculation for embeddings"""
        record = tracker.track_usage(
            model=ModelType.TEXT_EMBEDDING,
            request_type=RequestType.EMBEDDING,
            input_tokens=1000000,
            output_tokens=0,
        )
        
        # Should be free
        assert record.total_cost == 0.0
    
    def test_concurrent_tracking(self, tracker):
        """Test concurrent tracking (basic thread safety)"""
        import threading
        
        def track_request():
            for _ in range(10):
                tracker.track_usage(
                    model=ModelType.GEMINI_2_FLASH,
                    request_type=RequestType.GENERATION,
                    input_tokens=100,
                    output_tokens=50,
                )
        
        # Create multiple threads
        threads = [threading.Thread(target=track_request) for _ in range(5)]
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Should have 50 requests total
        summary = tracker.get_usage_summary()
        assert summary.total_requests == 50
