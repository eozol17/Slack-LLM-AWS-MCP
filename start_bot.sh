#!/bin/bash

echo "🤖 Starting LLM Bot with logging..."
echo "📝 Logs will be written to bot.log"
echo "🔍 To monitor logs in real-time, run: python monitor_logs.py"
echo ""

# Start the bot and capture output
./venv/bin/python llm_bot.py 2>&1 | tee bot.log
