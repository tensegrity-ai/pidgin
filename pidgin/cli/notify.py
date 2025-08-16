# pidgin/cli/notify.py
"""Desktop notification support for experiments."""

import shlex
import subprocess
import sys

from ..core.constants import ExperimentStatus


def send_notification(title: str, message: str):
    """Send desktop notification using system tools.

    Args:
        title: Notification title
        message: Notification message
    """
    system = sys.platform

    try:
        if system == "darwin":  # macOS
            # Use osascript for native macOS notifications
            # Properly escape inputs to prevent command injection
            script = f"display notification {shlex.quote(message)} with title {shlex.quote(title)}"
            subprocess.run(["osascript", "-e", script], check=True)

        elif system == "linux":
            # Try notify-send (most Linux desktops)
            subprocess.run(["notify-send", title, message], check=True)

        elif system == "win32":
            # Windows notifications (requires win10toast)
            try:
                from win10toast import ToastNotifier

                toaster = ToastNotifier()
                toaster.show_toast(title, message, duration=10)
            except ImportError:
                # Fallback to powershell with proper escaping
                # Use base64 encoding to safely pass strings to PowerShell
                import base64

                ps_script = f"""
                [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms") | Out-Null
                [System.Windows.Forms.MessageBox]::Show({shlex.quote(message)}, {shlex.quote(title)})
                """
                encoded = base64.b64encode(ps_script.encode("utf-16le")).decode("ascii")
                subprocess.run(["powershell", "-EncodedCommand", encoded], check=True)

    except (subprocess.CalledProcessError, OSError, FileNotFoundError):
        # If desktop notifications fail, just use terminal bell
        print("\a", end="", flush=True)


def notify_experiment_complete(
    experiment_name: str, status: str = ExperimentStatus.COMPLETED
):
    """Send notification for experiment completion.

    Args:
        experiment_name: Name of the experiment
        status: Final status (completed, failed, interrupted)
    """
    if status == ExperimentStatus.COMPLETED:
        title = "Experiment Complete"
        message = f"Experiment '{experiment_name}' has finished successfully"
    elif status == ExperimentStatus.FAILED:
        title = "Experiment Failed"
        message = f"Experiment '{experiment_name}' failed"
    elif status == ExperimentStatus.INTERRUPTED:
        title = "Experiment Interrupted"
        message = f"Experiment '{experiment_name}' was interrupted"
    else:
        title = "Experiment Status Changed"
        message = f"Experiment '{experiment_name}' status: {status}"

    send_notification(title, message)
    # Also do terminal bell
    print("\a", end="", flush=True)


if __name__ == "__main__":
    # Test notification
    if len(sys.argv) > 1:
        notify_experiment_complete(
            sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "completed"
        )
    else:
        send_notification("Pidgin Test", "This is a test notification")
