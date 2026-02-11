"""
Example script demonstrating the AI Agent system
Run this after setup to test the system
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config.config_loader import get_config
from database.db_manager import DatabaseManager
from app.gemini_enhanced import GeminiClient
from app.planner_critique import PlannerCritiqueOrchestrator


async def example_1_simple_generation():
    """Example 1: Simple text generation."""
    print("\n" + "="*60)
    print("Example 1: Simple Text Generation")
    print("="*60)
    
    config = get_config()
    
    client = GeminiClient(
        api_key=config.gemini_api_key,
        model_name=config.gemini_model,
        enable_cache=True
    )
    
    response = await client.generate_async(
        prompt="Explain what loan collateral is in 2-3 sentences.",
        temperature=0.7,
        max_tokens=200
    )
    
    print(f"\nResponse: {response.text}")
    print(f"\nTokens: {response.token_usage.total_tokens}")
    print(f"Latency: {response.latency_ms}ms")
    print(f"Cost: ${response.token_usage.estimated_cost:.6f}")
    print(f"From cache: {response.from_cache}")


async def example_2_intent_classification():
    """Example 2: Intent classification."""
    print("\n" + "="*60)
    print("Example 2: Intent Classification")
    print("="*60)
    
    config = get_config()
    
    client = GeminiClient(
        api_key=config.gemini_api_key,
        enable_cache=False
    )
    
    messages = [
        "Hello, how are you?",
        "What is loan collateral?",
        "Calculate the interest rate",
        "Can you clarify what you mean?",
    ]
    
    for message in messages:
        intent, confidence = await client.classify_intent(message)
        print(f"\nMessage: '{message}'")
        print(f"Intent: {intent} (confidence: {confidence:.2f})")


async def example_3_database_operations():
    """Example 3: Database operations."""
    print("\n" + "="*60)
    print("Example 3: Database Operations")
    print("="*60)
    
    config = get_config()
    db = DatabaseManager(config.db_path)
    
    # Create session
    session_id = "example_session_123"
    db.create_session(session_id, "example_user")
    print(f"\n✓ Created session: {session_id}")
    
    # Add conversations
    conv_id = db.add_conversation(
        session_id=session_id,
        user_message="What is collateral?",
        agent_response="Collateral is an asset pledged as security for a loan.",
        intent="question",
        confidence=0.95,
        response_time_ms=1500,
        token_count=45
    )
    print(f"✓ Added conversation (ID: {conv_id})")
    
    # Get conversation context
    context = db.get_conversation_context(session_id, max_tokens=1000)
    print(f"✓ Retrieved context: {len(context)} characters")
    
    # Store additional context
    db.store_context(
        session_id=session_id,
        context_type="user_preference",
        context_key="language",
        context_value="English",
        relevance_score=1.0
    )
    print("✓ Stored user context")
    
    # Get statistics
    stats = db.get_database_stats()
    print(f"\n📊 Database Statistics:")
    for table, count in stats.items():
        print(f"   {table}: {count} rows")
    
    db.close()


async def example_4_planner_critique():
    """Example 4: Planner-critique loop."""
    print("\n" + "="*60)
    print("Example 4: Planner-Critique Loop")
    print("="*60)
    
    config = get_config()
    db = DatabaseManager(config.db_path)
    
    client = GeminiClient(
        api_key=config.gemini_api_key,
        enable_cache=False,
        db_manager=db
    )
    
    orchestrator = PlannerCritiqueOrchestrator(
        gemini_client=client,
        max_iterations=config.max_critique_iterations,
        acceptance_threshold=config.critique_threshold,
        db_manager=db
    )
    
    query = "What are the different types of loan collateral?"
    context = """
    Common types of loan collateral include:
    1. Real Estate: Property such as homes or land
    2. Vehicles: Cars, trucks, or other vehicles
    3. Cash Deposits: Savings accounts or CDs
    4. Inventory: Business inventory or equipment
    5. Securities: Stocks, bonds, or mutual funds
    """
    
    print(f"\nQuery: {query}")
    print(f"Context provided: {len(context)} characters")
    print("\nRunning planner-critique loop...")
    
    result = await orchestrator.run(
        query=query,
        context=context
    )
    
    print(f"\n📊 Results:")
    print(f"   Total iterations: {result.total_iterations}")
    print(f"   Final score: {result.final_score:.2f}")
    print(f"   Approved: {result.approved}")
    print(f"   Total time: {result.total_time_ms}ms")
    print(f"   Total tokens: {result.total_tokens}")
    
    print(f"\n💬 Final Response:")
    print(f"{result.final_response}")
    
    print(f"\n📝 Iteration Details:")
    for iteration in result.iterations:
        print(f"\n   Iteration {iteration.iteration}:")
        print(f"      Score: {iteration.critique_score:.2f}")
        print(f"      Accuracy: {iteration.accuracy:.2f}")
        print(f"      Completeness: {iteration.completeness:.2f}")
        print(f"      Clarity: {iteration.clarity:.2f}")
        print(f"      Approved: {iteration.approved}")
        if iteration.feedback:
            print(f"      Feedback: {iteration.feedback[:100]}...")
    
    db.close()


async def example_5_caching_performance():
    """Example 5: Demonstrate caching benefits."""
    print("\n" + "="*60)
    print("Example 5: Caching Performance")
    print("="*60)
    
    config = get_config()
    db = DatabaseManager(config.db_path)
    
    client = GeminiClient(
        api_key=config.gemini_api_key,
        enable_cache=True,
        db_manager=db
    )
    
    prompt = "What is the purpose of loan collateral?"
    
    # First call (no cache)
    print("\n🔍 First call (no cache)...")
    response1 = await client.generate_async(
        prompt=prompt,
        temperature=0.7,
        max_tokens=100
    )
    print(f"   Latency: {response1.latency_ms}ms")
    print(f"   From cache: {response1.from_cache}")
    
    # Second call (should hit cache)
    print("\n🔍 Second call (should hit cache)...")
    response2 = await client.generate_async(
        prompt=prompt,
        temperature=0.7,
        max_tokens=100
    )
    print(f"   Latency: {response2.latency_ms}ms")
    print(f"   From cache: {response2.from_cache}")
    
    # Show statistics
    stats = client.get_statistics()
    print(f"\n📊 Client Statistics:")
    print(f"   Total requests: {stats['total_requests']}")
    print(f"   Total tokens: {stats['total_tokens']}")
    print(f"   Cache hits: {stats['cache_hits']}")
    print(f"   Cache hit rate: {stats['cache_hit_rate']:.1%}")
    
    db.close()


async def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("AI Agent System - Examples")
    print("="*60)
    
    try:
        # Load configuration
        config = get_config()
        
        print("\n✓ Configuration loaded")
        print(f"   Model: {config.gemini_model}")
        print(f"   Database: {config.db_path}")
        print(f"   Max iterations: {config.max_critique_iterations}")
        print(f"   Acceptance threshold: {config.critique_threshold}")
        
        # Check API key
        if config.gemini_api_key == "your_gemini_api_key_here":
            print("\n❌ ERROR: GEMINI_API_KEY not configured")
            print("   Please update .env with your actual API key")
            return
        
        # Run examples
        examples = [
            ("1", example_1_simple_generation),
            ("2", example_2_intent_classification),
            ("3", example_3_database_operations),
            ("4", example_4_planner_critique),
            ("5", example_5_caching_performance),
        ]
        
        print("\nAvailable examples:")
        for num, func in examples:
            print(f"   {num}. {func.__doc__.split('.')[0]}")
        print("   all. Run all examples")
        print("   q. Quit")
        
        choice = input("\nSelect example (or 'all'): ").strip().lower()
        
        if choice == 'q':
            return
        
        if choice == 'all':
            for num, func in examples:
                await func()
                await asyncio.sleep(1)  # Brief pause between examples
        else:
            for num, func in examples:
                if choice == num:
                    await func()
                    break
            else:
                print("Invalid choice")
        
        print("\n" + "="*60)
        print("Examples completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
