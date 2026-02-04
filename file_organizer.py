#!/usr/bin/env python3
"""
File Organizer - Automated file organization script
Organizes files based on their extensions into categorized folders
"""

import os
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import sys


class FileOrganizer:
    def __init__(self, config_path: str = "config.json"):
        """Initialize the File Organizer with configuration"""
        self.config_path = config_path
        self.config = self._load_config()
        self._setup_logging()
        self.stats = {"moved": 0, "skipped": 0, "errors": 0}

    def _load_config(self) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Config file '{self.config_path}' not found!")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in config file: {e}")
            sys.exit(1)

    def _setup_logging(self):
        """Setup logging configuration"""
        self.logger = logging.getLogger(__name__)

        if not self.config.get("enable_logging", True):
            self.logger.addHandler(logging.NullHandler())
            logging.disable(logging.CRITICAL)
            return

        log_level = getattr(logging, self.config.get("log_level", "INFO"))
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / f"organizer_{datetime.now().strftime('%Y%m%d')}.log"

        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
        )
        self.logger = logging.getLogger(__name__)

    def _get_file_category(self, file_path: Path) -> Optional[str]:
        """Determine the category of a file based on its extension"""
        extension = file_path.suffix.lower()

        # Check if extension should be ignored
        if extension in self.config.get("ignore_extensions", []):
            return None

        # Check if filename should be ignored
        if file_path.name in self.config.get("ignore_files", []):
            return None

        # Find matching category
        for category, rules in self.config.get("organize_rules", {}).items():
            if extension in rules.get("extensions", []):
                return category

        # Return 'Extras' for files without a matching category
        return "Extras"

    def _get_target_path(self, file_path: Path, category: str) -> Path:
        """Get the target path for a file"""
        # Handle Extras category with a default location
        if category == "Extras":
            # Get base path from any organize rule or use default
            base_paths = [
                Path(rules["target_folder"]).parent
                for rules in self.config.get("organize_rules", {}).values()
            ]
            if base_paths:
                target_folder = base_paths[0] / "Extras"
            else:
                target_folder = Path("C:\\Users\\lnloh\\Documents\\Organized\\Extras")
        else:
            target_folder = Path(
                self.config["organize_rules"][category]["target_folder"]
            )

        # Create subfolder by date if enabled
        if self.config.get("organize_by_date", False):
            date_format = self.config.get("date_format", "%Y-%m")
            file_date = datetime.fromtimestamp(file_path.stat().st_mtime)
            target_folder = target_folder / file_date.strftime(date_format)

        target_folder.mkdir(parents=True, exist_ok=True)
        return target_folder / file_path.name

    def _handle_duplicate(self, target_path: Path) -> Optional[Path]:
        """Handle duplicate file names"""
        if not target_path.exists():
            return target_path

        duplicate_handling = self.config.get("duplicate_handling", "rename")

        if duplicate_handling == "skip":
            return None
        elif duplicate_handling == "overwrite":
            return target_path
        else:  # rename
            counter = 1
            stem = target_path.stem
            suffix = target_path.suffix
            parent = target_path.parent

            while target_path.exists():
                new_name = f"{stem}_{counter}{suffix}"
                target_path = parent / new_name
                counter += 1

            return target_path

    def organize_file(self, file_path: Path) -> bool:
        """Organize a single file"""
        try:
            # Skip if it's a directory
            if file_path.is_dir():
                return False

            # Get category
            category = self._get_file_category(file_path)
            if not category:
                # Files with ignored extensions/names
                self.logger.debug(f"Skipping ignored file: {file_path.name}")
                self.stats["skipped"] += 1
                return False

            # Get target path
            target_path = self._get_target_path(file_path, category)

            # Handle duplicates
            target_path = self._handle_duplicate(target_path)
            if not target_path:
                self.logger.info(f"Skipping duplicate: {file_path.name}")
                self.stats["skipped"] += 1
                return False

            # Move file (or simulate in dry-run mode)
            if self.config.get("dry_run", False):
                self.logger.info(f"[DRY RUN] Would move: {file_path} -> {target_path}")
            else:
                shutil.move(str(file_path), str(target_path))
                self.logger.info(
                    f"Moved: {file_path.name} -> {category}/{target_path.name}"
                )

            self.stats["moved"] += 1
            return True

        except PermissionError:
            self.logger.error(f"Permission denied: {file_path}")
            self.stats["errors"] += 1
        except Exception as e:
            self.logger.error(f"Error organizing {file_path}: {str(e)}")
            self.stats["errors"] += 1

        return False

    def organize_directory(self, directory: str):
        """Organize all files in a directory"""
        dir_path = Path(directory)

        if not dir_path.exists():
            self.logger.error(f"Directory does not exist: {directory}")
            return

        if not dir_path.is_dir():
            self.logger.error(f"Not a directory: {directory}")
            return

        self.logger.info(f"Organizing directory: {directory}")

        # Get files based on recursive setting
        recursive = self.config.get("recursive", False)
        if recursive:
            # Get all files recursively
            files = [f for f in dir_path.rglob("*") if f.is_file()]
        else:
            # Get all files (not recursive)
            files = [f for f in dir_path.iterdir() if f.is_file()]

        self.logger.info(f"Found {len(files)} files to process")

        for file_path in files:
            self.organize_file(file_path)

    def run(self):
        """Run the file organizer on all configured directories"""
        self.logger.info("=" * 60)
        self.logger.info("File Organizer Started")
        self.logger.info("=" * 60)

        watch_dirs = self.config.get("watch_directories", [])

        if not watch_dirs:
            self.logger.warning("No watch directories configured!")
            return

        for directory in watch_dirs:
            self.organize_directory(directory)

        # Print summary
        self.logger.info("=" * 60)
        self.logger.info("Organization Complete!")
        self.logger.info(f"Files moved: {self.stats['moved']}")
        self.logger.info(f"Files skipped: {self.stats['skipped']}")
        self.logger.info(f"Errors: {self.stats['errors']}")
        self.logger.info("=" * 60)

    def print_config_info(self):
        """Print configuration information"""
        print("\n" + "=" * 60)
        print("FILE ORGANIZER CONFIGURATION")
        print("=" * 60)
        print(f"\nWatching directories:")
        for directory in self.config.get("watch_directories", []):
            print(f"  - {directory}")

        print(f"\nOrganization rules:")
        for category, rules in self.config.get("organize_rules", {}).items():
            print(f"  {category}:")
            print(f"    Target: {rules['target_folder']}")
            print(f"    Extensions: {', '.join(rules['extensions'])}")

        print(f"\nSettings:")
        print(f"  Organize by date: {self.config.get('organize_by_date', False)}")
        print(
            f"  Duplicate handling: {self.config.get('duplicate_handling', 'rename')}"
        )
        print(f"  Dry run: {self.config.get('dry_run', False)}")
        print("=" * 60 + "\n")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Automated File Organizer")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument(
        "--dry-run", action="store_true", help="Run without moving files"
    )
    parser.add_argument(
        "--show-config", action="store_true", help="Show current configuration"
    )

    args = parser.parse_args()

    # Load organizer
    organizer = FileOrganizer(args.config)

    # Override dry-run if specified
    if args.dry_run:
        organizer.config["dry_run"] = True

    # Show config and exit if requested
    if args.show_config:
        organizer.print_config_info()
        return

    # Run organizer
    organizer.run()


if __name__ == "__main__":
    main()
