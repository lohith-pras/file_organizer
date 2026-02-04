#!/usr/bin/env python3
"""
File Watcher - Real-time file system monitoring
Monitors directories and automatically organizes new files
"""

import os
import sys
import time
import logging
from pathlib import Path
from watchdog.observers import Observer  # type: ignore
from watchdog.events import FileSystemEventHandler  # type: ignore
from file_organizer import FileOrganizer


class FileOrganizerHandler(FileSystemEventHandler):
    """Handler for file system events"""

    def __init__(self, organizer: FileOrganizer):
        super().__init__()
        self.organizer = organizer
        self.logger = logging.getLogger(__name__)
        # Track recently modified files to avoid duplicate processing
        self.processing_files = set()

    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        self._process_file(file_path, "created")

    def on_moved(self, event):
        """Handle file move events (e.g., downloads completing)"""
        if event.is_directory:
            return

        # When a file is moved into the watched directory
        file_path = Path(event.dest_path)
        self._process_file(file_path, "moved")

    def _process_file(self, file_path: Path, event_type: str):
        """Process a file with debouncing"""
        # Skip if already processing
        if str(file_path) in self.processing_files:
            return

        try:
            # Mark as processing
            self.processing_files.add(str(file_path))

            # Wait a bit to ensure file is fully written
            # Especially important for large downloads
            time.sleep(1)

            # Check if file still exists and is accessible
            if not file_path.exists():
                return

            # Check if file is still being written (size changes)
            initial_size = file_path.stat().st_size
            time.sleep(0.5)

            if not file_path.exists():
                return

            current_size = file_path.stat().st_size
            if initial_size != current_size:
                self.logger.debug(f"File still being written: {file_path.name}")
                return

            # Organize the file
            self.logger.info(f"New file {event_type}: {file_path.name}")
            self.organizer.organize_file(file_path)

        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {str(e)}")
        finally:
            # Remove from processing set after a delay
            # Use a thread timer to avoid blocking
            import threading

            def remove_from_processing():
                time.sleep(5)
                self.processing_files.discard(str(file_path))

            threading.Thread(target=remove_from_processing, daemon=True).start()


class FileWatcher:
    """Main file watcher class"""

    def __init__(self, config_path: str = "config.json"):
        self.organizer = FileOrganizer(config_path)
        self.logger = logging.getLogger(__name__)
        self.observers = []

    def start(self):
        """Start watching configured directories"""
        watch_dirs = self.organizer.config.get("watch_directories", [])

        if not watch_dirs:
            self.logger.error("No directories configured to watch!")
            sys.exit(1)

        # Create event handler
        event_handler = FileOrganizerHandler(self.organizer)

        # Setup observers for each directory
        for directory in watch_dirs:
            dir_path = Path(directory)

            if not dir_path.exists():
                self.logger.warning(f"Directory does not exist: {directory}")
                continue

            observer = Observer()
            observer.schedule(event_handler, str(dir_path), recursive=False)
            observer.start()
            self.observers.append(observer)

            self.logger.info(f"Watching directory: {directory}")

        if not self.observers:
            self.logger.error("No valid directories to watch!")
            sys.exit(1)

        self.logger.info("=" * 60)
        self.logger.info("File Watcher is running...")
        self.logger.info("Press Ctrl+C to stop")
        self.logger.info("=" * 60)

    def stop(self):
        """Stop all observers"""
        for observer in self.observers:
            observer.stop()
            observer.join()
        self.logger.info("File Watcher stopped")

    def run(self):
        """Run the watcher"""
        try:
            self.start()

            # Keep the program running
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            self.logger.info("\nReceived interrupt signal...")
            self.stop()
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            self.stop()
            sys.exit(1)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="File Organizer Watcher")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument(
        "--organize-first",
        action="store_true",
        help="Organize existing files before starting watcher",
    )

    args = parser.parse_args()

    # First, organize existing files if requested
    if args.organize_first:
        print("\nOrganizing existing files first...")
        organizer = FileOrganizer(args.config)
        organizer.run()
        print("\nStarting file watcher...\n")

    # Start the watcher
    watcher = FileWatcher(args.config)
    watcher.run()


if __name__ == "__main__":
    main()
