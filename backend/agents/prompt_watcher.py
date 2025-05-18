import os
import threading
import time
import logging

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

def watch_file_for_changes(target_path, on_change, logger_name="prompt_watcher"):
    logger = logging.getLogger(logger_name)
    abs_path = os.path.abspath(target_path)
    logger.info(f"Setting up watcher for {abs_path}")
    if WATCHDOG_AVAILABLE:
        class Handler(FileSystemEventHandler):
            def on_modified(self, event):
                if os.path.abspath(event.src_path) == abs_path:
                    logger.info(f"Detected change in {abs_path}, reloading.")
                    on_change()
        observer = Observer()
        handler = Handler()
        observer.schedule(handler, os.path.dirname(abs_path), recursive=False)
        observer.daemon = True
        observer.start()
        logger.info(f"Watchdog observer started for {abs_path}")
    else:
        def poll():
            last_mtime = None
            while True:
                try:
                    mtime = os.path.getmtime(abs_path)
                    if last_mtime is None:
                        last_mtime = mtime
                    elif mtime != last_mtime:
                        logger.info(f"Detected change in {abs_path} (polling), reloading.")
                        on_change()
                        last_mtime = mtime
                except Exception as e:
                    logger.warning(f"Polling error for {abs_path}: {e}")
                time.sleep(2)
        t = threading.Thread(target=poll, daemon=True)
        t.start()
        logger.info(f"Polling thread started for {abs_path}") 