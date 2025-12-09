"""
Check agent status and details
"""

import os
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

load_dotenv()

def check_agent(agent_id: str):
    """Check if an agent exists and get its details."""
    project_endpoint = os.environ.get("PROJECT_ENDPOINT")
    
    project_client = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential()
    )
    
    try:
        agent = project_client.agents.get_agent(agent_id)
        print(f"✅ Agent found!")
        print(f"   ID: {agent.id}")
        print(f"   Name: {agent.name}")
        print(f"   Model: {agent.model}")
        print(f"   Created: {agent.created_at}")
        print(f"   Tools: {len(agent.tools)} tool(s) configured")
        
        if agent.tools:
            for i, tool in enumerate(agent.tools, 1):
                print(f"      {i}. {tool.get('type', 'unknown')}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    agent_id = "asst_DiPfxf4ihI9UFeuNVAHSfnv4"
    print(f"Checking agent: {agent_id}\n")
    check_agent(agent_id)
