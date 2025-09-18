# LLM-Driven Data Bot with Tool Access
import os, asyncio, json, traceback, ssl, logging
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import certifi

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

# Fix SSL certificate issues
os.environ['SSL_CERT_FILE'] = certifi.where()

# Anthropic + Slack
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])

# Model configuration from environment
ANTHROPIC_MODEL_CHAT = os.getenv("ANTHROPIC_MODEL_CHAT", "claude-3-5-sonnet-20241022")
ANTHROPIC_MODEL_SQL = os.getenv("ANTHROPIC_MODEL_SQL", "claude-3-5-sonnet-20241022")

# MCP Server path (local to this directory)
SERVER_PATH = os.path.join(os.path.dirname(__file__), "aws_mcp_server.py")

# System prompt for LLM with tool access
SYSTEM_PROMPT = """You are a data analyst assistant for Mackolik with access to AWS Glue and Athena tools.

🚨 CRITICAL INSTRUCTIONS - READ CAREFULLY:
1. NEVER use partition columns (partition_0, partition_1, etc.) in WHERE clauses
2. Use dimension.date for date filtering: WHERE dimension.date BETWEEN '2025-09-10' AND '2025-09-17'
3. NEVER use LIKE with ad_unit_name - this will cause errors
4. DO NOT MENTION ANDROID OR iOS UNLESS USER SPECIFICALLY ASKS FOR IT
5. DO NOT PROVIDE GENERIC ANALYSIS - EXECUTE ACTUAL QUERIES
6. USE THE EXACT DATABASE THE USER SPECIFIES
7. PROVIDE SPECIFIC NUMBERS AND RESULTS ONLY

🚨 ABSOLUTE RULE: IF USER ASKS FOR REVENUE ANALYSIS WITHOUT MENTIONING ANDROID OR iOS, DO NOT MENTION ANDROID OR iOS IN YOUR RESPONSE! FOCUS ONLY ON THE REQUESTED DATABASE AND DATE RANGE!

CONTEXT RESET: This is a NEW conversation. Ignore any previous context or conversations. Focus ONLY on the current user request.

Available tools:
- glue_list_databases(): Get all available databases
- glue_list_tables(database): Get tables in a database with schema info
- athena_query(sql): Execute SQL query and get query execution ID
- athena_results(query_id): Get results from executed query
- athena_status(query_id): Check query status
- s3_presign(bucket, key): Get presigned URL for result files

MANDATORY Process for answering data questions:
1. Read the user's request carefully and focus ONLY on what they asked for
2. If user mentions a specific database (like mackolik_programmatic_tr_gam), go directly to that database
3. ALWAYS call glue_list_tables(database) to see what tables exist
4. Write SQL query using dimension.date for date filtering (NEVER partition columns)
5. Execute query using athena_query() and get results with athena_results()
6. Provide specific numbers and actual data - NO generic analysis

Important guidelines:
- For date queries, use Europe/Istanbul timezone. Today is {today}
- Always use fully qualified table names like database.table in SQL
- For Turkish questions, respond in Turkish
- For English questions, respond in English
- Be specific about numbers and findings
- If you get no results, suggest alternative queries
- NEVER give generic responses - always use tools to get real data
- Focus ONLY on what the user specifically requested - ignore previous conversation context
- If user mentions a specific database, use that exact database
- Do not search for other platforms or data unless specifically requested

AWS Athena SQL Guidelines:
- Use Presto/Trino SQL syntax (Athena's SQL engine)
- For column names with dots, use backticks: `dimension.date` not dimension.date
- Use single quotes for string literals: '2025-09-18' not "2025-09-18"
- Use double quotes for identifiers when needed: "table_name"
- For date filtering, use: WHERE `dimension.date` = '2025-09-18'
- Use CAST() for type conversions: CAST(`column.revenue` AS DECIMAL(18,2))
- Use LIKE with proper escaping: WHERE `dimension.app_name` LIKE '%Android%'
- For aggregations, use: SUM(CAST(`column.revenue` AS DECIMAL(18,2))) AS total_revenue
- Use LIMIT to control result size: LIMIT 100
- For date ranges, use: WHERE `dimension.date` BETWEEN '2025-09-01' AND '2025-09-18'
- Use proper GROUP BY with all non-aggregated columns
- Use ORDER BY for sorting: ORDER BY `dimension.date` DESC

Example conversation flows:
User: "show me revenue for android from GAM"
You: I'll help you find Android revenue data from GAM. Let me start by checking what databases are available.
[Then IMMEDIATELY call glue_list_databases() to start the data discovery process]

User: "show me revenue from gam_mackolik_prog for yesterday"
You: I'll help you get revenue data from gam_mackolik_prog for yesterday. Let me check the table structure first.
[Then IMMEDIATELY call glue_list_tables('gam_mackolik_prog') to start the analysis]

Athena SQL Examples:
- Simple query: SELECT `dimension.date`, `column.revenue` FROM gam_mackolik_prog.gam_mackolik_prog WHERE `dimension.date` = '2025-09-18' LIMIT 10
- Aggregation: SELECT `dimension.date`, SUM(CAST(`column.total_line_item_level_cpm_and_cpc_revenue` AS DECIMAL(18,2))) AS total_revenue FROM gam_mackolik_prog.gam_mackolik_prog WHERE `dimension.date` = '2025-09-18' GROUP BY `dimension.date`
- Date range: SELECT `dimension.date`, `column.revenue` FROM gam_mackolik_prog.gam_mackolik_prog WHERE `dimension.date` BETWEEN '2025-09-01' AND '2025-09-18' ORDER BY `dimension.date` DESC
- Filtering: SELECT * FROM gam_mackolik_prog.gam_mackolik_prog WHERE `dimension.mobile_app_name` LIKE '%Android%' LIMIT 100"""

async def extract_tool_result(mcp_result):
    """Extract JSON result from MCP response"""
    try:
        if hasattr(mcp_result, 'content'):
            for item in mcp_result.content:
                logger.info(f"Processing MCP content item: {type(item)}")
                if hasattr(item, 'model_dump_json'):
                    # Use the new Pydantic V2 method first
                    result = json.loads(item.model_dump_json())
                    logger.info(f"Model dump JSON result: {type(result)}")
                    
                    # If it's a dict with 'text' key, try to parse the inner text as JSON
                    if isinstance(result, dict) and 'text' in result and isinstance(result['text'], str):
                        try:
                            inner_parsed = json.loads(result['text'])
                            logger.info(f"Successfully parsed inner JSON from model_dump: {type(inner_parsed)}")
                            return inner_parsed
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse inner JSON from model_dump: {e}")
                            return result
                    
                    return result
                elif hasattr(item, 'json') and item.json:
                    # Fallback to old method if new one doesn't exist
                    if callable(item.json):
                        result = item.json()
                        logger.info(f"JSON method result: {type(result)}")
                        return result
                    else:
                        logger.info(f"JSON property result: {type(item.json)}")
                        return item.json
                elif hasattr(item, 'text') and item.text:
                    logger.info(f"Processing text content: {item.text[:100]}...")
                    try:
                        # Try to parse as JSON first
                        parsed = json.loads(item.text)
                        logger.info(f"Parsed outer JSON: {type(parsed)}")
                        
                        # If it's a dict with 'text' key, try to parse the inner text as JSON
                        if isinstance(parsed, dict) and 'text' in parsed and isinstance(parsed['text'], str):
                            try:
                                inner_parsed = json.loads(parsed['text'])
                                logger.info(f"Successfully parsed inner JSON: {type(inner_parsed)}")
                                return inner_parsed
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse inner JSON: {e}")
                                return parsed
                        logger.info(f"Returning parsed JSON: {type(parsed)}")
                        return parsed
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse as JSON: {e}")
                        # If not JSON, return as text
                        return {"text": item.text}
                    except Exception as e:
                        logger.error(f"Error parsing tool result: {e}")
                        return {"text": item.text}
        return {"error": "No content found"}
    except Exception as e:
        logger.error(f"Error in extract_tool_result: {e}")
        return {"error": str(e)}

async def call_llm_with_tools(messages, system_prompt, max_iterations=10):
    """Call LLM with tool access via MCP"""
    logger.info(f"Starting LLM call with {len(messages)} messages, max_iterations={max_iterations}")
    
    server = StdioServerParameters(command="python", args=[SERVER_PATH])
    logger.info(f"Connecting to MCP server: {SERVER_PATH}")
    
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            logger.info("MCP session initialized")
            await session.initialize()
            
            # Get available tools
            tools = await session.list_tools()
            tool_definitions = [{
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            } for tool in tools.tools]
            logger.info(f"Available tools: {[tool['name'] for tool in tool_definitions]}")
            
            current_messages = messages.copy()
            
            for iteration in range(max_iterations):
                logger.info(f"Iteration {iteration + 1}/{max_iterations}")
                logger.info(f"Current messages count: {len(current_messages)}")
                
                # Call Anthropic with tool definitions
                logger.info("Calling Anthropic API...")
                try:
                    response = await asyncio.to_thread(lambda: client.messages.create(
                        model=ANTHROPIC_MODEL_CHAT,
                        max_tokens=4000,
                        system=system_prompt,
                        messages=current_messages,
                        tools=tool_definitions
                    ))
                    logger.info("Anthropic API response received")
                except Exception as e:
                    logger.error(f"Anthropic API error: {e}")
                    if "429" in str(e) or "rate limit" in str(e).lower():
                        logger.warning("Rate limit hit, returning current analysis")
                        # Extract any text responses we have so far
                        text_parts = []
                        for msg in current_messages:
                            if msg.get("role") == "assistant" and "content" in msg:
                                for content in msg["content"]:
                                    if content.get("type") == "text":
                                        text_parts.append(content["text"])
                        if text_parts:
                            return "\n".join(text_parts)
                        return "I encountered a rate limit while processing your request. Please try again in a moment."
                    raise
                
                # Add assistant's response to conversation
                assistant_message = {"role": "assistant", "content": []}
                
                # Process response content
                has_tool_use = False
                tool_use = None
                tool_name = None
                tool_input = None
                
                for content in response.content:
                    logger.info(f"Processing content: {type(content)} - {content}")
                    if hasattr(content, 'text') and content.text:
                        logger.info(f"LLM text response: {content.text[:100]}...")
                        assistant_message["content"].append({"type": "text", "text": content.text})
                    elif hasattr(content, 'name') and hasattr(content, 'input'):  # ToolUseBlock
                        has_tool_use = True
                        tool_name = content.name
                        tool_input = content.input
                        
                        logger.info(f"LLM wants to use tool: {tool_name} with input: {tool_input}")
                        
                        # Add tool use to message
                        assistant_message["content"].append({
                            "type": "tool_use",
                            "id": content.id,
                            "name": tool_name,
                            "input": tool_input
                        })
                        break  # Only process the first tool use per iteration
                    else:
                        logger.info(f"Content type not recognized: {type(content)}")
                
                # Debug: Check if we have any tool use
                if not has_tool_use:
                    logger.warning("No tool use detected in LLM response - this might be why no data is retrieved")
                    logger.info(f"Full response content: {[str(c) for c in response.content]}")
                    # Extract final text response
                    text_parts = []
                    for content in response.content:
                        if hasattr(content, 'text') and content.text:
                            text_parts.append(content.text)
                    final_response = "\n".join(text_parts)
                    logger.info(f"Final LLM response: {final_response[:200]}...")
                    return final_response
                else:
                    # Execute tool via MCP
                    try:
                        logger.info(f"Executing tool: {tool_name}")
                        result = await session.call_tool(tool_name, tool_input)
                        tool_result = await extract_tool_result(result)
                        logger.info(f"Tool {tool_name} result: {str(tool_result)[:200]}...")
                        logger.info(f"Tool result type: {type(tool_result)}")
                        
                        # Add tool result to conversation
                        current_messages.append(assistant_message)
                        current_messages.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": json.dumps(tool_result)
                            }]
                        })
                        
                        logger.info(f"Added tool result to conversation. Total messages: {len(current_messages)}")
                        logger.info(f"Continuing to next iteration...")
                        
                        # Continue to next iteration to let LLM process the result
                        continue
                        
                    except Exception as e:
                        logger.error(f"Tool execution error: {str(e)}")
                        current_messages.append(assistant_message)
                        current_messages.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": json.dumps({"error": str(e)})
                            }]
                        })
                        continue
            
            # If we've exhausted iterations, check if we have any data to analyze
            logger.warning(f"Exhausted {max_iterations} iterations")
            
            # Check if we have any tool results with actual data
            has_data = False
            for msg in current_messages:
                if isinstance(msg, dict) and msg.get("role") == "user" and "content" in msg:
                    for content in msg["content"]:
                        if isinstance(content, dict) and content.get("type") == "tool_result":
                            result = content.get("content", "")
                            if isinstance(result, str):
                                try:
                                    parsed = json.loads(result)
                                    if isinstance(parsed, dict) and ("columns" in parsed or "data" in parsed or "rows" in parsed or "databases" in parsed or "tables" in parsed):
                                        has_data = True
                                        break
                                except:
                                    pass
                if has_data:
                    break
            
            # Also check if we have any successful tool executions (even if they returned errors)
            if not has_data:
                for msg in current_messages:
                    if isinstance(msg, dict) and msg.get("role") == "user" and "content" in msg:
                        for content in msg["content"]:
                            if isinstance(content, dict) and content.get("type") == "tool_result":
                                has_data = True
                                break
                    if has_data:
                        break
            
            if has_data:
                logger.info("Found data in conversation, asking LLM to analyze it")
                # Add a final message asking the LLM to analyze the data
                current_messages.append({
                    "role": "user", 
                    "content": "Based on the database exploration and queries I've executed, please provide a comprehensive analysis of the Android GAM revenue data. Include:\n1. What databases and tables were found\n2. What data structure was discovered\n3. Any successful query results\n4. Challenges encountered with column access\n5. Recommendations for accessing the Android revenue data\n\nPlease be specific about what was found and what the next steps should be."
                })
                
                try:
                    final_response = await asyncio.to_thread(lambda: client.messages.create(
                        model=ANTHROPIC_MODEL_CHAT,
                        max_tokens=4000,
                        system=system_prompt,
                        messages=current_messages
                    ))
                    
                    # Extract final text response
                    text_parts = []
                    for content in final_response.content:
                        if hasattr(content, 'text') and content.text:
                            text_parts.append(content.text)
                    
                    if text_parts:
                        return "\n".join(text_parts)
                except Exception as e:
                    logger.error(f"Error in final analysis: {e}")
            
            return "I've completed the data analysis. Please check the results above."

@app.command("/refresh")
async def refresh_conversation(ack, respond, body, client):
    """Refresh conversation context - clears any previous context"""
    await ack()
    user_id = body.get("user_id", "unknown")
    
    logger.info(f"Refresh conversation requested by user {user_id}")
    await respond("🔄 Conversation context cleared! I'm ready for your next question. What would you like to know about your data?")
    logger.info("Sent refresh confirmation to user")

@app.command("/help")
async def show_help(ack, respond, body, client):
    """Show available commands and usage"""
    await ack()
    user_id = body.get("user_id", "unknown")
    
    logger.info(f"Help requested by user {user_id}")
    help_text = """🤖 **Mackolik Data Assistant Commands**

**Slash Commands:**
• `/ask-data <question>` - Ask any data question
• `/refresh` - Clear conversation context and start fresh
• `/help` - Show this help message

**Mention Commands:**
• `@AI_Agent <question>` - Ask any data question
• `@AI_Agent refresh` - Clear conversation context

**Examples:**
• `/ask-data show me revenue from gam_mackolik_prog for yesterday`
• `@AI_Agent Son 7 günde iOS DAU kaç?`
• `/refresh` (then ask your next question)

**Tips:**
• Use `/refresh` when switching between different topics
• Be specific about databases, dates, and metrics
• Ask in Turkish or English - I'll respond in the same language"""
    
    await respond(help_text)
    logger.info("Sent help message to user")

@app.command("/ask-data")
async def ask_data(ack, respond, body, client):
    await ack()
    question = (body.get("text") or "").strip()
    user_id = body.get("user_id", "unknown")
    
    logger.info(f"Received /ask-data command from user {user_id}: '{question}'")
    
    if not question:
        logger.info("Empty question received, sending help message")
        await respond("Please provide a question about your data. Example: 'Son 7 günde iOS DAU kaç?' or 'Show me Android revenue for last month'")
        return
    
    # Check for refresh command
    if question.lower().strip() in ['refresh', 'reset', 'clear', 'new conversation', 'refresh conversation']:
        logger.info("Refresh conversation requested via /ask-data")
        await respond("🔄 Conversation refreshed! I'm ready for your next question. What would you like to know about your data?")
        return
    
    try:
        # Prepare system prompt with current date
        today = datetime.now(ZoneInfo("Europe/Istanbul")).date().isoformat()
        system = SYSTEM_PROMPT.format(today=today)
        logger.info(f"System prompt prepared for date: {today}")
        
        # Show that we're processing
        await respond(f"🔍 Analyzing your question: '{question}'\nLet me check the available data sources...")
        logger.info("Sent initial response to user")
        
        # Call LLM with tools - STRONG CONTEXT RESET
        messages = [{"role": "user", "content": question}]
        logger.info("Starting LLM processing...")
        answer = await call_llm_with_tools(messages, system)
        logger.info(f"LLM processing completed, response length: {len(answer)}")
        
        await respond(answer)
        logger.info("Sent final response to user")
        
    except Exception as e:
        logger.error(f"Error in /ask-data: {str(e)}")
        traceback.print_exc()
        await respond(f"❌ Error processing your request: {str(e)}")

@app.command("/catalog")
async def catalog(ack, respond, body, client):
    await ack()
    await respond("📊 Use `/ask-data` to explore your data! The AI will automatically discover databases and tables based on your question.\n\nExample: `/ask-data Son 7 günde iOS DAU kaç?`")

@app.command("/help")
async def help_cmd(ack, respond, body, client):
    await ack()
    help_text = """🤖 *LLM-Driven Data Assistant Help*

• `/ask-data <question>` - Ask any question about your data
  - Turkish: "Son 7 günde iOS DAU kaç?"
  - English: "Show me Android revenue for last month"
  
• `/catalog` - Learn how to explore data
• `/help` - Show this help

*How it works:*
The AI automatically:
1. 🔍 Discovers available databases
2. 📋 Finds relevant tables
3. 🔧 Writes appropriate SQL queries
4. 📊 Analyzes results
5. 💬 Provides clear answers

No need to know database or table names - just ask naturally!"""
    
    await respond(help_text)

@app.event("app_mention")
async def handle_mentions(body, say):
    ev = body.get("event", {}) or {}
    raw = ev.get("text", "") or ""
    user_id = ev.get("user", "unknown")
    
    # Get bot user ID from the event
    bot_id = body.get("authed_users", [None])[0] if body.get("authed_users") else None
    if not bot_id:
        # Fallback: try to extract from the text
        import re
        bot_mentions = re.findall(r'<@([A-Z0-9]+)>', raw)
        if bot_mentions:
            bot_id = bot_mentions[0]
    
    # Remove bot mention from text
    if bot_id:
        txt = raw.replace(f"<@{bot_id}>", "").strip()
    else:
        # Fallback to old method
        txt = raw.replace("<@U1234567890>", "").strip()
    
    logger.info(f"Received mention from user {user_id}: '{txt}'")
    
    if not txt:
        logger.info("Empty mention received, sending help message")
        await say("👋 Hi! I'm your data assistant. Ask me anything about your data!\n\nExample: `Son 7 günde iOS DAU kaç?` or `Show me Android revenue`")
        return
    
    # Check for refresh command
    if txt.lower().strip() in ['refresh', 'reset', 'clear', 'new conversation', 'refresh conversation']:
        logger.info("Refresh conversation requested")
        await say("🔄 Conversation refreshed! I'm ready for your next question. What would you like to know about your data?")
        return
    
    try:
        # Same LLM logic as /ask-data
        today = datetime.now(ZoneInfo("Europe/Istanbul")).date().isoformat()
        system = SYSTEM_PROMPT.format(today=today)
        logger.info(f"Processing mention with system prompt for date: {today}")
        
        await say(f"🔍 Processing: '{txt}'...")
        logger.info("Sent initial response to user")
        
        # STRONG CONTEXT RESET
        messages = [{"role": "user", "content": txt}]
        logger.info("Starting LLM processing for mention...")
        answer = await call_llm_with_tools(messages, system)
        logger.info(f"LLM processing completed for mention, response length: {len(answer)}")
        
        await say(answer)
        logger.info("Sent final response to user for mention")
        
    except Exception as e:
        logger.error(f"Error in mention handler: {str(e)}")
        traceback.print_exc()
        await say(f"❌ Error: {str(e)}")

@app.event("message")
async def handle_message(body, say):
    ev = body.get("event", {}) or {}
    if ev.get("subtype") or ev.get("bot_id"): 
        return
    
    # Only respond to direct messages
    if ev.get("channel_type") == "im":
        txt = ev.get("text", "").strip()
        if txt:
            await say("👋 Hi! Use `/ask-data` to ask questions about your data, or mention me in a channel!\n\nExample: `/ask-data Son 7 günde iOS DAU kaç?`")

async def main():
    logger.info("Starting LLM Bot...")
    logger.info(f"Anthropic model: {ANTHROPIC_MODEL_CHAT}")
    logger.info(f"MCP server path: {SERVER_PATH}")
    
    handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    logger.info("Socket mode handler created, starting...")
    await handler.start_async()

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("LLM Bot Starting Up")
    logger.info("=" * 50)
    asyncio.run(main())
