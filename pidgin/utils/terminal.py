import sys
import select
from contextlib import contextmanager

# Only import Unix-specific modules on non-Windows platforms
if sys.platform != 'win32':
    import termios
    import tty


@contextmanager
def raw_terminal_mode():
    """Context manager for raw terminal mode (Unix/Linux/macOS)"""
    if sys.platform == 'win32':
        yield  # Windows doesn't need this
        return
        
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setraw(sys.stdin.fileno())
        yield
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


def check_for_spacebar() -> bool:
    """Non-blocking check for spacebar press"""
    if sys.platform == 'win32':
        import msvcrt
        if msvcrt.kbhit():
            key = msvcrt.getch()
            return key == b' '
    else:
        # Unix/Linux/macOS
        if select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.read(1)
            return key == ' '
    return False