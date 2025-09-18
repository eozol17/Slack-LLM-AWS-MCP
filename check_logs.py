#!/usr/bin/env python3
"""
Check recent bot logs
"""
import os
import sys

def check_logs():
    log_file = "bot.log"
    
    if not os.path.exists(log_file):
        print("❌ No log file found. Start the bot first!")
        return
    
    print(f"📋 Recent logs from {log_file}:")
    print("=" * 50)
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            # Show last 30 lines
            recent_lines = lines[-30:] if len(lines) > 30 else lines
            
            for line in recent_lines:
                print(line.rstrip())
                
    except Exception as e:
        print(f"❌ Error reading logs: {e}")

if __name__ == "__main__":
    check_logs()
