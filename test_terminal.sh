#!/bin/bash
# Test script to verify colors work in real terminal

echo "=== Testing Pidgin Colors in Terminal ==="
echo ""
echo "1. Testing with FORCE_COLOR=1:"
FORCE_COLOR=1 poetry run pidgin --help | head -30

echo ""
echo "2. Testing color rendering:"
echo -e "\033[31mThis should be red\033[0m"
echo -e "\033[32mThis should be green\033[0m"
echo -e "\033[1;34mThis should be bold blue\033[0m"

echo ""
echo "3. To test in your terminal, run:"
echo "   cd $(pwd)"
echo "   poetry run pidgin --help"
echo ""
echo "If you don't see colors, try:"
echo "   FORCE_COLOR=1 poetry run pidgin --help"