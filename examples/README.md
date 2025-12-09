# Ohio BMV Agent Service - Code Examples

This directory contains Python code examples demonstrating how to create and configure the Azure AI Foundry agent for the Ohio BMV use case.

## Files

- **`create_agent.py`** - Complete example of creating an agent with Bing grounding
- **`requirements.txt`** - Python dependencies needed to run the examples
- **`.env.example`** - Template for environment variables (copy to `.env` and fill in your values)

## Prerequisites

1. **Azure AI Foundry Project**
   - Create a project at https://ai.azure.com
   - Note your project endpoint from the overview page

2. **Bing Custom Search Connection**
   - Follow [../docs/bing-custom-search-setup.md](../docs/bing-custom-search-setup.md)
   - Configure the connection in your Foundry project
   - Note the connection ID from "Connected resources"

3. **Azure CLI & Authentication**
   ```bash
   az login
   ```

4. **Python Environment**
   ```bash
   python --version  # Should be 3.11 or higher
   ```

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

3. **Set environment variables in your shell:**
   ```bash
   # Option 1: Use python-dotenv (recommended)
   # The script will automatically load .env file
   
   # Option 2: Export manually
   export PROJECT_ENDPOINT="https://your-project.eastus.api.azureml.ms"
   export BING_CONNECTION_ID="/subscriptions/.../connections/bing-search"
   export MODEL_DEPLOYMENT_NAME="gpt-4o"
   ```

## Running the Examples

### Create and Test the Agent

```bash
python create_agent.py
```

This will:
1. Create an AI project client
2. Load the system prompt from `../prompts/ohio-bmv-agent-system-prompt.md`
3. Initialize Bing grounding with your custom search configuration
4. Create the agent
5. Test it with a sample question about driver's license renewal

**Expected output:**
```
Creating AI Project Client...
Initializing Bing Grounding tool...
Loading system prompt...
Creating Ohio BMV agent...
✅ Created agent: asst_abc123xyz
   Name: ohio-bmv-online-assistant
   Model: gpt-4o
   Tools: Bing Grounding

============================================================
Testing agent with question:
  What documents do I need to renew my Ohio driver's license? 
============================================================

Created thread: thread_abc123
Created message: msg_abc123
Running agent...
Run completed with status: completed

============================================================
Conversation:
============================================================

USER:
What documents do I need to renew my Ohio driver's license? Also, can you tell me about the fees?

ASSISTANT:
To renew your Ohio driver's license, you'll need:
1. Your current Ohio driver's license
2. Payment for the renewal fee ($32.25 for an 8-year license)
...

============================================================
✅ Agent creation and testing completed successfully!
Agent ID: asst_abc123xyz
```

## What the Code Does

### 1. Authentication
Uses `DefaultAzureCredential()` which tries multiple authentication methods:
- Azure CLI (`az login`)
- Environment variables
- Managed Identity (when running in Azure)

### 2. Bing Grounding Setup
```python
bing = BingGroundingTool(connection_id=bing_connection_id)
```

This connects to your Bing Custom Search instance configured to search only:
- `bmv.ohio.gov`
- `codes.ohio.gov`
- Other approved Ohio BMV domains

### 3. Agent Creation
```python
agent = project_client.agents.create_agent(
    model="gpt-4o",
    name="ohio-bmv-online-assistant",
    instructions=system_instructions,  # From the markdown file
    tools=bing.definitions,
)
```

The agent is created with:
- Your chosen model (GPT-4o recommended)
- The detailed system prompt for BMV use cases
- Bing grounding tool attached

### 4. Testing
Creates a thread, sends a message, and runs the agent to demonstrate:
- How the agent uses Bing grounding to answer questions
- How to retrieve and display conversation history
- How to inspect tool usage in run steps

## Next Steps

### Add MCP Tool for Address Changes

The current example shows Bing grounding only. To add the MCP tool for address changes:

1. **Deploy the MCP server** (if not already done):
   ```bash
   cd ../mcp-server
   azd up
   ```

2. **Get the MCP endpoint and key:**
   ```bash
   # Get function app name
   FUNCTION_APP_NAME=$(cat .azure/$(cat .azure/config.json | jq -r '.defaultEnvironment')/env.json | jq -r '.FUNCTION_APP_NAME')
   
   # Get MCP extension key
   az functionapp keys list --resource-group rg-ohio-bmv-sql-mcp --name $FUNCTION_APP_NAME
   ```

3. **Configure MCP connection in Foundry:**
   - Go to your project in Azure AI Foundry portal
   - Navigate to "Connected resources"
   - Add a new connection for your MCP server
   - Use the SSE endpoint: `https://<function-app-name>.azurewebsites.net/runtime/webhooks/mcp/sse`

4. **Update the agent to include MCP tools:**
   ```python
   # In create_agent.py, you would add:
   from azure.ai.agents.models import ConnectionTool
   
   mcp_connection_id = os.environ["MCP_CONNECTION_ID"]
   mcp_tool = ConnectionTool(connection_id=mcp_connection_id)
   
   # Then combine tools:
   tools = bing.definitions + mcp_tool.definitions
   
   agent = project_client.agents.create_agent(
       model=model_deployment_name,
       name="ohio-bmv-online-assistant",
       instructions=system_instructions,
       tools=tools,  # Now includes both Bing and MCP tools
   )
   ```

### Use the Agent in Production

Once created, you can use the agent ID in your application:

```python
# In your application code
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

project_client = AIProjectClient(
    endpoint=project_endpoint,
    credential=DefaultAzureCredential()
)

# Use the existing agent
agent_id = "asst_abc123xyz"  # From the creation output

with project_client:
    thread = project_client.agents.threads.create()
    
    message = project_client.agents.messages.create(
        thread_id=thread.id,
        role="user",
        content="I need to update my license address..."
    )
    
    run = project_client.agents.runs.create_and_process(
        thread_id=thread.id,
        agent_id=agent_id
    )
    
    messages = project_client.agents.messages.list(thread_id=thread.id)
    # Process messages...
```

## Troubleshooting

### Error: "PROJECT_ENDPOINT environment variable is required"
- Make sure you've created a `.env` file with your values
- Or export the environment variables in your shell

### Error: "DefaultAzureCredential failed to retrieve a token"
- Run `az login` to authenticate with Azure CLI
- Ensure you have access to the Azure subscription

### Error: "Connection ID not found"
- Verify your Bing connection is set up in the Foundry portal
- Check the connection ID format matches the expected pattern
- The connection ID should start with `/subscriptions/...`

### Agent doesn't use Bing grounding
- Check that your Bing Custom Search is configured correctly
- Verify the connection is active in the Foundry portal
- Try explicitly forcing the tool: `tool_choice={"type": "bing_grounding"}`

## Resources

- [Azure AI Foundry Documentation](https://learn.microsoft.com/azure/ai-foundry/)
- [Bing Grounding Code Samples](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/tools/bing-code-samples)
- [Azure AI Projects SDK](https://learn.microsoft.com/python/api/overview/azure/ai-projects-readme)
- [Main Project README](../README.md)
