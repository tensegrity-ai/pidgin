#!/bin/bash
# pidgin_dev.sh - Development helper script

# Nord color palette for shell
NORD_RED='\033[38;2;191;97;106m'     # nord11 - errors/warnings
NORD_GREEN='\033[38;2;163;190;140m'  # nord14 - success
NORD_YELLOW='\033[38;2;235;203;139m' # nord13 - info/warnings  
NORD_BLUE='\033[38;2;136;192;208m'   # nord8 - headers
NORD_ORANGE='\033[38;2;208;135;112m' # nord12 - highlights
NORD_CYAN='\033[38;2;143;188;187m'   # nord7 - secondary info
NORD_DARK='\033[38;2;76;86;106m'     # nord3 - dim text
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR"

echo -e "${NORD_BLUE}◆ Pidgin Development Helper${NC}"
echo -e "${NORD_DARK}━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

case "${1:-help}" in
    "rebuild")
        echo -e "${NORD_YELLOW}Rebuilding and installing with pipx...${NC}"
        cd "$PROJECT_ROOT"
        
        # Clean old builds
        rm -rf dist/ build/
        
        # Build with poetry
        poetry build
        
        # Install with pipx
        pipx install dist/*.whl --force
        
        echo -e "${NORD_GREEN}[OK] Rebuild complete!${NC}"
        ;;
        
    "quick")
        echo -e "${NORD_YELLOW}Quick rebuild (no clean)...${NC}"
        cd "$PROJECT_ROOT"
        poetry build && pipx install dist/*.whl --force
        echo -e "${NORD_GREEN}[OK] Quick rebuild complete!${NC}"
        ;;
        
    "clean")
        echo -e "${NORD_YELLOW}Cleaning build artifacts...${NC}"
        cd "$PROJECT_ROOT"
        
        rm -rf dist/ build/ *.egg-info
        find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
        find . -type f -name "*.pyc" -delete
        
        echo -e "${NORD_GREEN}[OK] Clean complete!${NC}"
        ;;
        
    "clean-all")
        echo -e "${NORD_YELLOW}Cleaning all generated files and directories...${NC}"
        cd "$PROJECT_ROOT"
        
        # Build artifacts
        rm -rf dist/ build/ *.egg-info
        
        # Test/coverage artifacts  
        rm -rf htmlcov/ .coverage .pytest_cache/
        
        # Generated output directories
        rm -rf pidgin_output/ notebooks/
        
        # Config files
        rm -f ~/.config/pidgin/pidgin.yaml
        rm -f ~/.pidgin.yaml
        rm -f pidgin.yaml
        rm -f .pidgin.yaml
        
        # Remove config directory if empty
        rmdir ~/.config/pidgin 2>/dev/null || true
        
        # Python cache files
        find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
        find . -type f -name "*.pyc" -delete
        find . -type f -name "*.pyo" -delete
        
        echo -e "${NORD_GREEN}[OK] Full clean complete!${NC}"
        ;;
        
    "reset")
        echo -e "${NORD_RED}Resetting all experiment data...${NC}"
        echo -e "${NORD_YELLOW}This will kill running experiments and delete all data!${NC}"
        echo -n "Are you sure? (y/N) "
        read -r response
        
        if [[ "$response" =~ ^[Yy]$ ]]; then
            # Kill any running daemons
            if [ -d "pidgin_output/experiments/active" ]; then
                echo -e "${NORD_YELLOW}Killing running daemons...${NC}"
                for pidfile in pidgin_output/experiments/active/*.pid; do
                    if [ -f "$pidfile" ]; then
                        pid=$(cat "$pidfile")
                        echo "  Killing daemon PID $pid"
                        kill -9 "$pid" 2>/dev/null || true
                    fi
                done
            fi
            
            # Remove all experiment data
            echo -e "${NORD_YELLOW}Removing experiment data...${NC}"
            rm -rf pidgin_output/
            
            echo -e "${NORD_GREEN}[OK] Reset complete! You can now run new experiments.${NC}"
        else
            echo -e "${NORD_YELLOW}Reset cancelled.${NC}"
        fi
        ;;
        
    "test")
        echo -e "${NORD_YELLOW}Running quick test...${NC}"
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
        echo -e "${NORD_YELLOW}Running pidgin with poetry from current directory...${NC}"
        # This preserves the current working directory
        poetry -C "$PROJECT_ROOT" run python -m pidgin.cli "$@"
        ;;
        
    "alias")
        echo -e "${NORD_YELLOW}Setting up shell alias...${NC}"
        
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
        echo -e "${NORD_YELLOW}Checking installation status...${NC}"
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
        echo "Usage: $0 {rebuild|quick|clean|clean-all|reset|test|dev|alias|status}"
        echo
        echo "Commands:"
        echo "  rebuild   - Clean, build, and install with pipx"
        echo "  quick     - Build and install without cleaning"
        echo "  clean     - Remove build artifacts only"
        echo "  clean-all - Remove ALL generated files (build, test, output)"
        echo "  reset     - Kill experiments and delete all data (destructive!)"
        echo "  test      - Run a quick test in temp directory"
        echo "  dev       - Run development version preserving working directory"
        echo "  alias     - Set up pidgin-dev alias for development"
        echo "  status    - Check installation status"
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
