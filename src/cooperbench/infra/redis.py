"""Redis connection management."""

import subprocess
import time

from cooperbench.utils import console


def ensure_redis(redis_url: str = "redis://localhost:6379") -> None:
    """Ensure Redis is running, auto-start via Docker if needed."""
    import redis as redis_lib

    client = redis_lib.from_url(redis_url)
    try:
        client.ping()
        console.print("  [dim]redis[/dim] [green]connected[/green]")
        return
    except redis_lib.ConnectionError:
        pass

    console.print("  [dim]redis[/dim] [yellow]starting via docker...[/yellow]")
    try:
        subprocess.run(
            ["docker", "run", "-d", "--name", "cooperbench-redis", "-p", "6379:6379", "redis:alpine"],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        subprocess.run(["docker", "start", "cooperbench-redis"], capture_output=True)
    except FileNotFoundError:
        console.print("[red]error:[/red] Docker not found. Install Docker or Redis.")
        raise SystemExit(1)

    for _ in range(10):
        time.sleep(0.5)
        try:
            client.ping()
            console.print("  [dim]redis[/dim] [green]started[/green]")
            return
        except redis_lib.ConnectionError:
            pass

    console.print("[red]error:[/red] Failed to start Redis")
    raise SystemExit(1)
