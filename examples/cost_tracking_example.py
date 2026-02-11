"""
Example usage of cost analysis system
"""

import asyncio
from datetime import datetime, timedelta

from cost_analysis.tracker import CostTracker
from cost_analysis.calculator import CostCalculator
from cost_analysis.budget import BudgetManager
from cost_analysis.optimizer import CostOptimizer
from cost_analysis.analytics import CostAnalytics
from cost_analysis.models import ModelType, RequestType, BudgetPeriod


async def basic_tracking_example():
    """Example 1: Basic cost tracking"""
    print("\n=== Basic Cost Tracking ===\n")
    
    tracker = CostTracker()
    
    # Track a simple request
    record = tracker.track_usage(
        model=ModelType.GEMINI_15_PRO,
        request_type=RequestType.GENERATION,
        input_tokens=1000,
        output_tokens=500,
        user_id="user123",
        session_id="session456",
        metadata={"agent": "planner", "task": "create_plan"},
    )
    
    print(f"Request ID: {record.request_id}")
    print(f"Total tokens: {record.usage.total_tokens}")
    print(f"Input cost: ${record.input_cost:.6f}")
    print(f"Output cost: ${record.output_cost:.6f}")
    print(f"Total cost: ${record.total_cost:.6f}")


async def usage_summary_example():
    """Example 2: Get usage summary"""
    print("\n=== Usage Summary ===\n")
    
    tracker = CostTracker()
    
    # Track multiple requests
    models = [ModelType.GEMINI_15_PRO, ModelType.GEMINI_15_FLASH, ModelType.GEMINI_2_FLASH]
    for i in range(10):
        tracker.track_usage(
            model=models[i % len(models)],
            request_type=RequestType.GENERATION,
            input_tokens=1000 * (i + 1),
            output_tokens=500 * (i + 1),
            user_id=f"user{i % 3}",
        )
    
    # Get summary for last 24 hours
    summary = tracker.get_usage_summary(
        start_time=datetime.utcnow() - timedelta(hours=24),
        end_time=datetime.utcnow(),
    )
    
    print(f"Total requests: {summary.total_requests}")
    print(f"Total tokens: {summary.total_tokens:,}")
    print(f"Total cost: ${summary.total_cost:.6f}")
    print(f"\nBy model:")
    for model, stats in summary.by_model.items():
        print(f"  {model}: {stats['count']} requests, ${stats['cost']:.6f}")
    print(f"\nBy user:")
    for user, stats in summary.by_user.items():
        print(f"  {user}: {stats['count']} requests, ${stats['cost']:.6f}")


async def budget_management_example():
    """Example 3: Budget management"""
    print("\n=== Budget Management ===\n")
    
    tracker = CostTracker()
    budget_manager = BudgetManager()
    
    # Create a daily budget
    budget = budget_manager.create_budget(
        name="Daily API Budget",
        period=BudgetPeriod.DAILY,
        limit=10.0,
        warning_threshold=0.8,  # 80%
        critical_threshold=0.95,  # 95%
    )
    
    print(f"Created budget: {budget.name}")
    print(f"Limit: ${budget.limit:.2f}")
    print(f"Period: {budget.period}")
    
    # Simulate some usage
    for i in range(5):
        tracker.track_usage(
            model=ModelType.GEMINI_15_PRO,
            request_type=RequestType.GENERATION,
            input_tokens=200000,
            output_tokens=100000,
        )
    
    # Update budget usage
    updated_budget = budget_manager.update_budget_usage(budget.id, tracker)
    
    print(f"\nCurrent usage: ${updated_budget.current:.6f}")
    print(f"Percentage used: {updated_budget.percentage_used:.1f}%")
    print(f"Remaining: ${updated_budget.limit - updated_budget.current:.6f}")
    
    # Check for alerts
    alerts = budget_manager.get_alerts(budget_id=budget.id)
    if alerts:
        print(f"\nAlerts ({len(alerts)}):")
        for alert in alerts:
            print(f"  - {alert.level}: {alert.message}")


async def user_budget_example():
    """Example 4: Per-user budget"""
    print("\n=== Per-User Budget ===\n")
    
    tracker = CostTracker()
    budget_manager = BudgetManager()
    
    # Create budget for specific user
    budget = budget_manager.create_budget(
        name="John's Monthly Budget",
        period=BudgetPeriod.MONTHLY,
        limit=100.0,
        user_id="john_doe",
    )
    
    # Track usage for different users
    for i in range(3):
        tracker.track_usage(
            model=ModelType.GEMINI_15_PRO,
            request_type=RequestType.GENERATION,
            input_tokens=1000000,
            output_tokens=500000,
            user_id="john_doe",
        )
    
    for i in range(2):
        tracker.track_usage(
            model=ModelType.GEMINI_15_PRO,
            request_type=RequestType.GENERATION,
            input_tokens=1000000,
            output_tokens=500000,
            user_id="jane_smith",
        )
    
    # Update budget (only john's usage counts)
    updated_budget = budget_manager.update_budget_usage(budget.id, tracker)
    
    print(f"Budget for: {updated_budget.user_id}")
    print(f"Usage: ${updated_budget.current:.2f} / ${updated_budget.limit:.2f}")
    print(f"Percentage: {updated_budget.percentage_used:.1f}%")


async def cost_optimization_example():
    """Example 5: Cost optimization recommendations"""
    print("\n=== Cost Optimization ===\n")
    
    tracker = CostTracker()
    optimizer = CostOptimizer()
    
    # Simulate usage pattern
    for i in range(20):
        tracker.track_usage(
            model=ModelType.GEMINI_15_PRO,  # Using expensive model
            request_type=RequestType.GENERATION,
            input_tokens=2000,  # Large context
            output_tokens=1000,
            user_id=f"user{i % 5}",
        )
    
    # Get recent records
    records = tracker.get_recent_requests(limit=100)
    
    # Get optimization recommendations
    recommendations = optimizer.analyze_and_recommend(records)
    
    print(f"Found {len(recommendations)} optimization opportunities:\n")
    for rec in recommendations[:3]:  # Show top 3
        print(f"Type: {rec.optimization_type}")
        print(f"Priority: {rec.priority}")
        print(f"Estimated savings: ${rec.estimated_savings:.2f}/month")
        print(f"Description: {rec.description}")
        print(f"Implementation: {rec.implementation_steps[0]}")
        print()


async def analytics_report_example():
    """Example 6: Comprehensive analytics report"""
    print("\n=== Analytics Report ===\n")
    
    tracker = CostTracker()
    analytics = CostAnalytics(tracker)
    
    # Simulate varied usage
    models = [ModelType.GEMINI_15_PRO, ModelType.GEMINI_15_FLASH, ModelType.GEMINI_2_FLASH]
    users = ["user1", "user2", "user3"]
    
    for i in range(30):
        tracker.track_usage(
            model=models[i % len(models)],
            request_type=RequestType.GENERATION,
            input_tokens=1000 * (i % 5 + 1),
            output_tokens=500 * (i % 5 + 1),
            user_id=users[i % len(users)],
        )
    
    # Generate report
    report = analytics.generate_report(
        start_time=datetime.utcnow() - timedelta(days=7),
        end_time=datetime.utcnow(),
    )
    
    print(f"Period: {report.start_time.date()} to {report.end_time.date()}")
    print(f"\nSummary:")
    print(f"  Total requests: {report.summary.total_requests}")
    print(f"  Total cost: ${report.summary.total_cost:.6f}")
    print(f"  Average cost/request: ${report.summary.average_cost_per_request:.6f}")
    
    print(f"\nTop Users:")
    for user in report.top_users[:3]:
        print(f"  {user['user_id']}: ${user['total_cost']:.6f} ({user['request_count']} requests)")
    
    print(f"\nTop Models:")
    for model in report.top_models[:3]:
        print(f"  {model['model']}: ${model['total_cost']:.6f} ({model['request_count']} requests)")
    
    if report.recommendations:
        print(f"\nRecommendations:")
        for rec in report.recommendations[:2]:
            print(f"  - {rec}")


async def cost_comparison_example():
    """Example 7: Compare model costs"""
    print("\n=== Model Cost Comparison ===\n")
    
    calculator = CostCalculator()
    
    # Compare costs for same workload across models
    input_tokens = 10000
    output_tokens = 5000
    
    print(f"Workload: {input_tokens:,} input + {output_tokens:,} output tokens\n")
    
    comparison = calculator.pricing_model.compare_model_costs(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    
    # Sort by cost
    sorted_models = sorted(comparison.items(), key=lambda x: x[1]["total_cost"])
    
    for model, costs in sorted_models:
        print(f"{model.value}:")
        print(f"  Total cost: ${costs['total_cost']:.6f}")
        print(f"  Input: ${costs['input_cost']:.6f}")
        print(f"  Output: ${costs['output_cost']:.6f}")
        print()


async def cost_projection_example():
    """Example 8: Cost projections"""
    print("\n=== Cost Projections ===\n")
    
    tracker = CostTracker()
    calculator = CostCalculator()
    
    # Simulate a week of usage
    for day in range(7):
        for i in range(10):
            tracker.track_usage(
                model=ModelType.GEMINI_15_PRO,
                request_type=RequestType.GENERATION,
                input_tokens=1000,
                output_tokens=500,
            )
    
    # Get recent records
    records = tracker.get_recent_requests(limit=1000)
    
    # Project next 30 days
    projection = calculator.calculate_projected_cost(
        historical_records=records,
        days=30,
    )
    
    print(f"Historical period: {projection['historical_days']} days")
    print(f"Historical cost: ${projection['historical_cost']:.2f}")
    print(f"Daily average: ${projection['daily_average']:.2f}")
    print(f"\nProjected for next {projection['projection_days']} days:")
    print(f"  Estimated cost: ${projection['projected_cost']:.2f}")
    print(f"  Confidence: {projection['confidence']}")


async def cost_breakdown_example():
    """Example 9: Detailed cost breakdown"""
    print("\n=== Cost Breakdown ===\n")
    
    tracker = CostTracker()
    calculator = CostCalculator()
    
    # Track varied usage
    for i in range(20):
        tracker.track_usage(
            model=ModelType.GEMINI_15_PRO if i % 2 == 0 else ModelType.GEMINI_15_FLASH,
            request_type=RequestType.GENERATION if i % 3 == 0 else RequestType.CLASSIFICATION,
            input_tokens=1000,
            output_tokens=500,
            user_id=f"user{i % 3}",
            metadata={"agent": f"agent{i % 2}"},
        )
    
    records = tracker.get_recent_requests(limit=100)
    breakdown = calculator.calculate_cost_breakdown(records)
    
    print("By Model:")
    for model, cost in breakdown["by_model"].items():
        print(f"  {model}: ${cost:.6f}")
    
    print("\nBy Request Type:")
    for req_type, cost in breakdown["by_request_type"].items():
        print(f"  {req_type}: ${cost:.6f}")
    
    print("\nBy User:")
    for user, cost in breakdown["by_user"].items():
        print(f"  {user}: ${cost:.6f}")


async def alert_management_example():
    """Example 10: Alert management"""
    print("\n=== Alert Management ===\n")
    
    tracker = CostTracker()
    budget_manager = BudgetManager()
    
    # Create budget
    budget = budget_manager.create_budget(
        name="Alert Test Budget",
        period=BudgetPeriod.DAILY,
        limit=5.0,
        warning_threshold=0.7,
        critical_threshold=0.9,
    )
    
    # Trigger warning
    tracker.track_usage(
        model=ModelType.GEMINI_15_PRO,
        request_type=RequestType.GENERATION,
        input_tokens=600000,  # $0.75
        output_tokens=600000,  # $3.00
    )
    budget_manager.update_budget_usage(budget.id, tracker)
    
    # Get unacknowledged alerts
    alerts = budget_manager.get_alerts(
        budget_id=budget.id,
        acknowledged=False,
    )
    
    print(f"Unacknowledged alerts: {len(alerts)}\n")
    for alert in alerts:
        print(f"Alert ID: {alert.id}")
        print(f"Level: {alert.level}")
        print(f"Message: {alert.message}")
        print(f"Budget: {alert.budget_name}")
        print(f"Usage: {alert.current_usage:.1f}% (${alert.current_cost:.2f}/${alert.budget_limit:.2f})")
        print()
        
        # Acknowledge the alert
        acknowledged = budget_manager.acknowledge_alert(alert.id, "admin")
        print(f"Acknowledged by: {acknowledged.acknowledged_by}")
        print(f"Acknowledged at: {acknowledged.acknowledged_at}")


async def main():
    """Run all examples"""
    examples = [
        ("Basic Tracking", basic_tracking_example),
        ("Usage Summary", usage_summary_example),
        ("Budget Management", budget_management_example),
        ("Per-User Budget", user_budget_example),
        ("Cost Optimization", cost_optimization_example),
        ("Analytics Report", analytics_report_example),
        ("Model Cost Comparison", cost_comparison_example),
        ("Cost Projections", cost_projection_example),
        ("Cost Breakdown", cost_breakdown_example),
        ("Alert Management", alert_management_example),
    ]
    
    print("=" * 60)
    print("Cost Analysis System - Examples")
    print("=" * 60)
    
    for name, example_func in examples:
        try:
            await example_func()
        except Exception as e:
            print(f"\nError in {name}: {e}")
        
        print("\n" + "-" * 60)
    
    print("\nAll examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
