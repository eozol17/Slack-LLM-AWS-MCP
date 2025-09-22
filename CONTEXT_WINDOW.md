# Context Window & Retry Logic Configuration

The Slack LLM bot now supports configurable context windows and automatic retry logic with exponential backoff to handle API failures gracefully.

## How It Works

Instead of sending the entire channel conversation history to the LLM, the bot now only sends the last `t` messages as context, where `t` is configurable.

## Configuration

### Environment Variables

#### Context Window
Set the `CONTEXT_WINDOW_SIZE` environment variable to control the number of recent messages to include:

```bash
# Default: 5 messages
export CONTEXT_WINDOW_SIZE=5

# Disable context (fresh conversation each time)
export CONTEXT_WINDOW_SIZE=0

# More context for complex conversations
export CONTEXT_WINDOW_SIZE=10

# Minimal context
export CONTEXT_WINDOW_SIZE=2
```

#### Retry Logic
Configure retry behavior for API failures:

```bash
# Default: 3 attempts
export MAX_RETRY_ATTEMPTS=3

# Base delay for exponential backoff (default: 1.0 seconds)
export BASE_DELAY=1.0

# Maximum delay between retries (default: 30.0 seconds)
export MAX_DELAY=30.0
```

#### Smart Context Filtering
Configure intelligent context filtering:

```bash
# Similarity threshold for context relevance (default: 0.25)
export CONTEXT_SIMILARITY_THRESHOLD=0.25

# Disable context filtering entirely (default: false)
export DISABLE_CONTEXT_FILTERING=false
```

### In .env file

Add to your `.env` file:

```
CONTEXT_WINDOW_SIZE=5
MAX_RETRY_ATTEMPTS=3
BASE_DELAY=1.0
MAX_DELAY=30.0
CONTEXT_SIMILARITY_THRESHOLD=0.30
DISABLE_CONTEXT_FILTERING=false
```

## Commands

- `/context` - Show current context window and retry configuration
- `/help` - Show help including context window info

## Benefits

### Context Window
1. **Reduced Token Usage**: Only sends recent messages instead of entire conversation
2. **Better Performance**: Faster processing with smaller context
3. **Configurable**: Easy to adjust based on your needs
4. **Cost Effective**: Lower API costs due to reduced token usage

### Retry Logic
1. **Automatic Recovery**: Handles temporary API failures (overload, rate limits, network issues)
2. **Exponential Backoff**: Intelligent delay between retries to avoid overwhelming servers
3. **Jitter**: Random variation in delays to prevent thundering herd problems
4. **Configurable**: Adjust retry behavior based on your needs
5. **Better Reliability**: Reduces failed requests during high load periods

### Smart Context Filtering
1. **Semantic Analysis**: Automatically detects if historical context is relevant to current question
2. **No Keywords Required**: Works with any topic (campaign performance, user activity, revenue, etc.)
3. **Similarity Scoring**: Uses word overlap and length similarity to determine relevance
4. **Configurable Threshold**: Adjust how strict the filtering should be
5. **Disable Option**: Can be completely disabled if needed

## Examples

### Limited Context (CONTEXT_WINDOW_SIZE=3)
```
User: What's the revenue for Android?
Bot: [Analyzes with last 3 messages as context]

User: How about iOS?
Bot: [Analyzes with last 3 messages including the Android question]
```

### No Context (CONTEXT_WINDOW_SIZE=0)
```
User: What's the revenue for Android?
Bot: [Analyzes without any context]

User: How about iOS?
Bot: [Analyzes without any context - treats as fresh question]
```

### Extensive Context (CONTEXT_WINDOW_SIZE=20)
```
User: What's the revenue for Android?
Bot: [Analyzes with last 20 messages as context]

User: How about iOS?
Bot: [Analyzes with last 20 messages including extensive conversation history]
```

## Technical Details

- Messages are fetched using Slack's `conversations.history` API
- Bot messages and mentions are filtered out
- Messages are ordered chronologically (oldest first)
- Context is added before the current user message
- If context fetching fails, the bot falls back to no context

## Retry Logic Examples

### Conservative (Default)
```bash
MAX_RETRY_ATTEMPTS=3
BASE_DELAY=1.0
MAX_DELAY=30.0
```
- 3 attempts with delays: 1s, 2s, 4s
- Good for most use cases

### Aggressive Retry
```bash
MAX_RETRY_ATTEMPTS=5
BASE_DELAY=0.5
MAX_DELAY=15.0
```
- 5 attempts with delays: 0.5s, 1s, 2s, 4s, 8s
- Better for unreliable networks

### Minimal Retry
```bash
MAX_RETRY_ATTEMPTS=2
BASE_DELAY=2.0
MAX_DELAY=10.0
```
- 2 attempts with delays: 2s, 4s
- Faster failure for non-critical operations

## Recommended Settings

### Context Window
- **Development/Testing**: `CONTEXT_WINDOW_SIZE=2-3`
- **Production (Balanced)**: `CONTEXT_WINDOW_SIZE=5-7`
- **Complex Conversations**: `CONTEXT_WINDOW_SIZE=10-15`
- **Cost Optimization**: `CONTEXT_WINDOW_SIZE=1-3`
- **Fresh Conversations**: `CONTEXT_WINDOW_SIZE=0`

### Retry Logic
- **Production**: `MAX_RETRY_ATTEMPTS=3`, `BASE_DELAY=1.0`, `MAX_DELAY=30.0`
- **High Load**: `MAX_RETRY_ATTEMPTS=5`, `BASE_DELAY=2.0`, `MAX_DELAY=60.0`
- **Development**: `MAX_RETRY_ATTEMPTS=2`, `BASE_DELAY=0.5`, `MAX_DELAY=10.0`

### Smart Context Filtering
- **Strict Filtering**: `CONTEXT_SIMILARITY_THRESHOLD=0.35` (only very similar topics)
- **Balanced**: `CONTEXT_SIMILARITY_THRESHOLD=0.25` (default, good balance)
- **Loose Filtering**: `CONTEXT_SIMILARITY_THRESHOLD=0.15` (more context included)
- **Disabled**: `DISABLE_CONTEXT_FILTERING=true` (no filtering, use all context)

## Smart Context Filtering Examples

### Example 1: Topic Mismatch (Filtered Out)
```
Current Question: "How many users were active last weekend?"
Historical Context: "Android revenue analysis from mackolik_programmatic_tr_gam"
Result: Context filtered out (similarity: 0.12) - focuses on user activity
```

### Example 2: Topic Match (Kept)
```
Current Question: "What was the Android revenue last week?"
Historical Context: "Android revenue analysis from last week"
Result: Context kept (similarity: 0.46) - relevant to current question
```

### Example 3: Campaign Performance (No Keywords Needed)
```
Current Question: "How did our summer campaign perform?"
Historical Context: "Campaign metrics for summer promotion"
Result: Context kept (similarity: 0.45) - automatically detected relevance
```
