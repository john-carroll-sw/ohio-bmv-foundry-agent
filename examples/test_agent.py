"""
Test the Ohio BMV agent locally

This script allows you to interact with an existing agent and test its responses.
"""

import os
import sys
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# Load environment variables
load_dotenv()

def test_agent(agent_id: str, question: str):
    """
    Test an existing agent with a question.
    
    Args:
        agent_id: The ID of the agent to test
        question: The question to ask
    """
    project_endpoint = os.environ.get("PROJECT_ENDPOINT")
    if not project_endpoint:
        raise ValueError("PROJECT_ENDPOINT environment variable is required")
    
    print(f"Connecting to project: {project_endpoint}")
    print(f"Testing agent: {agent_id}")
    print(f"\nQuestion: {question}")
    print("="*60)
    
    # Create project client
    project_client = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential()
    )
    
    # Create a thread for the conversation
    thread = project_client.agents.threads.create()
    print(f"Created thread: {thread.id}")
    
    # Add the user message
    message = project_client.agents.messages.create(
        thread_id=thread.id,
        role="user",
        content=question,
    )
    print(f"Message sent\n")
    
    # Run the agent
    print("Agent is thinking...")
    run = project_client.agents.runs.create_and_process(
        thread_id=thread.id,
        agent_id=agent_id,
    )
    print(f"Run status: {run.status}\n")
    
    if run.status == "failed":
        print(f"❌ Run failed: {run.last_error}")
        return
    
    # Fetch and display messages
    print("="*60)
    print("RESPONSE:")
    print("="*60)
    messages = project_client.agents.messages.list(thread_id=thread.id)
    
    for msg in reversed(list(messages)):
        if msg.role == "assistant":
            content = msg.content[0].text.value if msg.content else ""
            print(content)
            print()
            
            # Show citations if available
            if hasattr(msg.content[0].text, 'annotations') and msg.content[0].text.annotations:
                print("\nCitations:")
                for i, annotation in enumerate(msg.content[0].text.annotations, 1):
                    if hasattr(annotation, 'url'):
                        print(f"  [{i}] {annotation.url}")
    
    # Display tool usage
    print("\n" + "="*60)
    print("TOOL USAGE:")
    print("="*60)
    run_steps = project_client.agents.run_steps.list(thread_id=thread.id, run_id=run.id)
    
    for step in run_steps:
        step_details = step.get("step_details", {})
        tool_calls = step_details.get("tool_calls", [])
        
        if tool_calls:
            for call in tool_calls:
                tool_type = call.get("type", "unknown")
                print(f"✓ Used tool: {tool_type}")
                
                if tool_type == "bing_grounding":
                    print(f"  (Searched Bing Custom Search for relevant BMV information)")

def main():
    """Main execution."""
    # Use the agent ID from the most recent creation
    # Can be passed as command line argument or update default below
    agent_id = sys.argv[1] if len(sys.argv) > 1 else "asst_xe5J832KDbgAHPCOGsM2X81Q"
    
    # Test questions
    questions = [
        "What documents do I need to renew my Ohio driver's license?",
        "How much does it cost to get a duplicate license in Ohio?",
        "What are the office hours for Ohio BMV locations?",
    ]
    
    print("Ohio BMV Agent Test")
    print("="*60)
    print(f"Agent ID: {agent_id}")
    print("="*60)
    print()
    
    # Test with the first question
    test_agent(agent_id, questions[0])
    
    # Uncomment to test more questions
    # for question in questions[1:]:
    #     print("\n\n")
    #     test_agent(agent_id, question)

if __name__ == "__main__":
    main()
