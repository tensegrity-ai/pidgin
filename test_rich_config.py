#!/usr/bin/env python3
"""Test rich-click configuration"""

import os
os.environ['FORCE_COLOR'] = '1'

import rich_click as click
from rich import print as rprint

# Check the config object
print("=== Rich-Click Config ===")
print(f"rich_config: {click.rich_config}")
print(f"Type: {type(click.rich_config)}")

# List all config options
print("\nConfig attributes:")
for attr in dir(click.rich_config):
    if not attr.startswith('_'):
        value = getattr(click.rich_config, attr)
        print(f"  {attr}: {value}")

# Try setting config
print("\n=== Setting Config ===")
click.rich_config.USE_RICH_MARKUP = True
click.rich_config.COLOR_SYSTEM = "truecolor"
click.rich_config.FORCE_TERMINAL = True
click.rich_config.STYLE_OPTION = "bold cyan"
click.rich_config.STYLE_ARGUMENT = "bold bright_cyan"

print("Config updated.")

# Create test command
@click.command()
@click.option('--name', help='Your name')
@click.option('--count', type=int, default=1, help='Number of greetings')
def greet(name, count):
    """A colorful greeting program."""
    for _ in range(count):
        click.echo(f"Hello {name or 'World'}!")

# Test the help
print("\n=== Testing Help Output ===")
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(greet, ['--help'])
print("Has ANSI codes:", '\033[' in result.output)
print("\nOutput preview:")
lines = result.output.split('\n')[:15]
for line in lines:
    print(repr(line))