"""Development scripts for Pidgin."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.prompt import Confirm

console = Console()

# Nord color theme
NORD_RED = "[#BF616A]"
NORD_GREEN = "[#A3BE8C]"
NORD_YELLOW = "[#EBCB8B]"
NORD_BLUE = "[#88C0D0]"
NORD_ORANGE = "[#D08770]"
NORD_DARK = "[#4C566A]"


def run_command(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    console.print(f"{NORD_DARK}Running: {' '.join(cmd)}[/]")
    return subprocess.run(cmd, check=check)


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


# === Code Quality Commands ===


@click.command()
def format():
    """Format code with black and isort."""
    console.print(f"{NORD_YELLOW}Formatting code...[/]")
    project_root = get_project_root()
    
    run_command(["poetry", "run", "black", "pidgin", "tests"], check=False)
    run_command(["poetry", "run", "isort", "pidgin", "tests"], check=False)
    
    console.print(f"{NORD_GREEN}✓ Code formatted![/]")


@click.command()
def lint():
    """Run linting checks with flake8."""
    console.print(f"{NORD_YELLOW}Running linting checks...[/]")
    
    result = run_command(["poetry", "run", "flake8", "pidgin", "tests"], check=False)
    
    if result.returncode == 0:
        console.print(f"{NORD_GREEN}✓ Linting passed![/]")
    else:
        console.print(f"{NORD_RED}✗ Linting failed[/]")
        sys.exit(1)


@click.command()
def typecheck():
    """Run type checking with mypy."""
    console.print(f"{NORD_YELLOW}Running type checks...[/]")
    
    result = run_command(["poetry", "run", "mypy", "pidgin"], check=False)
    
    if result.returncode == 0:
        console.print(f"{NORD_GREEN}✓ Type checking passed![/]")
    else:
        console.print(f"{NORD_RED}✗ Type checking failed[/]")
        sys.exit(1)


@click.command()
def check():
    """Run all code quality checks (format, lint, typecheck)."""
    console.print(f"{NORD_BLUE}Running all code quality checks...[/]")
    
    # Run format first
    format.invoke(click.Context(format))
    
    # Then lint and typecheck
    lint.invoke(click.Context(lint))
    typecheck.invoke(click.Context(typecheck))
    
    console.print(f"{NORD_GREEN}✓ All checks passed![/]")


# === Testing Commands ===


@click.command()
@click.option("--unit", is_flag=True, help="Run unit tests only")
@click.option("--integration", is_flag=True, help="Run integration tests only")
@click.option("--slow", is_flag=True, help="Run slow tests")
@click.option("--cov", is_flag=True, help="Run with coverage")
@click.option("--failed", is_flag=True, help="Re-run failed tests")
@click.option("-k", "--pattern", help="Run tests matching pattern")
def test(unit: bool, integration: bool, slow: bool, cov: bool, failed: bool, pattern: Optional[str]):
    """Run tests with various options."""
    console.print(f"{NORD_YELLOW}Running tests...[/]")
    
    cmd = ["poetry", "run", "pytest", "-xvs"]
    
    if unit:
        cmd.extend(["-m", "unit"])
    elif integration:
        cmd.extend(["-m", "integration"])
    elif slow:
        cmd.append("--runslow")
    
    if cov:
        cmd.extend(["--cov=pidgin", "--cov-report=html", "--cov-report=term"])
    
    if failed:
        cmd.append("--lf")
    
    if pattern:
        cmd.extend(["-k", pattern])
    
    result = run_command(cmd, check=False)
    
    if result.returncode == 0:
        console.print(f"{NORD_GREEN}✓ Tests passed![/]")
        if cov:
            console.print(f"{NORD_DARK}Coverage report generated in htmlcov/[/]")
    else:
        console.print(f"{NORD_RED}✗ Tests failed[/]")
        sys.exit(1)


# === Build and Install Commands ===


@click.command()
def build():
    """Build the package with poetry."""
    console.print(f"{NORD_YELLOW}Building package...[/]")
    
    # Clean old builds
    dist_dir = get_project_root() / "dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    
    run_command(["poetry", "build"])
    console.print(f"{NORD_GREEN}✓ Package built![/]")


@click.command()
@click.option("--force", is_flag=True, help="Force reinstall")
def install_pipx(force: bool):
    """Install the package with pipx."""
    console.print(f"{NORD_YELLOW}Installing with pipx...[/]")
    
    # First build
    build.invoke(click.Context(build))
    
    # Find the wheel file
    dist_dir = get_project_root() / "dist"
    wheel_files = list(dist_dir.glob("*.whl"))
    
    if not wheel_files:
        console.print(f"{NORD_RED}✗ No wheel file found![/]")
        sys.exit(1)
    
    cmd = ["pipx", "install", str(wheel_files[0])]
    if force:
        cmd.append("--force")
    
    run_command(cmd)
    console.print(f"{NORD_GREEN}✓ Installed with pipx![/]")


# === Cleanup Commands ===


@click.command()
@click.option("--all", is_flag=True, help="Clean everything including output and config")
@click.option("--yes", is_flag=True, help="Skip confirmation prompts")
def clean(all: bool, yes: bool):
    """Clean build artifacts and optionally all generated files."""
    if all:
        console.print(f"{NORD_YELLOW}Cleaning all generated files...[/]")
    else:
        console.print(f"{NORD_YELLOW}Cleaning build artifacts...[/]")
    
    project_root = get_project_root()
    
    # Always clean these
    patterns = [
        "dist", "build", "*.egg-info",
        ".coverage", "htmlcov", ".pytest_cache", ".mypy_cache",
        "**/__pycache__", "**/*.pyc", "**/*.pyo"
    ]
    
    if all:
        # Add more aggressive cleanup
        patterns.extend([
            "pidgin_output", "notebooks",
            "~/.config/pidgin", "~/.pidgin.yaml",
            "pidgin.yaml", ".pidgin.yaml"
        ])
        
        if not yes and not Confirm.ask(
            f"{NORD_RED}This will delete all experiment data and config files. Continue?[/]"
        ):
            console.print(f"{NORD_YELLOW}Cleanup cancelled.[/]")
            return
    
    for pattern in patterns:
        if pattern.startswith("~/"):
            # Handle home directory paths
            path = Path.home() / pattern[2:]
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                console.print(f"{NORD_DARK}Removed: {path}[/]")
        elif pattern.startswith("**"):
            # Handle glob patterns
            for path in project_root.rglob(pattern[3:]):
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
        else:
            # Handle regular paths
            path = project_root / pattern
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                console.print(f"{NORD_DARK}Removed: {path}[/]")
    
    console.print(f"{NORD_GREEN}✓ Cleanup complete![/]")


@click.command()
@click.option("--yes", is_flag=True, help="Skip confirmation prompt")
def reset(yes: bool):
    """Reset experiments by killing daemons and deleting all data."""
    console.print(f"{NORD_RED}Resetting all experiment data...[/]")
    
    if not yes and not Confirm.ask(
        f"{NORD_RED}This will kill running experiments and delete all data. Continue?[/]"
    ):
        console.print(f"{NORD_YELLOW}Reset cancelled.[/]")
        return
    
    project_root = get_project_root()
    pidgin_output = project_root / "pidgin_output"
    
    # Kill running daemons
    active_dir = pidgin_output / "experiments" / "active"
    if active_dir.exists():
        console.print(f"{NORD_YELLOW}Killing running daemons...[/]")
        for pidfile in active_dir.glob("*.pid"):
            try:
                pid = int(pidfile.read_text().strip())
                console.print(f"{NORD_DARK}Killing daemon PID {pid}[/]")
                os.kill(pid, 9)
            except (ValueError, ProcessLookupError):
                pass
    
    # Remove all experiment data
    if pidgin_output.exists():
        console.print(f"{NORD_YELLOW}Removing experiment data...[/]")
        shutil.rmtree(pidgin_output)
    
    console.print(f"{NORD_GREEN}✓ Reset complete![/]")


# === Development Commands ===


@click.command()
@click.argument("args", nargs=-1)
def dev(args):
    """Run the development version of pidgin without installing."""
    # Pass through to the CLI
    cmd = ["poetry", "run", "python", "-m", "pidgin.cli"] + list(args)
    result = run_command(cmd, check=False)
    sys.exit(result.returncode)


@click.command()
def status():
    """Check installation and development status."""
    console.print(f"{NORD_BLUE}◆ Pidgin Development Status[/]")
    console.print(f"{NORD_DARK}{'─' * 40}[/]")
    
    # Check if pidgin is in PATH
    result = subprocess.run(["which", "pidgin"], capture_output=True, text=True)
    if result.returncode == 0:
        console.print(f"Pidgin in PATH: {NORD_GREEN}{result.stdout.strip()}[/]")
    else:
        console.print(f"Pidgin in PATH: {NORD_RED}Not found[/]")
    
    # Check pipx
    result = subprocess.run(["pipx", "list"], capture_output=True, text=True)
    if "pidgin" in result.stdout:
        console.print(f"Pipx install: {NORD_GREEN}✓ Installed[/]")
    else:
        console.print(f"Pipx install: {NORD_DARK}Not installed[/]")
    
    # Show paths
    console.print(f"\nProject root: {get_project_root()}")
    console.print(f"Current dir: {Path.cwd()}")
    
    # Check for output directory
    pidgin_output = get_project_root() / "pidgin_output"
    if pidgin_output.exists():
        exp_count = len(list(pidgin_output.glob("experiments/*")))
        console.print(f"\nExperiments: {NORD_YELLOW}{exp_count} found[/]")
    else:
        console.print(f"\nExperiments: {NORD_DARK}No output directory[/]")


# === Quick Commands ===


@click.command()
def quick_test():
    """Run a quick test with local models."""
    console.print(f"{NORD_YELLOW}Running quick test...[/]")
    cmd = ["poetry", "run", "pidgin", "run", "-a", "local:test", "-b", "local:test", "-t", "5"]
    run_command(cmd, check=False)


@click.command()
def ci():
    """Run the full CI pipeline locally."""
    console.print(f"{NORD_BLUE}Running CI pipeline locally...[/]")
    
    # Clean first
    clean.invoke(click.Context(clean))
    
    # Run all checks
    check.invoke(click.Context(check))
    
    # Run tests with coverage
    ctx = click.Context(test)
    ctx.params = {"cov": True, "unit": False, "integration": False, 
                  "slow": False, "failed": False, "pattern": None}
    test.invoke(ctx)
    
    console.print(f"{NORD_GREEN}✓ CI pipeline complete![/]")


# Main entry point for the script
if __name__ == "__main__":
    # This allows running as `python -m pidgin.scripts <command>`
    import sys
    
    commands = {
        "format": format,
        "lint": lint,
        "typecheck": typecheck,
        "check": check,
        "test": test,
        "build": build,
        "install-pipx": install_pipx,
        "clean": clean,
        "reset": reset,
        "dev": dev,
        "status": status,
        "quick-test": quick_test,
        "ci": ci,
    }
    
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        commands[sys.argv[1]]()
    else:
        console.print(f"{NORD_RED}Unknown command. Available commands:[/]")
        for cmd in commands:
            console.print(f"  {cmd}")