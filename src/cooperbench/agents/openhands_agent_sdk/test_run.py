#!/usr/bin/env python3
"""Simple test script to verify OpenHands SDK runs correctly."""

import os
import sys
import tempfile

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add the package paths for namespace imports
SDK_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SDK_ROOT, "openhands-sdk"))
sys.path.insert(0, os.path.join(SDK_ROOT, "openhands-tools"))
sys.path.insert(0, os.path.join(SDK_ROOT, "openhands-workspace"))

# Now we can import
from openhands.sdk import LLM, Agent, Conversation, Tool
from openhands.tools.terminal import TerminalTool
from openhands.tools.file_editor import FileEditorTool


def main():
    # Use Gemini Flash (free tier friendly)
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Please set GEMINI_API_KEY or GOOGLE_API_KEY environment variable")
        return

    model = "gemini/gemini-2.0-flash"

    print(f"Using model: {model}")

    # Create LLM
    from pydantic import SecretStr
    llm = LLM(
        model=model,
        api_key=SecretStr(api_key),
    )

    # Register and get tools
    from openhands.sdk.tool import register_tool
    register_tool(TerminalTool.name, TerminalTool)
    register_tool(FileEditorTool.name, FileEditorTool)

    # Create agent with tools
    agent = Agent(
        llm=llm,
        tools=[
            Tool(name=TerminalTool.name),
            Tool(name=FileEditorTool.name),
        ],
    )

    # Create a temp workspace
    with tempfile.TemporaryDirectory() as workspace:
        print(f"Workspace: {workspace}")

        # Create conversation
        conversation = Conversation(agent=agent, workspace=workspace)

        # Send a simple task
        task = "Create a file called hello.txt with the content 'Hello from OpenHands!'"
        print(f"\nTask: {task}")
        print("-" * 50)

        conversation.send_message(task)
        conversation.run()

        # Check result
        hello_file = os.path.join(workspace, "hello.txt")
        if os.path.exists(hello_file):
            with open(hello_file) as f:
                print(f"\n✅ Success! File content: {f.read()}")
        else:
            print("\n❌ File was not created")

        # Print conversation stats
        print(f"\nConversation stats:")
        print(f"  Events: {len(conversation.state.events)}")


if __name__ == "__main__":
    main()
