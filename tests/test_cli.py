"""Tests for CLI functionality."""

import sys
from unittest.mock import patch

import pytest


class TestCLI:
    """Tests for CLI."""

    def test_cli_module_importable(self):
        """Test that CLI module is importable."""
        from cooperbench import cli

        assert hasattr(cli, "main")

    def test_cli_help(self):
        """Test CLI help output."""
        from cooperbench.cli import main

        with patch.object(sys, "argv", ["cooperbench", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # --help should exit with 0
            assert exc_info.value.code == 0

    def test_cli_run_subcommand_exists(self):
        """Test run subcommand exists."""
        from cooperbench.cli import main

        with patch.object(sys, "argv", ["cooperbench", "run", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_cli_eval_subcommand_exists(self):
        """Test eval subcommand exists."""
        from cooperbench.cli import main

        with patch.object(sys, "argv", ["cooperbench", "eval", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
