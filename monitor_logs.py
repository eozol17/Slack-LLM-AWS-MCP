#!/usr/bin/env python3
"""
Real-time log monitor for the LLM Bot
"""
import time
import os
import sys

def monitor_logs():
    """Monitor bot.log file in real-time"""
    log_file = "bot.log"
    
    if not os.path.exists(log_file):
        print(f"❌ Log file {log_file} not found. Start the bot first!")
        return
    
    print(f"🔍 Monitoring {log_file}... Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        with open(log_file, 'r') as f:
            # Go to end of file
            f.seek(0, 2)
            
            while True:
                line = f.readline()
                if line:
                    # Color code different log levels
                    if "ERROR" in line:
                        print(f"\033[91m{line.strip()}\033[0m")  # Red
                    elif "WARNING" in line:
                        print(f"\033[93m{line.strip()}\033[0m")  # Yellow
                    elif "INFO" in line:
                        print(f"\033[92m{line.strip()}\033[0m")  # Green
                    else:
                        print(line.strip())
                else:
                    time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n👋 Stopped monitoring logs")
    except Exception as e:
        print(f"❌ Error monitoring logs: {e}")

if __name__ == "__main__":
    monitor_logs()
