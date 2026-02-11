"""CLI utility for interacting with the AI Agent Workflow.

Usage:
    python -m app.cli chat "user-123" "Hello, how are you?"
    python -m app.cli history "user-123"
    python -m app.cli cleanup-cache
"""
import asyncio
import sys
import json
from .orchestrator import Orchestrator
from .database import DatabaseManager


async def chat(user_id: str, message: str, use_web: bool = False, use_linkedin: bool = False):
    """Send a message and get response."""
    orch = Orchestrator()
    result = await orch.handle(user_id, message, use_web=use_web, use_linkedin=use_linkedin)
    print(json.dumps(result, indent=2))


async def history(user_id: str, limit: int = 10):
    """Get conversation history."""
    orch = Orchestrator()
    result = await orch.get_conversation_history(user_id, limit)
    print(json.dumps(result, indent=2))


def cleanup_cache():
    """Clean up expired cache entries."""
    db = DatabaseManager()
    deleted = db.cleanup_expired_cache()
    print(f"Cleaned up {deleted} expired cache entries.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m app.cli <command> [args...]")
        print("Commands:")
        print("  chat <user_id> <message> [--web] [--linkedin]")
        print("  history <user_id> [--limit N]")
        print("  cleanup-cache")
        sys.exit(1)

    command = sys.argv[1]

    if command == "chat":
        if len(sys.argv) < 4:
            print("Usage: python -m app.cli chat <user_id> <message> [--web] [--linkedin]")
            sys.exit(1)
        user_id = sys.argv[2]
        message = sys.argv[3]
        use_web = "--web" in sys.argv
        use_linkedin = "--linkedin" in sys.argv
        asyncio.run(chat(user_id, message, use_web, use_linkedin))

    elif command == "history":
        if len(sys.argv) < 3:
            print("Usage: python -m app.cli history <user_id> [--limit N]")
            sys.exit(1)
        user_id = sys.argv[2]
        limit = 10
        if "--limit" in sys.argv:
            limit_idx = sys.argv.index("--limit")
            if limit_idx + 1 < len(sys.argv):
                limit = int(sys.argv[limit_idx + 1])
        asyncio.run(history(user_id, limit))

    elif command == "cleanup-cache":
        cleanup_cache()

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
