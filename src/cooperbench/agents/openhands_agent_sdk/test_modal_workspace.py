#!/usr/bin/env python3
"""Test script to verify ModalWorkspace works correctly."""

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
from openhands.workspace.modal import ModalWorkspace


def test_basic_execution():
    """Test basic command execution in Modal Sandbox."""
    print("=" * 60)
    print("TEST 1: Basic Command Execution")
    print("=" * 60)

    with ModalWorkspace(
        working_dir="/workspace",
        image="python:3.11-slim",
        timeout=300,  # 5 minutes for testing
    ) as workspace:
        # Test simple command
        result = workspace.execute_command("echo 'Hello from Modal!'")
        print(f"Command: echo 'Hello from Modal!'")
        print(f"Output: {result.stdout.strip()}")
        print(f"Exit code: {result.exit_code}")
        assert result.exit_code == 0
        assert "Hello from Modal!" in result.stdout
        print("✅ Passed\n")


def test_file_operations():
    """Test file upload and download."""
    print("=" * 60)
    print("TEST 2: File Upload/Download")
    print("=" * 60)

    with ModalWorkspace(
        working_dir="/workspace",
        image="python:3.11-slim",
        timeout=300,
    ) as workspace:
        # Create a temp file locally
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test content from local machine!")
            local_file = f.name

        try:
            # Upload to sandbox
            upload_result = workspace.file_upload(
                source_path=local_file,
                destination_path="/workspace/uploaded.txt"
            )
            print(f"Upload: {upload_result.success}")
            assert upload_result.success, f"Upload failed: {upload_result.error}"

            # Verify file exists in sandbox
            result = workspace.execute_command("cat /workspace/uploaded.txt")
            print(f"Content in sandbox: {result.stdout.strip()}")
            assert "Test content from local machine!" in result.stdout

            # Download back
            download_path = tempfile.mktemp(suffix=".txt")
            download_result = workspace.file_download(
                source_path="/workspace/uploaded.txt",
                destination_path=download_path
            )
            print(f"Download: {download_result.success}")
            assert download_result.success, f"Download failed: {download_result.error}"

            # Verify downloaded content
            with open(download_path) as f:
                downloaded_content = f.read()
            print(f"Downloaded content: {downloaded_content}")
            assert downloaded_content == "Test content from local machine!"

            # Cleanup
            os.unlink(download_path)

        finally:
            os.unlink(local_file)

        print("✅ Passed\n")


def test_agent_with_modal():
    """Test OpenHands agent with ModalWorkspace."""
    print("=" * 60)
    print("TEST 3: Agent with ModalWorkspace")
    print("=" * 60)

    # Check for API key
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("⚠️  Skipped (no GEMINI_API_KEY or GOOGLE_API_KEY)")
        return

    from pydantic import SecretStr
    from openhands.sdk import LLM, Agent, Conversation, Tool
    from openhands.sdk.tool import register_tool
    from openhands.tools.terminal import TerminalTool
    from openhands.tools.file_editor import FileEditorTool

    # Create LLM
    llm = LLM(
        model="gemini/gemini-2.0-flash",
        api_key=SecretStr(api_key),
    )

    # Register tools
    register_tool(TerminalTool.name, TerminalTool)
    register_tool(FileEditorTool.name, FileEditorTool)

    # Create agent
    agent = Agent(
        llm=llm,
        tools=[
            Tool(name=TerminalTool.name),
            Tool(name=FileEditorTool.name),
        ],
    )

    # Create ModalWorkspace
    with ModalWorkspace(
        working_dir="/workspace",
        image="python:3.11-slim",
        timeout=300,
    ) as workspace:
        print(f"Modal Sandbox ID: {workspace._sandbox.object_id if workspace._sandbox else 'N/A'}")

        # Create conversation with Modal workspace
        conversation = Conversation(agent=agent, workspace=workspace)

        # Send a task
        task = "Create a Python file called test.py that prints 'Hello from Modal!' when executed"
        print(f"\nTask: {task}")
        print("-" * 50)

        conversation.send_message(task)
        conversation.run()

        # Verify by running the created file
        result = workspace.execute_command("python /workspace/test.py")
        print(f"\nExecution result: {result.stdout.strip()}")

        if "Hello from Modal!" in result.stdout:
            print("✅ Passed")
        else:
            print("⚠️  File created but output different than expected")

        print(f"\nConversation stats:")
        print(f"  Events: {len(conversation.state.events)}")


def main():
    print("\n🚀 Testing ModalWorkspace for OpenHands SDK\n")

    try:
        test_basic_execution()
        test_file_operations()
        test_agent_with_modal()

        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
