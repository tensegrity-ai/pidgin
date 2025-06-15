#!/usr/bin/env python3
"""Direct test of colors in terminal"""

import os
import sys

# Force colors
os.environ['FORCE_COLOR'] = '1'

print("Testing colors directly in terminal:")
print()

# Test ANSI codes
print("ANSI escape codes:")
print("\033[31mRed text\033[0m")
print("\033[32mGreen text\033[0m")
print("\033[1;34mBold blue text\033[0m")
print()

# Test rich
print("Rich library:")
from rich.console import Console
console = Console(force_terminal=True)
console.print("[bold red]Bold red from Rich[/bold red]")
console.print("[green]Green from Rich[/green]")
console.print("[bold blue]Bold blue from Rich[/bold blue]")
print()

# Test rich-click
print("Rich-click:")
import rich_click as click

@click.command()
@click.option('--test', help='Test option')
def test_cmd(test):
    """Test command"""
    click.echo(click.style("Colored output from click", fg='red'))

# Show help
ctx = click.Context(test_cmd)
click.echo(ctx.get_help())