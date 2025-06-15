#!/usr/bin/env python3
"""Test rich-click color output"""

import os
import sys

# Print environment info
print("=== Environment Info ===")
print(f"TERM: {os.environ.get('TERM', 'not set')}")
print(f"COLORTERM: {os.environ.get('COLORTERM', 'not set')}")
print(f"FORCE_COLOR: {os.environ.get('FORCE_COLOR', 'not set')}")
print(f"NO_COLOR: {os.environ.get('NO_COLOR', 'not set')}")
print(f"CLICOLOR: {os.environ.get('CLICOLOR', 'not set')}")
print(f"CLICOLOR_FORCE: {os.environ.get('CLICOLOR_FORCE', 'not set')}")
print(f"sys.stdout.isatty(): {sys.stdout.isatty()}")
print()

# Test basic rich colors
print("=== Testing Rich ===")
from rich.console import Console
console = Console()
console.print("[bold red]This should be bold red[/bold red]")
console.print("[green]This should be green[/green]")
console.print("[blue on yellow]Blue on yellow background[/blue on yellow]")
print()

# Test rich-click
print("=== Testing Rich-Click ===")
os.environ['FORCE_COLOR'] = '1'

import rich_click as click

# Check rich-click version and attributes
print(f"rich_click version: {getattr(click, '__version__', 'unknown')}")
print(f"COLOR_SYSTEM: {getattr(click, 'COLOR_SYSTEM', 'not set')}")
print(f"FORCE_TERMINAL: {getattr(click, 'FORCE_TERMINAL', 'not set')}")
print()

# Create a simple CLI to test
@click.command()
@click.option('--name', '-n', default='World', help='Name to greet')
@click.option('--count', '-c', default=1, help='Number of greetings')
@click.option('--loud', is_flag=True, help='Make it loud!')
def hello(name, count, loud):
    """A simple greeting program with colorful help."""
    for _ in range(count):
        msg = f"Hello {name}!"
        if loud:
            msg = msg.upper()
        click.echo(msg)

# Test the help output
print("=== CLI Help Output ===")
try:
    hello(['--help'])
except SystemExit:
    pass

# Check rich-click's internal state
print("\n=== Rich-Click Internal State ===")
import rich_click
print(f"rich_click.__version__: {rich_click.__version__}")

# Test click's color support
print("\n=== Click Color Support ===")
print(f"click.utils.should_strip_ansi: {click.utils.should_strip_ansi()}")

# Check if terminal detection is the issue
import sys
print(f"sys.stdout.isatty(): {sys.stdout.isatty()}")
print(f"sys.stderr.isatty(): {sys.stderr.isatty()}")

# Force color and retry
print("\n=== Forcing Color Environment ===")
os.environ['FORCE_COLOR'] = '1'
os.environ['CLICOLOR_FORCE'] = '1'
print(f"FORCE_COLOR now: {os.environ.get('FORCE_COLOR')}")
print(f"click.utils.should_strip_ansi() after FORCE_COLOR: {click.utils.should_strip_ansi()}")

# Try to force colors in different ways
print("\n=== Testing Click Echo with Colors ===")
click.echo(click.style('This is red text', fg='red'))
click.echo(click.style('This is green text', fg='green'))
click.echo(click.style('This is bold blue text', fg='blue', bold=True))

# Test raw ANSI output
print("\n=== Raw ANSI Test ===")
print("\033[31mThis is red text\033[0m")
print("\033[32mThis is green text\033[0m")
print("\033[1;34mThis is bold blue text\033[0m")