"""
Integration Test Runner

Script to run integration tests with different configurations:
- Smoke tests only (quick)
- Full integration suite
- Performance benchmarks
- Load tests
- Chaos engineering
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run command and print results"""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode != 0:
        print(f"\n❌ {description} FAILED")
        return False
    else:
        print(f"\n✅ {description} PASSED")
        return True


def run_smoke_tests():
    """Run smoke tests only (<1 minute)"""
    cmd = [
        "pytest",
        "tests/integration",
        "-m", "smoke",
        "-v",
        "--tb=short"
    ]
    return run_command(cmd, "Smoke Tests")


def run_integration_tests():
    """Run all integration tests (except slow tests)"""
    cmd = [
        "pytest",
        "tests/integration",
        "-m", "integration and not slow",
        "-v"
    ]
    return run_command(cmd, "Integration Tests")


def run_performance_tests():
    """Run performance benchmark tests"""
    cmd = [
        "pytest",
        "tests/integration",
        "-m", "performance",
        "-v",
        "-s"  # Show print statements for metrics
    ]
    return run_command(cmd, "Performance Benchmarks")


def run_load_tests():
    """Run load tests"""
    cmd = [
        "pytest",
        "tests/integration",
        "-m", "load",
        "-v",
        "-s"
    ]
    return run_command(cmd, "Load Tests")


def run_chaos_tests():
    """Run chaos engineering tests"""
    cmd = [
        "pytest",
        "tests/integration",
        "-m", "chaos",
        "-v"
    ]
    return run_command(cmd, "Chaos Engineering Tests")


def run_all_tests():
    """Run complete test suite"""
    cmd = [
        "pytest",
        "tests/integration",
        "-v",
        "--tb=short"
    ]
    return run_command(cmd, "Complete Test Suite")


def run_with_coverage():
    """Run tests with coverage report"""
    cmd = [
        "pytest",
        "tests/integration",
        "--cov=app",
        "--cov=routing",
        "--cov=linkedin",
        "--cov=cost_analysis",
        "--cov-report=html",
        "--cov-report=term",
        "-v"
    ]
    return run_command(cmd, "Tests with Coverage")


def main():
    parser = argparse.ArgumentParser(description="Integration Test Runner")
    parser.add_argument(
        "suite",
        choices=["smoke", "integration", "performance", "load", "chaos", "all", "coverage"],
        help="Test suite to run"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    print(f"\n🚀 Running {args.suite.upper()} tests...")
    
    if args.suite == "smoke":
        success = run_smoke_tests()
    elif args.suite == "integration":
        success = run_integration_tests()
    elif args.suite == "performance":
        success = run_performance_tests()
    elif args.suite == "load":
        success = run_load_tests()
    elif args.suite == "chaos":
        success = run_chaos_tests()
    elif args.suite == "all":
        success = run_all_tests()
    elif args.suite == "coverage":
        success = run_with_coverage()
    
    if success:
        print(f"\n✅ All {args.suite} tests passed!")
        sys.exit(0)
    else:
        print(f"\n❌ Some {args.suite} tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
