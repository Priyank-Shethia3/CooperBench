"""Integration tests for GCP git server.

These tests require:
1. GCP credentials configured (gcloud auth application-default login)
2. GOOGLE_CLOUD_PROJECT environment variable set
3. Network access to GCP

Run with: pytest tests/integration/test_gcp_git.py -v
"""

import os

import pytest

# Skip all tests if GCP is not configured
pytestmark = pytest.mark.skipif(
    not os.environ.get("GOOGLE_CLOUD_PROJECT"),
    reason="GOOGLE_CLOUD_PROJECT not set - skipping GCP integration tests",
)


@pytest.fixture(scope="module")
def gcp_git_server():
    """Create a GCP git server for tests.

    Uses module scope to avoid creating a new VM for each test (~2min startup).
    """
    from cooperbench.agents.mini_swe_agent.connectors import create_git_server

    server = create_git_server(
        "gcp",
        run_id="test-git-server",
        machine_type="e2-micro",
    )
    yield server
    server.cleanup()


class TestGCPGitServer:
    """Integration tests for GCPGitServer."""

    def test_url_format(self, gcp_git_server):
        """Test the git URL has correct format."""
        url = gcp_git_server.url
        assert url.startswith("git://")
        assert url.endswith("/repo.git")
        assert ":9418/" in url

    def test_network_name_none_without_vpc(self, gcp_git_server):
        """Test network_name is None when not using VPC."""
        # Our fixture doesn't specify a network
        assert gcp_git_server.network_name is None


class TestGCPGitServerFactory:
    """Test the git server factory function (no GCP resources needed)."""

    def test_create_gcp_server_missing_project(self):
        """Test creating GCP server without project_id fails gracefully."""
        from unittest.mock import patch

        from cooperbench.agents.mini_swe_agent.connectors.git_servers.gcp import GCPGitServer

        # Mock _get_default_project to return None (simulates no gcloud config)
        with patch.object(GCPGitServer, "_get_default_project", return_value=None):
            with pytest.raises(ValueError, match="project_id required"):
                GCPGitServer.create(
                    run_id="test",
                    project_id=None,
                )

    def test_invalid_backend(self):
        """Test invalid backend raises error."""
        from cooperbench.agents.mini_swe_agent.connectors import create_git_server

        with pytest.raises(ValueError, match="Unknown git server backend"):
            create_git_server("invalid", run_id="test")

    def test_gcp_in_available_backends(self):
        """Test gcp is listed in available backends error message."""
        from cooperbench.agents.mini_swe_agent.connectors import create_git_server

        with pytest.raises(ValueError, match="gcp"):
            create_git_server("invalid", run_id="test")


class TestGCPGitServerWithVPC:
    """Test GCP git server with VPC network (requires VPC to exist)."""

    @pytest.mark.skipif(
        not os.environ.get("COOPERBENCH_TEST_VPC"),
        reason="COOPERBENCH_TEST_VPC not set - skipping VPC tests",
    )
    def test_vpc_mode(self):
        """Test git server in VPC mode."""
        from cooperbench.agents.mini_swe_agent.connectors import create_git_server

        vpc_name = os.environ.get("COOPERBENCH_TEST_VPC")

        server = create_git_server(
            "gcp",
            run_id="test-vpc-git",
            network=vpc_name,
            machine_type="e2-micro",
        )

        try:
            # URL should use internal IP (10.x.x.x)
            url = server.url
            assert url.startswith("git://10.")
            assert server.network_name == vpc_name
        finally:
            server.cleanup()


class TestGCPGitServerWithAgent:
    """Test git server integration with GCP agent."""

    def test_agent_can_clone_and_push(self, gcp_git_server):
        """Test that a GCP agent can clone from and push to the git server."""
        from cooperbench.agents.mini_swe_agent.environments import get_environment

        GCPEnv = get_environment("gcp")
        env = GCPEnv(
            image="python:3.11-slim",
            machine_type="e2-small",
            cwd="/workspace",
        )

        try:
            # Install git
            result = env.execute("apt-get update && apt-get install -y git")
            assert result["returncode"] == 0, f"Failed to install git: {result['output']}"

            # Configure git
            env.execute("git config --global user.email 'test@test.com'")
            env.execute("git config --global user.name 'Test'")

            # Clone the repo
            git_url = gcp_git_server.url
            result = env.execute(f"git clone {git_url} repo")
            assert result["returncode"] == 0, f"Failed to clone: {result['output']}"

            # Create a file and commit
            env.execute("echo 'hello' > repo/test.txt")
            result = env.execute("cd repo && git add test.txt && git commit -m 'test'")
            assert result["returncode"] == 0, f"Failed to commit: {result['output']}"

            # Push to server
            result = env.execute("cd repo && git push origin master")
            assert result["returncode"] == 0, f"Failed to push: {result['output']}"

            # Clone again to verify
            result = env.execute(f"git clone {git_url} repo2")
            assert result["returncode"] == 0, f"Failed to clone again: {result['output']}"

            # Verify file exists
            result = env.execute("cat repo2/test.txt")
            assert result["returncode"] == 0, f"Failed to read file: {result['output']}"
            assert "hello" in result["output"]

        finally:
            env.cleanup()
