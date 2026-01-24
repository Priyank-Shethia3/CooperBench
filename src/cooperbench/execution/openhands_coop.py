"""
OpenHands Coop agent implementation for CooperBench execution.

Runs two agents in parallel with MCP communication for coordinated code generation.
"""

import asyncio
import json
import logging
import os
import shutil
import sqlite3
import time
from pathlib import Path

from cooperbench.execution.agent import BaseAgent
from cooperbench.execution.prompt import render_task_prompt

logger = logging.getLogger(__name__)

EXECUTION_TIMEOUT_SECONDS = 25 * 60


class OpenHandsCoopAgent(BaseAgent):
    """OpenHands Coop agent for multi-agent execution with MCP communication."""

    def __init__(
        self,
        agent_workspace_path: Path,
        prompt: str,
        config: dict | None = None,
    ) -> None:
        """Initialize the agent with the agent_workspace_path and prompt."""
        super().__init__(agent_workspace_path, prompt, config)
        self.container_name = self.config.get("container_name")

    def remove_existing_container(self) -> bool:
        """Check for and remove existing container with the same name."""
        import subprocess

        try:
            check_cmd = [
                "docker",
                "ps",
                "-a",
                "--filter",
                f"name={self.container_name}",
                "--format",
                "{{.Names}}\t{{.Status}}",
            ]
            result = subprocess.run(check_cmd, capture_output=True, text=True, check=True)

            for line in result.stdout.strip().split("\n"):
                if "\t" in line:
                    container_name, _status = line.split("\t", 1)
                    subprocess.run(["docker", "rm", "-f", container_name], check=True)

            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error checking/removing container: {e}")
            return False

    async def run_openhands(self) -> bool:
        """Run the OpenHands Docker command with MCP support asynchronously."""
        import subprocess

        self.remove_existing_container()

        agent_workspace_path_absolute = str(self.agent_workspace_path.absolute())
        host_ohl_state = os.path.expanduser("~/.openhands")

        # Google credentials mount
        credentials_path = self.config.get("GOOGLE_APPLICATION_CREDENTIALS", "")
        credentials_filename = os.path.basename(credentials_path) if credentials_path else ""
        container_credentials_path = f"/opt/credentials/{credentials_filename}" if credentials_filename else ""

        # MCP config from config
        mcp_server_file = self.config.get("mcp_server_file")
        shared_db_dir = self.config.get("shared_db_dir")
        config_file = self.config.get("config_file")
        logs_dir = self.config.get("logs_dir")

        # Build agent volumes string (workspace + MCP server + shared db)
        agent_volumes = f"{agent_workspace_path_absolute}:/workspace:rw,{mcp_server_file}:/app/mcp_communication_server.py:ro,{shared_db_dir}:/app/db:rw"

        command = [
            "docker",
            "run",
            "--rm",
            "--pull=never",
            "-e",
            f"SANDBOX_RUNTIME_CONTAINER_IMAGE={self.config['RUNTIME_IMAGE']}",
            "-e",
            f"SANDBOX_USER_ID={os.getuid()}",
            "-e",
            f"SANDBOX_VOLUMES={agent_volumes}",
            "-e",
            f"LLM_PROVIDER={self.config.get('LLM_PROVIDER', '')}",
            "-e",
            f"LLM_API_KEY={self.config.get('LLM_API_KEY', '')}",
            "-e",
            f"LLM_API_VERSION={self.config.get('LLM_API_VERSION', '')}",
            "-e",
            f"LLM_BASE_URL={self.config.get('LLM_BASE_URL', '')}",
            "-e",
            f"LLM_MODEL={self.config.get('LLM_MODEL', '')}",
            "-e",
            "PYTHONDONTWRITEBYTECODE=1",
            "-e",
            f"GOOGLE_API_KEY={self.config.get('GOOGLE_API_KEY', '')}",
            "-e",
            f"GEMINI_API_KEY={self.config.get('GEMINI_API_KEY', '')}",
            "-e",
            f"VERTEXAI_PROJECT={self.config.get('VERTEXAI_PROJECT', '')}",
            "-e",
            f"VERTEXAI_LOCATION={self.config.get('VERTEXAI_LOCATION', '')}",
            "-e",
            f"GOOGLE_APPLICATION_CREDENTIALS={container_credentials_path if credentials_path else ''}",
            "-e",
            "LOG_ALL_EVENTS=true",
            "-e",
            "DEBUG=true",
            "-e",
            f"SAVE_TRAJECTORY_PATH={self.config.get('local_trajectory_path')}",
            "-e",
            f"OPENHANDS_AGENT_ID={self.config.get('agent_id', 'agent_1')}",
            "-v",
            "/var/run/docker.sock:/var/run/docker.sock",
            "-v",
            f"{host_ohl_state}:/.openhands",
            "-v",
            f"{config_file}:/app/config.toml:ro",
            "-v",
            f"{logs_dir}:/logs:rw",
            *(["-v", f"{credentials_path}:{container_credentials_path}"] if credentials_path else []),
            "--add-host",
            "host.docker.internal:host-gateway",
            "--name",
            self.container_name,
            self.config["OPENHANDS_IMAGE"],
            "python",
            "-m",
            "openhands.core.main",
            "--config-file",
            "/app/config.toml",
            "-i",
            "100",
            "--log-level",
            "DEBUG",
            "-t",
            self.prompt,
        ]

        try:
            logger.info(f"Running OpenHands Coop in directory: {agent_workspace_path_absolute}")

            agent_num = self.config.get("agent_id", "agent_1").split("_")[1]
            output_log = Path(logs_dir) / f"agent_{agent_num}_output.log"

            with open(output_log, "w") as log_file:
                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=log_file,
                    stderr=asyncio.subprocess.STDOUT,
                )
                await process.wait()

            if process.returncode == 0:
                logger.info("Successfully ran OpenHands Coop")
                return True
            else:
                logger.error(f"OpenHands Coop failed with return code {process.returncode}")
                if output_log.exists():
                    with open(output_log) as f:
                        log_content = f.read()
                        logger.error(f"Agent output: {log_content[-1000:]}")
                return False
        except Exception as e:
            logger.error(f"Error running OpenHands Coop: {e}")
            return False

    async def execute(self) -> bool:
        """Execute the agent workflow asynchronously."""
        start_time = time.time()
        run_success = False

        try:
            run_success = await self.run_openhands()
        finally:
            duration = round(time.time() - start_time, 2)
            if run_success:
                logger.info(f"{type(self).__name__} execution completed successfully in {duration}s")
            else:
                logger.error(f"{type(self).__name__} execution failed after {duration}s")
            self.cleanup()

        return run_success

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
        """Synchronous run - not used for coop mode."""
        raise NotImplementedError("Use execute() for async coop execution")


def _resolve_api_key(model: str) -> str:
    """Resolve API key based on model type."""
    model_lower = model.lower()
    if "claude" in model_lower or "anthropic" in model_lower:
        return os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    elif "gemini" in model_lower or "google" in model_lower:
        return os.getenv("LLM_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
    elif "gpt" in model_lower or "openai" in model_lower:
        return os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
    else:
        return os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY") or ""


def _clean_model_name(model: str) -> str:
    """Normalize model name for file naming."""
    model_lower = model.lower()
    if "minimax" in model_lower:
        return "minimax"
    if "claude" in model_lower:
        return "claude"
    if "gemini" in model_lower:
        return "gemini"
    if "qwen" in model_lower:
        return "qwen"
    return "gpt5"


async def run_coop_execution(
    workspace_1: Path,
    workspace_2: Path,
    feature_desc_1: str,
    feature_desc_2: str,
    plan_1: str,
    plan_2: str,
    model1: str,
    model2: str,
    feature1_id: int,
    feature2_id: int,
    repo_name: str,
    task_id: int,
    k: int = 1,
) -> tuple[bool, Path | None, Path | None, Path | None, list[Path]]:
    """
    Run parallel OpenHands agents with MCP communication.

    Returns:
        Tuple of (success, traj1_path, traj2_path, conversation_json_path, agent_log_paths)
    """
    # Setup paths for MCP from the openhands_colab submodule
    base_dir = Path(__file__).parent / "openhands_colab"
    logs_dir = base_dir / "logs_colab"
    config_file = base_dir / "config.toml"
    mcp_server_file = base_dir / "mcp_communication_server.py"

    # Verify required files exist
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")
    if not mcp_server_file.exists():
        raise FileNotFoundError(f"MCP server file not found: {mcp_server_file}")

    # Create final logs directory
    feature_min = min(feature1_id, feature2_id)
    feature_max = max(feature1_id, feature2_id)
    final_logs_dir = (
        Path("logs")
        / "coop"
        / repo_name
        / f"task{task_id}"
        / f"feature{feature_min}_feature{feature_max}"
    )
    shared_db_dir = final_logs_dir / "mcp_db"

    # Remove existing MCP database to prevent contamination
    if shared_db_dir.exists():
        shutil.rmtree(shared_db_dir)
        logger.info(f"Removed existing MCP database directory: {shared_db_dir}")
    shared_db_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(exist_ok=True)

    logger.info(f"MCP database: {shared_db_dir}")

    # Resolve API keys
    llm_api_key_1 = _resolve_api_key(model1)
    llm_api_key_2 = _resolve_api_key(model2)

    # Container images
    runtime_image = "colab/openhands_runtime_colab:latest"
    openhands_image = "colab/openhands_colab:latest"

    model1_clean = _clean_model_name(model1)
    model2_clean = _clean_model_name(model2)
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # Render prompts for both agents using coop template
    prompt_1 = render_task_prompt(
        feature_description=feature_desc_1,
        plan=plan_1,
        template_name="coop_prompt.j2",
        agent_id=f"agent_{feature1_id}",
        workspace="/workspace",
    )

    prompt_2 = render_task_prompt(
        feature_description=feature_desc_2,
        plan=plan_2,
        template_name="coop_prompt.j2",
        agent_id=f"agent_{feature2_id}",
        workspace="/workspace",
    )

    # Create agents
    agents = []
    for feature_id, workspace, prompt, model, model_clean, llm_api_key in [
        (feature1_id, workspace_1, prompt_1, model1, model1_clean, llm_api_key_1),
        (feature2_id, workspace_2, prompt_2, model2, model2_clean, llm_api_key_2),
    ]:
        container_name = f"openhands-agent_{feature_id}-{timestamp}"
        trajectory_filename = f"execution_traj_{model_clean}_k{k}_feature{feature_id}.json"

        # Write agent ID to workspace for MCP server identification
        (workspace / "agent_id.txt").write_text(f"agent_{feature_id}")

        config = {
            "LLM_MODEL": model,
            "local_trajectory_path": f"/logs/{trajectory_filename}",
            "container_name": container_name,
            "agent_id": f"agent_{feature_id}",
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
            "mcp_server_file": str(mcp_server_file),
            "shared_db_dir": str(shared_db_dir.absolute()),
            "config_file": str(config_file),
            "logs_dir": str(logs_dir),
            "trajectory_filename": trajectory_filename,
        }

        agent = OpenHandsCoopAgent(workspace, prompt, config)
        agents.append(agent)

    # Run both agents in parallel
    async def run_agent_async(agent: OpenHandsCoopAgent) -> bool:
        return await agent.execute()

    agent_tasks = [
        asyncio.create_task(run_agent_async(agents[0])),
        asyncio.create_task(run_agent_async(agents[1])),
    ]
    timed_out = False
    agent_log_paths: list[Path] = []

    try:
        results = await asyncio.wait_for(
            asyncio.gather(*agent_tasks, return_exceptions=True),
            timeout=EXECUTION_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        timed_out = True
        logger.error(f"Timed out after {EXECUTION_TIMEOUT_SECONDS}s; cancelling tasks.")
        for task in agent_tasks:
            task.cancel()
        results = await asyncio.gather(*agent_tasks, return_exceptions=True)
    except Exception as e:
        logger.error(f"Error running agents in parallel: {e}")
        results = await asyncio.gather(*agent_tasks, return_exceptions=True)
    finally:
        for task in agent_tasks:
            if not task.done():
                task.cancel()

    success_1 = results[0] if len(results) > 0 else False
    success_2 = results[1] if len(results) > 1 else False

    if timed_out:
        logger.warning(f"Execution timed out after {EXECUTION_TIMEOUT_SECONDS}s; treating as success.")
        both_succeeded = True
    else:
        both_succeeded = isinstance(success_1, bool) and isinstance(success_2, bool) and success_1 and success_2

    if isinstance(success_1, Exception):
        logger.error(f"Agent {feature1_id} failed with exception: {success_1}")
    if isinstance(success_2, Exception):
        logger.error(f"Agent {feature2_id} failed with exception: {success_2}")

    traj1_path = None
    traj2_path = None
    conversation_json_path = None

    if both_succeeded:
        logger.info("Both agents completed successfully!")

        try:
            for i, agent in enumerate(agents):
                # Move trajectory files
                traj_filename = agent.config["trajectory_filename"]
                source_traj = logs_dir / traj_filename
                dest_traj = final_logs_dir / traj_filename

                if source_traj.exists():
                    shutil.move(str(source_traj), str(dest_traj))

                # Move agent output logs
                agent_identifier = agent.config.get("agent_id", f"agent_{i + 1}")
                agent_log_filename = f"{agent_identifier}_output.log"
                source_log = logs_dir / agent_log_filename
                dest_log_name = f"{agent_identifier}_output_{_clean_model_name(agent.config['LLM_MODEL'])}.log"
                dest_log = final_logs_dir / dest_log_name

                if source_log.exists():
                    shutil.move(str(source_log), str(dest_log))
                    agent_log_paths.append(dest_log)

            # Export conversation data (MCP messages)
            db_path = shared_db_dir / "openhands_messages.db"
            conversation_json = final_logs_dir / f"conversation_{model1_clean}.json"

            if db_path.exists():
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM messages ORDER BY timestamp")
                messages = []
                columns = [description[0] for description in cursor.description]

                for row in cursor.fetchall():
                    message = dict(zip(columns, row))
                    messages.append(message)

                conn.close()

                with open(conversation_json, "w") as f:
                    json.dump(
                        {
                            "messages": messages,
                            "export_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "total_messages": len(messages),
                        },
                        f,
                        indent=2,
                    )

            # Collect file paths
            for i, agent in enumerate(agents):
                traj_filename = agent.config["trajectory_filename"]
                traj_local_path = final_logs_dir / traj_filename
                if traj_local_path.exists():
                    if i == 0:
                        traj1_path = traj_local_path
                    else:
                        traj2_path = traj_local_path

            conversation_json_path = conversation_json if conversation_json.exists() else None

        except Exception as e:
            logger.error(f"Error moving/processing files: {e}")
    else:
        logger.error(f"Agent failures - Agent {feature1_id}: {success_1}, Agent {feature2_id}: {success_2}")

    # Cleanup both agents
    for agent in agents:
        try:
            agent.cleanup()
        except Exception as e:
            logger.warning(f"Error cleaning up agent: {e}")

    return both_succeeded, traj1_path, traj2_path, conversation_json_path, agent_log_paths
