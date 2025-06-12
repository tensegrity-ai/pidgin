import sys
import threading
import queue
import time


class RichCompatibleKeyListener:
    """Rich-compatible keyboard listener using background thread."""
    
    def __init__(self):
        self.key_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.listener_thread = None
        self._running = False
    
    def start_listening(self):
        """Start background thread for keyboard listening."""
        if self._running:
            return
            
        self.stop_event.clear()
        self.listener_thread = threading.Thread(target=self._listen_for_keys, daemon=True)
        self.listener_thread.start()
        self._running = True
    
    def stop_listening(self):
        """Stop background thread."""
        if not self._running:
            return
            
        self.stop_event.set()
        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.join(timeout=0.5)
        self._running = False
    
    def _listen_for_keys(self):
        """Background thread function for keyboard detection."""
        while not self.stop_event.is_set():
            try:
                if sys.platform == 'win32':
                    import msvcrt
                    if msvcrt.kbhit():
                        key = msvcrt.getch()
                        if key == b' ':
                            self.key_queue.put('space')
                else:
                    # Unix/Linux/macOS - use select for non-blocking
                    import select
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        key = sys.stdin.read(1)
                        if key == ' ':
                            self.key_queue.put('space')
                            
            except (OSError, IOError, ImportError):
                # If stdin unavailable or import fails, wait and continue
                time.sleep(0.1)
                continue
    
    def check_for_spacebar(self) -> bool:
        """Non-blocking check for spacebar press."""
        try:
            self.key_queue.get_nowait()
            return True
        except queue.Empty:
            return False


# Global listener instance - Rich-compatible
_global_listener = RichCompatibleKeyListener()


def check_for_spacebar() -> bool:
    """Rich-compatible spacebar detection using background thread."""
    global _global_listener
    
    # Start listener if not running
    if not _global_listener._running:
        _global_listener.start_listening()
    
    return _global_listener.check_for_spacebar()


def cleanup_keyboard_listener():
    """Clean up background keyboard listener."""
    global _global_listener
    _global_listener.stop_listening()