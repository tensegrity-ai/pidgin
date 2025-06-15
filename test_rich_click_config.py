#!/usr/bin/env python3
"""Test rich-click configuration methods"""

import os
os.environ['FORCE_COLOR'] = '1'
os.environ['CLICOLOR_FORCE'] = '1'

# Method 1: Direct import and config
print("=== Method 1: Direct Configuration ===")
import rich_click as click
print(f"rich_click module: {click.rich_click}")
print(f"Has COLOR_SYSTEM: {hasattr(click.rich_click, 'COLOR_SYSTEM')}")

# Set config
click.rich_click.USE_RICH_MARKUP = True
click.rich_click.COLOR_SYSTEM = "truecolor"
click.rich_click.FORCE_TERMINAL = True

# Method 2: Check the console used by rich-click
print("\n=== Method 2: Console Configuration ===")
from rich_click import get_rich_console
console = get_rich_console()
print(f"Console: {console}")
print(f"Console force_terminal: {console.force_terminal}")
print(f"Console color_system: {console.color_system}")

# Method 3: Try patching click
print("\n=== Method 3: Click Utilities ===")
if hasattr(click, 'formatting'):
    print(f"click.formatting available")
if hasattr(click, 'utils'):
    print(f"click.utils available")
    print(f"Dir of utils: {[x for x in dir(click.utils) if 'color' in x.lower() or 'ansi' in x.lower()]}")

# Create a test command
@click.command()
@click.option('--name', '-n', help='Name to use', default='World')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def hello(name, verbose):
    """Simple test command with rich-click formatting."""
    click.echo(f"Hello {name}!")

# Try to display help
print("\n=== Help Output ===")
from click.testing import CliRunner
runner = CliRunner(mix_stderr=False)
result = runner.invoke(hello, ['--help'])
print("Exit code:", result.exit_code)
print("Output has ANSI codes:", '\033[' in result.output)
print("\nFirst 500 chars of output:")
print(repr(result.output[:500]))