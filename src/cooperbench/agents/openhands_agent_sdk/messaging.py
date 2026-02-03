"""Collaboration prompt generation for multi-agent mode.

Messaging tools (SendMessageTool, ReceiveMessageTool) run inside Modal sandbox.
This module only provides the prompt that explains collaboration to the agent.
"""


def get_collaboration_system_prompt(
    agent_id: str,
    agents: list[str],
    messaging_enabled: bool = True,
    git_enabled: bool = False,
) -> str:
    """Generate collaboration instructions for the agent.
    
    Mirrors the prompt style from mini_swe_agent/config/mini.yaml:
    short, factual, unopinionated.
    
    Args:
        agent_id: This agent's ID
        agents: All agent IDs in the team
        messaging_enabled: Whether messaging is available
        git_enabled: Whether shared git is available
        
    Returns:
        System prompt addition with team coordination instructions
    """
    teammates = [a for a in agents if a != agent_id]
    
    prompt = f"""

You are {agent_id} working as a team with: {', '.join(teammates)}.
You are all working on related features in the same codebase. Each agent has their own workspace.
"""

    if git_enabled:
        prompt += "A shared git remote called 'team' is available for code sharing between agents.\n"
    
    if messaging_enabled:
        prompt += "Use send_message and receive_messages tools to coordinate.\n"

    prompt += """
<collaboration>
Each agent has their own workspace. At the end, all agents' changes will be merged together.
**Important**: Coordinate to avoid merge conflicts - your patches must cleanly combine!
"""

    if git_enabled:
        prompt += f"""
## Git
A shared remote called 'team' is configured. Your branch is `{agent_id}`.
Teammates' branches are at `team/<name>` (e.g., `team/{teammates[0] if teammates else 'agent_1'}`).

Syntax:
```
git push team {agent_id}
git fetch team
```
"""

    if messaging_enabled:
        prompt += f"""
## Messaging
Use the **send_message** tool to send messages to teammates.
Use the **receive_messages** tool to check for messages from teammates.

Parameters for send_message:
- `recipient`: The agent to send to (e.g., `{teammates[0] if teammates else 'agent_1'}`)
- `content`: Your message

Call receive_messages periodically to check for new messages.
"""

    prompt += "</collaboration>"
    
    return prompt
