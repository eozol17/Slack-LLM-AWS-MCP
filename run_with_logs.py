#!/usr/bin/env python3
"""
Start the bot with logging to both console and file
"""
import subprocess
import sys
import os

def main():
    print("🤖 Starting LLM Bot with logging...")
    print("📝 Logs will be written to bot.log")
    print("🔍 To monitor logs in real-time, run: python monitor_logs.py")
    print("=" * 50)
    
    # Start the bot
    try:
        subprocess.run(["./venv/bin/python", "llm_bot.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Bot failed with exit code {e.returncode}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
