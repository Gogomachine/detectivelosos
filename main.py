#!/usr/bin/env python3
"""
Case Walker — AML Journalist Agent
Main entry point for running the agent.

Usage:
    python main.py              # Run the full agent (parser + publisher + scheduler)
    python main.py --parse      # Run a single parse cycle
    python main.py --post       # Generate and publish one post
    python main.py --digest     # Generate and publish a digest
    python main.py --status     # Show agent status
"""

import argparse
import asyncio
import logging
import sys

from config import ADMIN_CHAT_IDS
from src.agent import CaseWalkerAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("agent.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("casewalker")


async def run_agent():
    """Run the full agent with scheduler."""
    agent = CaseWalkerAgent(admin_chat_ids=ADMIN_CHAT_IDS)
    await agent.run_forever()


async def run_single_parse():
    """Run a single news parsing cycle."""
    agent = CaseWalkerAgent(admin_chat_ids=ADMIN_CHAT_IDS)
    await agent.db.connect()
    count = await agent.parse_all_news()
    print(f"Parsed and saved {count} new articles")
    await agent.db.close()


async def run_single_post():
    """Generate and publish a single post."""
    agent = CaseWalkerAgent(admin_chat_ids=ADMIN_CHAT_IDS)
    await agent.db.connect()
    result = await agent.generate_and_publish_post()
    print(result)
    await agent.db.close()


async def run_digest(is_morning: bool = True):
    """Generate and publish a digest."""
    agent = CaseWalkerAgent(admin_chat_ids=ADMIN_CHAT_IDS)
    await agent.db.connect()
    await agent.generate_and_publish_digest(is_morning=is_morning)
    print("Digest published")
    await agent.db.close()


async def show_status():
    """Show agent status."""
    agent = CaseWalkerAgent(admin_chat_ids=ADMIN_CHAT_IDS)
    await agent.db.connect()
    status = await agent.get_status()
    print(status)
    await agent.db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Case Walker — AML Journalist Agent 🕵️"
    )
    parser.add_argument("--parse", action="store_true", help="Run single parse cycle")
    parser.add_argument("--post", action="store_true", help="Generate and publish one post")
    parser.add_argument("--digest", action="store_true", help="Generate morning digest")
    parser.add_argument(
        "--digest-evening", action="store_true", help="Generate evening digest"
    )
    parser.add_argument("--status", action="store_true", help="Show agent status")

    args = parser.parse_args()

    if args.parse:
        asyncio.run(run_single_parse())
    elif args.post:
        asyncio.run(run_single_post())
    elif args.digest:
        asyncio.run(run_digest(is_morning=True))
    elif args.digest_evening:
        asyncio.run(run_digest(is_morning=False))
    elif args.status:
        asyncio.run(show_status())
    else:
        # Run full agent
        print("🕵️ Запускаю Кейса Уокера...")
        print("    АМЛ-агент-журналист — ходит по делам!")
        print("    Ctrl+C для остановки\n")
        asyncio.run(run_agent())


if __name__ == "__main__":
    main()
