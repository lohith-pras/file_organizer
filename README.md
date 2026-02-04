# File Organizer - Automated File Organization System

A powerful Python-based automation tool that helps you organize files on your laptop automatically. It runs every 24 hours, at startup, or monitors folders in real-time to keep your files organized.

## Features

✨ **Automatic Organization** - Categorizes files by type (Images, Documents, Videos, etc.)  
⏰ **Scheduled Execution** - Runs daily at your preferred time  
🚀 **Startup Integration** - Automatically runs when you log in  
👁️ **Real-time Monitoring** - Instantly organizes new files as they appear  
🔧 **Highly Configurable** - Customize rules, folders, and behavior  
📊 **Detailed Logging** - Track all operations with comprehensive logs  
🛡️ **Safe Operations** - Duplicate handling, dry-run mode, and error recovery

## Installation

### 1. Setup Virtual Environment

```bash
# The virtual environment is already created
# Activate it:
.\venv\Scripts\Activate.ps1

# If you need to reinstall dependencies:
pip install -r requirements.txt
```

### 2. Configure Your Preferences

Edit `config.json` to customize:

- **Watch directories**: Folders to monitor (e.g., Downloads, Desktop)
- **Organization rules**: File types and where they should go
- **Target folders**: Destination paths for organized files
- **Settings**: Duplicate handling, date organization, etc.

**Example Configuration:**

```json
{
  "watch_directories": [
    "C:\\Users\\YourName\\Downloads",
    "C:\\Users\\YourName\\Desktop"
  ],
  "organize_rules": {
    "Images": {
      "extensions": [".jpg", ".png", ".gif"],
      "target_folder": "C:\\Users\\YourName\\Documents\\Organized\\Images"
    }
  }
}
```

## Usage

### Option 1: One-Time Organization

Organize existing files in watched directories:

```bash
python file_organizer.py
```

**Options:**

- `--dry-run` - Preview changes without moving files
- `--show-config` - Display current configuration
- `--config path/to/config.json` - Use custom config file

**Example:**

```bash
# Preview what would be organized
python file_organizer.py --dry-run

# Show current configuration
python file_organizer.py --show-config
```

### Option 2: Real-Time File Watcher

Continuously monitor directories and organize files automatically:

```bash
python watcher.py
```

**Options:**

- `--organize-first` - Organize existing files before starting watcher
- `--config path/to/config.json` - Use custom config file

**Example:**

```bash
# Clean up existing files, then watch for new ones
python watcher.py --organize-first
```

Press `Ctrl+C` to stop the watcher.

### Option 3: Scheduled Automation

Setup Windows Task Scheduler to run automatically:

```bash
python scheduler_setup.py
```

**Interactive Menu Options:**

1. Setup daily organization task (runs at specific time)
2. Setup startup watcher (runs when you log in)
3. Setup both
4. List existing tasks
5. Delete a task

**Command Line Options:**

```bash
# Setup daily task at 9:00 AM
python scheduler_setup.py --setup-daily --time 09:00

# Setup startup watcher
python scheduler_setup.py --setup-startup

# Setup everything
python scheduler_setup.py --setup-all

# List all tasks
python scheduler_setup.py --list

# Delete a specific task
python scheduler_setup.py --delete FileOrganizerDaily
```

## Configuration Guide

### Watch Directories

Specify which folders to monitor:

```json
"watch_directories": [
  "C:\\Users\\YourName\\Downloads",
  "C:\\Users\\YourName\\Desktop"
]
```

### Organization Rules

Define file categories and where they should go:

```json
"organize_rules": {
  "CategoryName": {
    "extensions": [".ext1", ".ext2"],
    "target_folder": "C:\\Path\\To\\Destination"
  }
}
```

**Built-in Categories:**

- **Images**: `.jpg`, `.png`, `.gif`, `.bmp`, `.svg`, `.webp`
- **Documents**: `.pdf`, `.doc`, `.docx`, `.txt`, `.xlsx`, `.ppt`
- **Videos**: `.mp4`, `.avi`, `.mkv`, `.mov`, `.wmv`
- **Audio**: `.mp3`, `.wav`, `.flac`, `.aac`, `.ogg`
- **Archives**: `.zip`, `.rar`, `.7z`, `.tar`, `.gz`
- **Code**: `.py`, `.js`, `.java`, `.cpp`, `.html`, `.css`
- **Executables**: `.exe`, `.msi`, `.dmg`

### Additional Settings

```json
{
  "organize_by_date": false, // Group files by month/year
  "date_format": "%Y-%m", // Date folder format
  "ignore_extensions": [".tmp"], // Extensions to skip
  "ignore_files": [".DS_Store"], // Specific files to skip
  "duplicate_handling": "rename", // Options: rename, skip, overwrite
  "dry_run": false, // Preview mode
  "enable_logging": true, // Enable/disable logs
  "log_level": "INFO" // Log detail level
}
```

### Duplicate Handling

- **rename**: Add counter to filename (file_1.txt, file_2.txt)
- **skip**: Don't move if file exists
- **overwrite**: Replace existing file

## File Structure

```
file-organizer/
├── file_organizer.py       # Main organization script
├── watcher.py              # Real-time file monitoring
├── scheduler_setup.py      # Windows Task Scheduler setup
├── config.json             # Configuration file
├── requirements.txt        # Python dependencies
├── logs/                   # Log files directory
│   └── organizer_YYYYMMDD.log
├── venv/                   # Virtual environment
└── README.md              # This file
```

## Logs

All operations are logged to `logs/organizer_YYYYMMDD.log`

**Log entries include:**

- Files moved and their destinations
- Skipped files and reasons
- Errors encountered
- Summary statistics

## Troubleshooting

### Permission Errors

If you see permission errors:

1. Run PowerShell/Command Prompt as Administrator
2. Ensure you have write access to target folders
3. Check if files are in use by another program

### Task Scheduler Not Working

1. Verify tasks exist: `python scheduler_setup.py --list`
2. Check Task Scheduler manually (Windows → Task Scheduler)
3. Ensure Python path in task is correct
4. Run as administrator when setting up tasks

### Files Not Being Organized

1. Check if file extension is in your rules
2. Verify watch directories exist and are correct
3. Check logs for errors
4. Run with `--dry-run` to see what would happen

### Watcher Not Detecting Files

1. Ensure you're watching the correct directory
2. Check if files are being created (not moved)
3. Large downloads may need time to complete
4. Check logs for processing messages

## Examples

### Example 1: Clean Downloads Folder

```bash
# First, organize everything in Downloads
python file_organizer.py

# Then start monitoring for new downloads
python watcher.py
```

### Example 2: Setup Complete Automation

```bash
# Setup everything to run automatically
python scheduler_setup.py --setup-all --time 09:00
```

This will:

- Organize files daily at 9:00 AM
- Start file watcher when you log in
- Organize existing files, then monitor for new ones

### Example 3: Test Before Applying

```bash
# See what would be organized without moving anything
python file_organizer.py --dry-run
```

## Requirements

- Python 3.7 or higher
- Windows OS (for Task Scheduler integration)
- Required packages (installed via requirements.txt):
  - watchdog - File system monitoring
  - pywin32 - Windows integration
  - colorama - Terminal colors
  - python-dateutil - Date handling

## Tips

💡 **Start with dry-run mode** to see what will happen  
💡 **Use the watcher** for real-time organization  
💡 **Setup startup task** for automatic organization  
💡 **Check logs** if something unexpected happens  
💡 **Customize config.json** to match your workflow  
💡 **Backup important files** before first run

## License

This project is open source and available for personal use.

## Support

For issues or questions:

1. Check the logs directory for error messages
2. Verify your config.json syntax
3. Ensure all paths exist and are accessible
4. Run in dry-run mode to diagnose issues

---

**Happy organizing! 🎉**
