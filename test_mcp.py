#!/usr/bin/env python3
"""
Test MCP server connection and tools
"""
import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

load_dotenv()

async def test_mcp():
    """Test MCP server connection"""
    print("🔧 Testing MCP server connection...")
    
    # Check environment
    required_vars = ["ATHENA_OUTPUT_S3", "AWS_REGION"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"❌ Missing environment variables: {missing}")
        return False
    
    print("✅ Environment variables OK")
    
    # Test MCP server
    server_path = os.path.join(os.path.dirname(__file__), "aws_mcp_server.py")
    print(f"🔗 Connecting to MCP server: {server_path}")
    
    server = StdioServerParameters(command="python", args=[server_path])
    
    try:
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as session:
                print("✅ MCP session connected")
                await session.initialize()
                print("✅ MCP session initialized")
                
                # List tools
                tools = await session.list_tools()
                print(f"✅ Available tools: {[tool.name for tool in tools.tools]}")
                
                # Test a simple tool call
                print("🧪 Testing glue_list_databases...")
                result = await session.call_tool("glue_list_databases", {})
                print(f"✅ Tool result: {result}")
                
                return True
                
    except Exception as e:
        print(f"❌ MCP test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mcp())
    if success:
        print("\n🎉 MCP server is working!")
    else:
        print("\n💥 MCP server test failed!")
