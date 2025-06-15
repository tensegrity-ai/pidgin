#!/usr/bin/env python3
"""Diagnose color support in terminal"""

import os
import sys
import subprocess

print("=== Terminal Color Diagnostic ===\n")

# Check environment
print("1. Environment Variables:")
env_vars = ['TERM', 'COLORTERM', 'FORCE_COLOR', 'NO_COLOR', 'CLICOLOR', 'CLICOLOR_FORCE']
for var in env_vars:
    value = os.environ.get(var, 'not set')
    print(f"   {var}: {value}")

# Check terminal capabilities
print("\n2. Terminal Capabilities:")
print(f"   sys.stdout.isatty(): {sys.stdout.isatty()}")
print(f"   sys.stderr.isatty(): {sys.stderr.isatty()}")

# Test basic ANSI
print("\n3. Basic ANSI Color Test:")
print("   \033[31mRed\033[0m \033[32mGreen\033[0m \033[34mBlue\033[0m \033[1;33mBold Yellow\033[0m")

# Test 256 colors
print("\n4. 256 Color Test:")
for i in range(16):
    print(f"   \033[38;5;{i}m▓\033[0m", end='')
print()

# Test 24-bit true color
print("\n5. True Color Test (24-bit RGB):")
print("   \033[38;2;255;0;0mRed\033[0m \033[38;2;0;255;0mGreen\033[0m \033[38;2;0;0;255mBlue\033[0m")
print("   \033[38;2;143;188;187mNord7\033[0m \033[38;2;136;192;208mNord8\033[0m \033[38;2;94;129;172mNord10\033[0m")

# Test with tput
print("\n6. tput Commands:")
try:
    colors = subprocess.check_output(['tput', 'colors'], text=True).strip()
    print(f"   tput colors: {colors}")
except:
    print("   tput not available")

# Test rich directly
print("\n7. Rich Library Test:")
from rich.console import Console
console = Console(force_terminal=True, color_system="truecolor")
console.print("   [red]Red[/red] [green]Green[/green] [blue]Blue[/blue] [bold yellow]Bold Yellow[/bold yellow]")
console.print("   [#8fbcbb]Nord7[/#8fbcbb] [#88c0d0]Nord8[/#88c0d0] [#5e81ac]Nord10[/#5e81ac]")

# Test rich-click
print("\n8. Rich-Click Test:")
os.environ['FORCE_COLOR'] = '1'
import rich_click as click

@click.command()
@click.option('--test', help='Test option')
def test():
    """Test command"""
    pass

from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(test, ['--help'])
print("   Output has ANSI codes:", '\033[' in result.output)
print("   First line of help:")
print("   " + repr(result.output.split('\n')[1]))

# Recommendations
print("\n9. Recommendations:")
print("   - If you see colors above, rich-click IS working")
print("   - If not, try: export CLICOLOR_FORCE=1")
print("   - Or run with: FORCE_COLOR=1 pidgin --help")
print("   - Check your terminal emulator settings")
print("   - Some terminals need: export TERM=xterm-256color")