# pidgin/cli/notify.py
"""Desktop notification support for experiments."""

import sys
import subprocess
from pathlib import Path


def send_notification(title: str, message: str):
    """Send desktop notification using system tools.
    
    Args:
        title: Notification title
        message: Notification message
    """
    system = sys.platform
    
    try:
        if system == 'darwin':  # macOS
            # Use osascript for native macOS notifications
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(['osascript', '-e', script], check=True)
            
        elif system == 'linux':
            # Try notify-send (most Linux desktops)
            subprocess.run(['notify-send', title, message], check=True)
            
        elif system == 'win32':
            # Windows notifications (requires win10toast)
            try:
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast(title, message, duration=10)
            except ImportError:
                # Fallback to powershell
                ps_cmd = f'[System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms"); [System.Windows.Forms.MessageBox]::Show("{message}", "{title}")'
                subprocess.run(['powershell', '-Command', ps_cmd], check=True)
                
    except Exception:
        # If desktop notifications fail, just use terminal bell
        print('\a', end='', flush=True)


def notify_experiment_complete(experiment_name: str, status: str = 'completed'):
    """Send notification for experiment completion.
    
    Args:
        experiment_name: Name of the experiment
        status: Final status (completed, failed, interrupted)
    """
    if status == 'completed':
        title = "✓ Experiment Complete"
        message = f"Experiment '{experiment_name}' has finished successfully"
    elif status == 'failed':
        title = "✗ Experiment Failed"
        message = f"Experiment '{experiment_name}' failed"
    else:
        title = "⚠ Experiment Interrupted"
        message = f"Experiment '{experiment_name}' was interrupted"
    
    send_notification(title, message)
    # Also do terminal bell
    print('\a', end='', flush=True)


if __name__ == '__main__':
    # Test notification
    import sys
    if len(sys.argv) > 1:
        notify_experiment_complete(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'completed')
    else:
        send_notification("Pidgin Test", "This is a test notification")