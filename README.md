# LLM Orchestrator Bot

This is a simplified, LLM-driven version of the Slack MCP bot that uses Claude as the orchestrator for data queries.

## Architecture

Instead of complex hardcoded logic, this bot uses an LLM (Claude) with tool access to:
1. Understand user questions
2. Discover available databases and tables
3. Write appropriate SQL queries
4. Execute queries via MCP tools
5. Analyze results and provide answers

## Files

- `llm_bot.py` - Main bot implementation (150 lines vs 1300+ in original)
- `README.md` - This documentation
- `requirements.txt` - Dependencies
- `run.sh` - Startup script

## How It Works

### Traditional Approach (Complex)
```
User Question → 1000+ lines of hardcoded logic → Database Selection → Table Matching → SQL Generation → Results
```

### LLM Approach (Simple)
```
User Question → LLM with Tools → Automatic Discovery → Smart Querying → Results
```

## LLM Process

1. **User asks**: "Son 7 günde iOS DAU kaç?"
2. **LLM thinks**: "I need to find DAU data for iOS in the last 7 days"
3. **LLM uses tool**: `glue_list_databases()` → discovers databases
4. **LLM thinks**: "adjust_macko_dau sounds like the right database"
5. **LLM uses tool**: `glue_list_tables("adjust_macko_dau")` → sees tables
6. **LLM thinks**: "adjust_dau table probably has the data I need"
7. **LLM uses tool**: `athena_query("SELECT * FROM adjust_macko_dau.adjust_dau WHERE day >= '2024-01-01' AND os_name = 'ios'")`
8. **LLM uses tool**: `athena_results(query_id)` → gets actual data
9. **LLM responds**: "Son 7 günde iOS DAU ortalama 45,230 kullanıcı..."

## Benefits

✅ **Much Simpler**: 150 lines vs 1300+ lines  
✅ **More Flexible**: Handles new question types without code changes  
✅ **Better Reasoning**: LLM can handle complex scenarios  
✅ **Self-Improving**: Learns from tool interactions  
✅ **Natural Language**: No need to know database/table names  
✅ **Maintainable**: All logic in prompts, not hardcoded  

## Commands

- `/ask-data <question>` - Ask any data question
- `/help` - Show help
- `/catalog` - Learn about data exploration

## Environment Variables

Same as original bot:
- `ANTHROPIC_API_KEY`
- `SLACK_BOT_TOKEN`
- `SLACK_APP_TOKEN`
- `ATHENA_OUTPUT_S3`
- `AWS_REGION`

## Usage

```bash
cd llm_orchestrator
pip install -r requirements.txt
python llm_bot.py
```

## Example Conversations

**Turkish:**
```
User: Son 7 günde iOS DAU kaç?
Bot: 🔍 Analyzing your question: 'Son 7 günde iOS DAU kaç?'
     Let me check the available data sources...
     [LLM discovers databases, tables, executes query]
     Son 7 günde iOS DAU ortalama 45,230 kullanıcı. Detaylar: ...
```

**English:**
```
User: Show me Android revenue for last month
Bot: 🔍 Analyzing your question: 'Show me Android revenue for last month'
     Let me check the available data sources...
     [LLM discovers databases, tables, executes query]
     Android revenue for last month was $125,430. Here's the breakdown: ...
```

## Comparison with Original Bot

| Aspect | Original Bot | LLM Bot |
|--------|-------------|---------|
| Lines of Code | 1,347 | 150 |
| Database Selection | Hardcoded algorithms | LLM reasoning |
| Table Matching | Complex scoring | Natural language understanding |
| SQL Generation | Template-based | LLM-generated |
| Error Handling | Extensive try/catch | LLM adaptation |
| New Features | Requires code changes | Prompt updates |
| Maintenance | High complexity | Simple prompts |
