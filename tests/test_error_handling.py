#!/usr/bin/env python3
"""Test script to demonstrate improved error handling"""

import asyncio
import os
from pidgin.cli.helpers import cli

# Force an API error by using an invalid API key
os.environ['ANTHROPIC_API_KEY'] = 'invalid-key-for-testing'

if __name__ == "__main__":
    # Run a conversation that will trigger an error
    cli(['chat', '-t', '1', '-p', 'Hello!'])