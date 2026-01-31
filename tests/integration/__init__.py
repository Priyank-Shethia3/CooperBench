"""Integration tests requiring Modal sandboxes.

Run these tests with: pytest tests/integration/ --run-modal

These tests are skipped by default as they:
- Require Modal credentials and network access
- Create actual cloud sandboxes (costs money)
- Are slow (10-60 seconds per test)

Run before package releases to ensure end-to-end functionality.
"""
