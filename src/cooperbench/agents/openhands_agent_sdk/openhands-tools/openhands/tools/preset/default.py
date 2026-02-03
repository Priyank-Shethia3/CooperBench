"""Default preset configuration for OpenHands agents."""

import os
from openhands.sdk import Agent
from openhands.sdk.context.condenser import (
    LLMSummarizingCondenser,
)
from openhands.sdk.context.condenser.base import CondenserBase
from openhands.sdk.llm.llm import LLM
from openhands.sdk.logger import get_logger
from openhands.sdk.tool import Tool


logger = get_logger(__name__)


def register_default_tools(enable_browser: bool = True) -> None:
    """Register the default set of tools."""
    # Tools are now automatically registered when imported
    from openhands.tools.file_editor import FileEditorTool
    from openhands.tools.task_tracker import TaskTrackerTool
    from openhands.tools.terminal import TerminalTool

    logger.debug(f"Tool: {TerminalTool.name} registered.")
    logger.debug(f"Tool: {FileEditorTool.name} registered.")
    logger.debug(f"Tool: {TaskTrackerTool.name} registered.")

    if enable_browser:
        from openhands.tools.browser_use import BrowserToolSet

        logger.debug(f"Tool: {BrowserToolSet.name} registered.")
    
    # Register collaboration tools (only active when REDIS_URL is set)
    from openhands.tools.collaboration import ReceiveMessageTool, SendMessageTool
    # DEBUG [Hypothesis A/D - tool names at registration]
    print(f"[DEBUG-DEFAULT] Registering collab tools. SendMessageTool.name={SendMessageTool.name} ReceiveMessageTool.name={ReceiveMessageTool.name}", flush=True)
    logger.debug(f"Tool: {SendMessageTool.name} registered.")
    logger.debug(f"Tool: {ReceiveMessageTool.name} registered.")


def get_default_tools(
    enable_browser: bool = True,
) -> list[Tool]:
    """Get the default set of tool specifications for the standard experience.

    Args:
        enable_browser: Whether to include browser tools.
    """
    register_default_tools(enable_browser=enable_browser)

    # Import tools to access their name attributes
    from openhands.tools.file_editor import FileEditorTool
    from openhands.tools.task_tracker import TaskTrackerTool
    from openhands.tools.terminal import TerminalTool
    from openhands.tools.collaboration import ReceiveMessageTool, SendMessageTool

    tools = [
        Tool(name=TerminalTool.name),
        Tool(name=FileEditorTool.name),
        Tool(name=TaskTrackerTool.name),
        Tool(name=SendMessageTool.name),  # Only active when REDIS_URL is set
        Tool(name=ReceiveMessageTool.name),  # Only active when REDIS_URL is set
    ]
    if enable_browser:
        from openhands.tools.browser_use import BrowserToolSet

        tools.append(Tool(name=BrowserToolSet.name))
    
    # DEBUG [Hypothesis D - tool names returned]
    tool_names = [t.name for t in tools]
    print(f"[DEBUG-DEFAULT] get_default_tools() returning: {tool_names}", flush=True)
    
    return tools


def get_default_condenser(llm: LLM) -> CondenserBase:
    # Create a condenser to manage the context. The condenser will automatically
    # truncate conversation history when it exceeds max_size, and replaces the dropped
    # events with an LLM-generated summary.
    condenser = LLMSummarizingCondenser(llm=llm, max_size=80, keep_first=4)

    return condenser


def get_default_agent(
    llm: LLM,
    cli_mode: bool = False,
) -> Agent:
    tools = get_default_tools(
        # Disable browser tools in CLI mode
        enable_browser=not cli_mode,
    )
    agent = Agent(
        llm=llm,
        tools=tools,
        system_prompt_kwargs={"cli_mode": cli_mode},
        condenser=get_default_condenser(
            llm=llm.model_copy(update={"usage_id": "condenser"})
        ),
    )
    return agent
