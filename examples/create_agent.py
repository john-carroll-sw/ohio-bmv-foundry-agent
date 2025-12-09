"""
Ohio BMV Agent Service Setup Example

This script demonstrates how to create an Azure AI Foundry agent with:
1. Bing Custom Search grounding for official BMV information
2. MCP tool connection for license address change requests

Prerequisites:
- Azure CLI installed and logged in (`az login`)
- Azure AI Foundry project created
- Bing Custom Search connection configured in the project
- Appropriate RBAC permissions (Azure AI Developer role)

Authentication:
- Uses DefaultAzureCredential (Azure CLI, Managed Identity, etc.)
- Bing connection can be provided via BING_CONNECTION_ID env var or auto-discovered
"""

import os
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import BingGroundingTool

# Load environment variables from .env file
load_dotenv()

# Load system prompt from file
def load_system_prompt(prompt_file: str = "../prompts/ohio-bmv-agent-system-prompt.md") -> str:
    """Load the system prompt from a markdown file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(script_dir, prompt_file)
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

def get_bing_connection_id(project_client) -> str:
    """
    Auto-discover the Bing connection ID from the project's connections.
    
    Args:
        project_client: The AI project client
        
    Returns:
        str: The connection ID for Bing Custom Search
        
    Raises:
        ValueError: If no Bing connection is found
    """
    print("Auto-discovering Bing Custom Search connection...")
    
    connections = project_client.connections.list()
    
    for conn in connections:
        # Look for Bing Custom Search connection
        conn_type = getattr(conn, 'connection_type', getattr(conn, 'type', ''))
        if conn_type == "BingCustomSearch" or "bing" in conn.name.lower():
            print(f"✅ Found Bing connection: {conn.name}")
            print(f"   Connection ID: {conn.id}")
            return conn.id
    
    raise ValueError(
        "No Bing Custom Search connection found in this project.\n"
        "Please create one in the Azure AI Foundry portal or provide BING_CONNECTION_ID env var."
    )

def create_ohio_bmv_agent():
    """
    Create and configure the Ohio BMV agent with Bing grounding and MCP tools.
    Uses DefaultAzureCredential for authentication.
    
    Returns:
        tuple: (agent, project_client) - The created agent and project client
    """
    
    # Only require the project endpoint
    project_endpoint = os.environ.get("PROJECT_ENDPOINT")
    if not project_endpoint:
        raise ValueError(
            "PROJECT_ENDPOINT environment variable is required.\n"
            "Find it in Azure AI Foundry portal -> Project -> Overview\n"
            "Format: https://<project-name>.<region>.api.azureml.ms"
        )
    
    model_deployment_name = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4o-mini")
    
    # Create project client with Azure credential (uses az login, managed identity, etc.)
    print("Authenticating with Azure (DefaultAzureCredential)...")
    credential = DefaultAzureCredential()
    
    print(f"Creating AI Project Client for: {project_endpoint}")
    project_client = AIProjectClient(
        endpoint=project_endpoint,
        credential=credential
    )
    
    # Try env var first, fall back to auto-discovery
    bing_connection_id = os.environ.get("BING_CONNECTION_ID")
    if bing_connection_id:
        print(f"Using Bing connection from environment variable")
        print(f"   Connection ID: {bing_connection_id}")
    else:
        print("BING_CONNECTION_ID not set, attempting auto-discovery...")
        bing_connection_id = get_bing_connection_id(project_client)
    
    # Initialize Bing Grounding tool
    # This configures Grounding with Bing Custom Search using your connection
    print("Initializing Bing Grounding tool...")
    bing = BingGroundingTool(connection_id=bing_connection_id)
    print("   Bing Custom Search grounding configured")
    
    # Load the system prompt
    print("Loading system prompt...")
    system_instructions = load_system_prompt()
    
    # Create the agent with Bing grounding
    print("Creating Ohio BMV agent...")
    with project_client:
        agent = project_client.agents.create_agent(
            model=model_deployment_name,
            name="ohio-bmv-online-assistant",
            instructions=system_instructions,
            tools=bing.definitions,  # Attach Bing Grounding tool
        )
        print(f"✅ Created agent: {agent.id}")
        print(f"   Name: {agent.name}")
        print(f"   Model: {model_deployment_name}")
        print(f"   Tools: Bing Custom Search Grounding (restricts to official BMV sources)")
    
    return agent, project_client

def test_agent_with_question(agent, project_client, question: str):
    """
    Test the agent with a sample question.
    
    Args:
        agent: The created agent
        project_client: The AI project client
        question: The question to ask
    """
    print(f"\n{'='*60}")
    print(f"Testing agent with question:")
    print(f"  {question}")
    print(f"{'='*60}\n")
    
    # Create a thread for the conversation
    thread = project_client.agents.threads.create()
    print(f"Created thread: {thread.id}")
    
    # Add the user message
    message = project_client.agents.messages.create(
        thread_id=thread.id,
        role="user",
        content=question,
    )
    print(f"Created message: {message['id']}")
    
    # Run the agent
    print("Running agent...")
    run = project_client.agents.runs.create_and_process(
        thread_id=thread.id,
        agent_id=agent.id,
    )
    print(f"Run completed with status: {run.status}")
    
    if run.status == "failed":
        print(f"❌ Run failed: {run.last_error}")
        return
    
    # Fetch and display messages
    print("\n" + "="*60)
    print("Conversation:")
    print("="*60)
    messages = project_client.agents.messages.list(thread_id=thread.id)
    for msg in reversed(list(messages)):
        role = msg.role.upper()
        content = msg.content[0].text.value if msg.content else ""
        print(f"\n{role}:")
        print(f"{content}")
    
    # Display run steps to show tool usage
    print("\n" + "="*60)
    print("Run Steps (Tool Usage):")
    print("="*60)
    run_steps = project_client.agents.run_steps.list(thread_id=thread.id, run_id=run.id)
    for step in run_steps:
        print(f"\nStep {step['id']}: {step['status']}")
        
        step_details = step.get("step_details", {})
        tool_calls = step_details.get("tool_calls", [])
        
        if tool_calls:
            print("  Tool calls:")
            for call in tool_calls:
                print(f"    - Type: {call.get('type')}")
                function_details = call.get("function", {})
                if function_details:
                    print(f"      Function: {function_details.get('name')}")

def main():
    """Main execution flow."""
    try:
        # Create the agent
        agent, project_client = create_ohio_bmv_agent()
        
        # Optional: Test with a sample question (requires re-creating the client)
        # test_agent_with_question(
        #     agent,
        #     project_client,
        #     "What documents do I need to renew my Ohio driver's license? "
        #     "Also, can you tell me about the fees?"
        # )
        
        print("\n" + "="*60)
        print("✅ Agent creation and testing completed successfully!")
        print(f"Agent ID: {agent.id}")
        print("\nTo use this agent:")
        print("1. Note the agent ID above")
        print("2. Use it in your application via the Azure AI Projects SDK")
        print("3. For address changes, add the MCP tool connection")
        print("="*60)
        
        # Keep the agent (don't delete it)
        # Uncomment the following if you want to clean up after testing:
        # with project_client:
        #     project_client.agents.delete_agent(agent.id)
        #     print(f"\n🗑️  Deleted agent: {agent.id}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise

if __name__ == "__main__":
    main()
