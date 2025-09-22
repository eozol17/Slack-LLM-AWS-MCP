# Slack LLM AWS MCP Bot

A Slack bot that provides AI-powered data analysis capabilities using AWS Athena, Glue, and S3 services through Model Context Protocol (MCP).

## Overview

This bot allows users to ask natural language questions about their data stored in AWS Athena/Glue and receive intelligent responses. It uses Anthropic's Claude models to understand queries and automatically execute appropriate SQL queries against your AWS data sources.

## Features

- Natural language data queries via Slack
- Automatic database and table discovery
- Intelligent SQL query generation
- Read-only access to AWS data (SELECT queries only)
- Support for Turkish and English queries
- Real-time data analysis and insights

## Prerequisites

- Python 3.8+
- AWS Account with appropriate permissions
- Slack App with Bot Token and App Token
- Anthropic API Key

## AWS IAM Roles and Permissions

### Required IAM Permissions

The bot requires the following AWS permissions to function properly:

#### Athena Permissions
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "athena:StartQueryExecution",
                "athena:GetQueryExecution",
                "athena:GetQueryResults",
                "athena:StopQueryExecution",
                "athena:ListQueryExecutions"
            ],
            "Resource": "*"
        }
    ]
}
```

#### Glue Permissions
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "glue:GetDatabases",
                "glue:GetTables",
                "glue:GetTable",
                "glue:GetPartitions"
            ],
            "Resource": "*"
        }
    ]
}
```

#### S3 Permissions
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:HeadObject",
                "s3:GetObjectVersion"
            ],
            "Resource": [
                "arn:aws:s3:::your-athena-results-bucket/*",
                "arn:aws:s3:::your-athena-results-bucket"
            ]
        }
    ]
}
```

### Recommended IAM Policy

Create a custom IAM policy with the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AthenaAccess",
            "Effect": "Allow",
            "Action": [
                "athena:StartQueryExecution",
                "athena:GetQueryExecution",
                "athena:GetQueryResults",
                "athena:StopQueryExecution",
                "athena:ListQueryExecutions"
            ],
            "Resource": "*"
        },
        {
            "Sid": "GlueAccess",
            "Effect": "Allow",
            "Action": [
                "glue:GetDatabases",
                "glue:GetTables",
                "glue:GetTable",
                "glue:GetPartitions"
            ],
            "Resource": "*"
        },
        {
            "Sid": "S3AthenaResults",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:HeadObject",
                "s3:GetObjectVersion"
            ],
            "Resource": [
                "arn:aws:s3:::your-athena-results-bucket/*",
                "arn:aws:s3:::your-athena-results-bucket"
            ]
        }
    ]
}
```

### IAM User/Role Setup

1. **Option 1: IAM User (Recommended for development)**
   - Create a new IAM user
   - Attach the custom policy above
   - Generate access keys
   - Set environment variables: `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`

2. **Option 2: IAM Role (Recommended for production)**
   - Create an IAM role with the custom policy
   - Attach the role to your EC2 instance, Lambda function, or ECS task
   - No need for access keys (uses instance profile)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Slack-LLM-AWS-MCP
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in the project root:

```bash
# AWS Configuration
AWS_REGION="--Your AWS Region--"
ATHENA_WORKGROUP="--Your Workgroup--"
ATHENA_OUTPUT_S3=s3://your-athena-results-bucket/

# AWS Credentials (if using IAM user)
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key

# Anthropic Configuration
### To use another model as backend change here
ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_MODEL_CHAT=claude-3-5-sonnet-20241022
ANTHROPIC_MODEL_SQL=claude-3-5-sonnet-20241022

# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
```

### 5. Slack App Setup

1. **Create a Slack App**
   - Go to [api.slack.com](https://api.slack.com/apps)
   - Click "Create New App" → "From scratch"
   - Name your app and select your workspace

2. **Configure Bot Token Scopes**
   - Go to "OAuth & Permissions"
   - Add the following Bot Token Scopes:
     - `app_mentions:read`
     - `channels:history`
     - `chat:write`
     - `commands`
     - `im:history`
     - `im:read`
     - `im:write`

3. **Enable Socket Mode**
   - Go to "Socket Mode"
   - Enable Socket Mode
   - Generate an App Token with `connections:write` scope

4. **Create Slash Commands**
   - Go to "Slash Commands"
   - Create the following commands:
     - `/ask-data` - Ask data questions
     - `/refresh` - Clear conversation context
     - `/help` - Show help information
     - `/catalog` - Learn about data exploration

5. **Install App to Workspace**
   - Go to "Install App"
   - Click "Install to Workspace"
   - Copy the Bot User OAuth Token and App Token

### 6. AWS Athena Setup

1. **Create S3 Bucket for Results**
   ```bash
   aws s3 mb s3://your-athena-results-bucket
   ```

2. **Configure Athena Workgroup**
   - Go to AWS Athena console
   - Create or use existing workgroup
   - Set output location to your S3 bucket

3. **Verify Glue Catalog**
   - Ensure your data is registered in AWS Glue Data Catalog
   - Verify databases and tables are accessible

### 7. Run the Bot

```bash
# Start the bot
python llm_bot.py

# Or use the provided script
./start_bot.sh
```

## Usage

### Slash Commands

- `/ask-data <question>` - Ask any data question
- `/refresh` - Clear conversation context
- `/help` - Show help information
- `/catalog` - Learn about data exploration

### Examples

**English:**
```
/ask-data show me revenue from your_database_name for yesterday
/ask-data What are the top performing ad units this week?
```

**Turkish:**
```
/ask-data Son 7 günde iOS DAU kaç?
/ask-data Android gelir verilerini göster
```

### Mentions

You can also mention the bot in channels:
```
@AI_Agent show me yesterday's revenue data
@AI_Agent Son 3 günde hangi uygulamalar en çok kullanıldı?
```

## Security Considerations

### Environment Variables
- Never commit `.env` file to version control
- Use IAM roles instead of access keys when possible
- Rotate credentials regularly

### AWS Permissions
- Follow principle of least privilege
- Use separate IAM users/roles for different environments
- Monitor CloudTrail for access patterns

### Data Access
- The bot only supports SELECT queries (read-only)
- No INSERT, UPDATE, DELETE, or DDL operations are allowed
- All queries are logged for audit purposes

## Troubleshooting

### Common Issues

1. **AWS Credentials Not Found**
   - Verify environment variables are set
   - Check IAM permissions
   - Ensure AWS CLI is configured if using default profile

2. **Slack Connection Issues**
   - Verify bot token and app token
   - Check Socket Mode is enabled
   - Ensure bot is installed in workspace

3. **Athena Query Failures**
   - Check S3 bucket permissions
   - Verify workgroup configuration
   - Ensure Glue catalog is accessible

### Logs

Check the `bot.log` file for detailed error information:

```bash
tail -f bot.log
```

## Development

### Project Structure

```
├── aws_mcp_server.py    # MCP server for AWS services
├── llm_bot.py          # Main Slack bot application
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (not in git)
├── bot.log           # Application logs
└── README.md         # This file
```

### Adding New Tools

To add new AWS services or tools:

1. Add new functions to `aws_mcp_server.py` with `@mcp.tool()` decorator
2. Update the system prompt in `llm_bot.py` to include new tool descriptions
3. Test with `/ask-data` command

### Customizing Models

Change the Anthropic model by updating environment variables:

```bash
ANTHROPIC_MODEL_CHAT=claude-3-5-sonnet-20241022
ANTHROPIC_MODEL_SQL=claude-3-5-sonnet-20241022
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions:
- Check the troubleshooting section
- Review AWS CloudTrail logs
- Check Slack app configuration
- Verify IAM permissions

---

**Note**: This bot is designed for read-only data analysis. It will not modify any data in your AWS environment.