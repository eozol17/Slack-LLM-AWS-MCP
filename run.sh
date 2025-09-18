#!/bin/bash

# LLM Orchestrator Bot Startup Script

echo "🤖 Starting LLM Orchestrator Bot..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please create .env file with required environment variables:"
    echo "ANTHROPIC_API_KEY=your_key"
    echo "SLACK_BOT_TOKEN=xoxb-your-token"
    echo "SLACK_APP_TOKEN=xapp-your-token"
    echo "ATHENA_OUTPUT_S3=s3://your-bucket"
    echo "AWS_REGION=eu-central-1"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Start the bot
echo "🚀 Starting LLM Bot..."
python llm_bot.py
