"""
OpenHands agent implementation for CooperBench execution.

Runs code generation using the OpenHands framework in a Docker container.
"""

import logging
import os
import subprocess
from pathlib import Path

from cooperbench.execution.agent import BaseAgent

logger = logging.getLogger(__name__)


class OpenHandsAgent(BaseAgent):
    """OpenHands agent implementation that runs a Docker container."""

    def __init__(
        self,
        agent_workspace_path: Path,
        prompt: str,
        config: dict | None = None,
    ) -> None:
        """Initialize the agent with workspace and prompt."""
        super().__init__(agent_workspace_path, prompt, config)
        self.container_name = self.config.get("container_name")

    def remove_existing_container(self) -> bool:
        """Check for and remove existing container with the same name."""
        try:
            check_cmd = [
                "docker",
                "ps",
                "-a",
                "--filter",
                "name=openhands",
                "--format",
                "{{.Names}}\t{{.Status}}",
            ]
            result = subprocess.run(check_cmd, capture_output=True, text=True, check=True)

            for line in result.stdout.strip().split("\n"):
                if "\t" in line:
                    container_name, status = line.split("\t", 1)
                    if not status.startswith("Up "):
                        subprocess.run(["docker", "rm", "-f", container_name], check=True)

            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error checking/removing container: {e}")
            return False

    def run_openhands(self) -> bool:
        """Run the OpenHands Docker command."""
        self.remove_existing_container()

        agent_workspace_absolute = str(self.agent_workspace_path.absolute())

        credentials_path = self.config.get("GOOGLE_APPLICATION_CREDENTIALS", "")
        credentials_filename = os.path.basename(credentials_path)
        container_credentials_path = f"/opt/credentials/{credentials_filename}"

        host_ohl_state = os.path.expanduser("~/.openhands")
        sandbox_volumes = f"{agent_workspace_absolute}:/workspace:rw"

        command = [
            "docker",
            "run",
            "--pull=never",  # Use local images, don't try to pull from registry
            "-e",
            f"SANDBOX_RUNTIME_CONTAINER_IMAGE={self.config['RUNTIME_IMAGE']}",
            "-e",
            f"SANDBOX_USER_ID={os.getuid()}",
            "-e",
            f"SANDBOX_VOLUMES={sandbox_volumes}",
            "-e",
            f"LLM_PROVIDER={self.config.get('LLM_PROVIDER', '')}",
            "-e",
            f"GOOGLE_APPLICATION_CREDENTIALS={container_credentials_path if credentials_path else ''}",
            "-e",
            f"VERTEXAI_PROJECT={self.config.get('VERTEXAI_PROJECT', '')}",
            "-e",
            f"VERTEXAI_LOCATION={self.config.get('VERTEXAI_LOCATION', '')}",
            "-e",
            f"LLM_BASE_URL={self.config.get('LLM_BASE_URL', '')}",
            "-e",
            f"LLM_API_VERSION={self.config.get('LLM_API_VERSION', '')}",
            "-e",
            f"LLM_API_KEY={self.config.get('LLM_API_KEY', '')}",
            "-e",
            f"LLM_MODEL={self.config.get('LLM_MODEL', '')}",
            "-e",
            "PYTHONDONTWRITEBYTECODE=1",
            "-e",
            "LOG_ALL_EVENTS=true",
            "-e",
            f"SAVE_TRAJECTORY_PATH={self.config.get('local_trajectory_path')}",
            "-v",
            f"{agent_workspace_absolute}:/opt/workspace_base:rw",
            "-v",
            f"{Path.cwd()}/logs:/logs:rw",
            *(["-v", f"{credentials_path}:{container_credentials_path}"] if credentials_path else []),
            "-v",
            "/var/run/docker.sock:/var/run/docker.sock",
            "-v",
            f"{host_ohl_state}:/.openhands",
            "-v",
            f"{os.path.expanduser('~')}/.openhands-state:/.openhands-state",
            "--add-host",
            "host.docker.internal:host-gateway",
            "--name",
            self.container_name,
            self.config["OPENHANDS_IMAGE"],
            "python",
            "-m",
            "openhands.core.main",
            "-i",
            "100",
            "-t",
            self.prompt,
        ]

        try:
            logger.info(f"Running OpenHands in directory: {agent_workspace_absolute}")
            subprocess.run(command, check=True)
            logger.info("Successfully ran OpenHands")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running OpenHands: {e}")
            return False

    def cleanup(self) -> bool:
        """Remove the docker container."""
        success = True
        try:
            self.remove_existing_container()
        except Exception as e:
            logger.error(f"Error removing docker container: {e}")
            success = False
        return success

    def run(self) -> bool:
        """Run the OpenHands agent workflow."""
        try:
            if not self.run_openhands():
                logger.error("Failed to run OpenHands")
                return False
            return True
        except Exception as e:
            logger.error(f"Error in OpenHands agent workflow: {e}")
            return False


def _resolve_api_key(model: str) -> str:
    """Resolve API key based on model type."""
    if "claude" in model.lower() or "anthropic" in model.lower():
        return os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    elif "gpt" in model.lower() or "openai" in model.lower():
        return os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
    elif "gemini" in model.lower() or "google" in model.lower():
        return os.getenv("LLM_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
    else:
        return os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY") or ""


async def run_execution(
    agent_workspace_path: Path,
    prompt: str,
    model: str,
    local_trajectory_path: Path,
    container_name: str,
    use_colab_images: bool = False,
) -> bool:
    """Run OpenHands execution.

    Args:
        agent_workspace_path: Path to the agent workspace directory
        prompt: Pre-rendered prompt to use
        model: LLM model to use
        local_trajectory_path: Path to save the execution trajectory log
        container_name: Docker container name to use
        use_colab_images: If True, use custom colab images for coop mode

    Returns:
        bool: Success status
    """
    # Default images based on mode
    if use_colab_images:
        default_runtime = "colab/openhands_runtime_colab:latest"
        default_openhands = "colab/openhands_colab:latest"
    else:
        default_runtime = "docker.all-hands.dev/all-hands-ai/runtime:0.54-nikolaik"
        default_openhands = "docker.all-hands.dev/all-hands-ai/openhands:0.54"

    runtime_image = (
        os.getenv("RUNTIME_IMAGE")
        or os.getenv("OPENHANDS_RUNTIME_IMAGE")
        or default_runtime
    )
    openhands_image = os.getenv("OPENHANDS_IMAGE", default_openhands)

    llm_api_key = _resolve_api_key(model)

    config = {
        "LLM_MODEL": model,
        "local_trajectory_path": "/" + str(local_trajectory_path),
        "container_name": container_name,
        "RUNTIME_IMAGE": runtime_image,
        "OPENHANDS_IMAGE": openhands_image,
        "LLM_PROVIDER": os.getenv("LLM_PROVIDER", ""),
        "LLM_API_KEY": llm_api_key,
        "LLM_API_VERSION": os.getenv("LLM_API_VERSION", ""),
        "LLM_BASE_URL": os.getenv("LLM_BASE_URL", ""),
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", "")),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
        "VERTEXAI_PROJECT": os.getenv("VERTEXAI_PROJECT", ""),
        "VERTEXAI_LOCATION": os.getenv("VERTEXAI_LOCATION", ""),
        "GOOGLE_APPLICATION_CREDENTIALS": os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
    }

    agent = OpenHandsAgent(agent_workspace_path, prompt, config)
    return agent.execute()
