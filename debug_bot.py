#!/usr/bin/env python3
"""
Debug the bot's LLM tool calling without Slack
"""
import asyncio
import os
from dotenv import load_dotenv
from llm_bot import call_llm_with_tools, SYSTEM_PROMPT
from datetime import datetime
from zoneinfo import ZoneInfo

load_dotenv()

async def debug_bot():
    """Debug the bot's tool calling"""
    print("🔍 Debugging bot tool calling...")
    
    # Test question
    question = "show me revenue for android from GAM"
    print(f"📝 Test question: '{question}'")
    
    # Prepare system prompt
    today = datetime.now(ZoneInfo("Europe/Istanbul")).date().isoformat()
    system = SYSTEM_PROMPT.format(today=today)
    print(f"📅 System prompt date: {today}")
    
    # Call LLM with tools
    messages = [{"role": "user", "content": question}]
    print("🤖 Calling LLM with tools...")
    
    try:
        answer = await call_llm_with_tools(messages, system)
        print("✅ Bot response received:")
        print(f"📋 {answer}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_bot())
