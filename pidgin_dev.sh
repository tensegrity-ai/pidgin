#!/bin/bash
# pidgin_dev.sh - Development helper script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR"

echo -e "${GREEN}Pidgin Development Helper${NC}"
echo "=========================="

case "${1:-help}" in
    "rebuild")
        echo -e "${YELLOW}Rebuilding and installing with pipx...${NC}"
        cd "$PROJECT_ROOT"
        
        # Clean old builds
        rm -rf dist/ build/
        
        # Build with poetry
        poetry build
        
        # Install with pipx
        pipx install dist/*.whl --force
        
        echo -e "${GREEN}✓ Rebuild complete!${NC}"
        ;;
        
    "quick")
        echo -e "${YELLOW}Quick rebuild (no clean)...${NC}"
        cd "$PROJECT_ROOT"
        poetry build && pipx install dist/*.whl --force
        echo -e "${GREEN}✓ Quick rebuild complete!${NC}"
        ;;
        
    "clean")
        echo -e "${YELLOW}Cleaning build artifacts...${NC}"
        cd "$PROJECT_ROOT"
        
        rm -rf dist/ build/ *.egg-info
        find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
        find . -type f -name "*.pyc" -delete
        
        echo -e "${GREEN}✓ Clean complete!${NC}"
        ;;
        
    "test")
        echo -e "${YELLOW}Running quick test...${NC}"
        # Save current directory
        CURRENT_DIR=$(pwd)
        # Create temp directory for test
        TEST_DIR=$(mktemp -d)
        cd "$TEST_DIR"
        echo "Testing in: $TEST_DIR"
        pidgin models
        cd "$CURRENT_DIR"
        rm -rf "$TEST_DIR"
        ;;
        
    "dev")
        echo -e "${YELLOW}Running pidgin with poetry from current directory...${NC}"
        # This preserves the current working directory
        poetry -C "$PROJECT_ROOT" run python -m pidgin.cli "$@"
        ;;
        
    "alias")
        echo -e "${YELLOW}Setting up shell alias...${NC}"
        
        ALIAS_CMD="alias pidgin-dev='poetry -C $PROJECT_ROOT run python -m pidgin.cli'"
        
        # Detect shell
        if [[ "$SHELL" == *"zsh"* ]]; then
            SHELL_RC="$HOME/.zshrc"
        else
            SHELL_RC="$HOME/.bashrc"
        fi
        
        # Check if alias already exists
        if grep -q "alias pidgin-dev=" "$SHELL_RC" 2>/dev/null; then
            echo "Alias already exists in $SHELL_RC"
        else
            echo "$ALIAS_CMD" >> "$SHELL_RC"
            echo "Added alias to $SHELL_RC"
        fi
        
        echo
        echo "Run this to activate:"
        echo "  source $SHELL_RC"
        echo
        echo "Then you can use: pidgin-dev [commands]"
        echo "This will run the development version while preserving your working directory."
        ;;
        
    "status")
        echo -e "${YELLOW}Checking installation status...${NC}"
        echo
        
        echo "Which pidgin:"
        which pidgin 2>/dev/null || echo "  Not found in PATH"
        echo
        
        echo "Pipx list:"
        pipx list | grep pidgin || echo "  Not installed via pipx"
        echo
        
        echo "Current directory: $(pwd)"
        echo "Project root: $PROJECT_ROOT"
        ;;
        
    *)
        echo "Usage: $0 {rebuild|quick|clean|test|dev|alias|status}"
        echo
        echo "Commands:"
        echo "  rebuild - Clean, build, and install with pipx"
        echo "  quick   - Build and install without cleaning"
        echo "  clean   - Remove build artifacts"
        echo "  test    - Run a quick test in temp directory"
        echo "  dev     - Run development version preserving working directory"
        echo "  alias   - Set up pidgin-dev alias for development"
        echo "  status  - Check installation status"
        echo
        echo "Examples:"
        echo "  $0 rebuild           # Full rebuild and install"
        echo "  $0 dev models        # Run 'pidgin models' using dev version"
        echo "  $0 dev chat -a claude -b gpt-4  # Run chat with dev version"
        echo
        echo "For development workflow:"
        echo "  1. Make code changes"
        echo "  2. Run: $0 quick"
        echo "  3. Test normally: pidgin [command]"
        ;;
esac
