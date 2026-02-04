#!/usr/bin/env python3
"""
Scheduler Setup - Windows Task Scheduler Integration
Sets up automated tasks to run file organizer on schedule and at startup
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional
import win32com.client  # type: ignore


class WindowsScheduler:
    """Windows Task Scheduler integration"""

    def __init__(self, script_dir: Optional[str] = None):
        if script_dir is None:
            self.script_dir = Path(__file__).parent.absolute()
        else:
            self.script_dir = Path(script_dir)

        self.python_exe = sys.executable
        self.file_organizer_script = self.script_dir / "file_organizer.py"
        self.watcher_script = self.script_dir / "watcher.py"

    def create_daily_task(
        self, task_name: str = "FileOrganizerDaily", time: str = "09:00"
    ):
        """Create a task that runs daily at a specific time"""
        try:
            scheduler = win32com.client.Dispatch("Schedule.Service")
            scheduler.Connect()
            root_folder = scheduler.GetFolder("\\")

            # Create task definition
            task_def = scheduler.NewTask(0)

            # Set task info
            task_def.RegistrationInfo.Description = "Organize files daily"
            task_def.RegistrationInfo.Author = os.getenv("USERNAME", "User")

            # Set settings
            task_def.Settings.Enabled = True
            task_def.Settings.StopIfGoingOnBatteries = False
            task_def.Settings.DisallowStartIfOnBatteries = False
            task_def.Settings.AllowDemandStart = True
            task_def.Settings.StartWhenAvailable = True
            task_def.Settings.RunOnlyIfNetworkAvailable = False

            # Create daily trigger
            TASK_TRIGGER_DAILY = 2
            trigger = task_def.Triggers.Create(TASK_TRIGGER_DAILY)
            trigger.StartBoundary = self._format_time(time)
            trigger.DaysInterval = 1
            trigger.Enabled = True

            # Create action
            TASK_ACTION_EXEC = 0
            action = task_def.Actions.Create(TASK_ACTION_EXEC)
            action.Path = self.python_exe
            action.Arguments = f'"{self.file_organizer_script}"'
            action.WorkingDirectory = str(self.script_dir)

            # Register task
            TASK_CREATE_OR_UPDATE = 6
            TASK_LOGON_NONE = 0
            root_folder.RegisterTaskDefinition(
                task_name,
                task_def,
                TASK_CREATE_OR_UPDATE,
                "",  # User (empty for current user)
                "",  # Password
                TASK_LOGON_NONE,
            )

            print(f"✓ Daily task '{task_name}' created successfully!")
            print(f"  Will run every day at {time}")
            return True

        except Exception as e:
            print(f"✗ Error creating daily task: {str(e)}")
            return False

    def create_startup_task(
        self, task_name: str = "FileOrganizerStartup", run_watcher: bool = True
    ):
        """Create a task that runs at system startup or user login"""
        try:
            scheduler = win32com.client.Dispatch("Schedule.Service")
            scheduler.Connect()
            root_folder = scheduler.GetFolder("\\")

            # Create task definition
            task_def = scheduler.NewTask(0)

            # Set task info
            description = (
                "Start file watcher at login"
                if run_watcher
                else "Organize files at startup"
            )
            task_def.RegistrationInfo.Description = description
            task_def.RegistrationInfo.Author = os.getenv("USERNAME", "User")

            # Set settings
            task_def.Settings.Enabled = True
            task_def.Settings.StopIfGoingOnBatteries = False
            task_def.Settings.DisallowStartIfOnBatteries = False
            task_def.Settings.AllowDemandStart = True
            task_def.Settings.StartWhenAvailable = True
            task_def.Settings.RunOnlyIfNetworkAvailable = False

            if run_watcher:
                # For watcher, don't stop on idle
                task_def.Settings.AllowHardTerminate = False
                task_def.Settings.ExecutionTimeLimit = "PT0S"  # No time limit

            # Create logon trigger (runs when user logs in)
            TASK_TRIGGER_LOGON = 9
            trigger = task_def.Triggers.Create(TASK_TRIGGER_LOGON)
            trigger.Enabled = True
            # Add delay to let system stabilize
            trigger.Delay = "PT30S"  # 30 seconds delay

            # Create action
            TASK_ACTION_EXEC = 0
            action = task_def.Actions.Create(TASK_ACTION_EXEC)
            action.Path = self.python_exe

            if run_watcher:
                action.Arguments = f'"{self.watcher_script}" --organize-first'
            else:
                action.Arguments = f'"{self.file_organizer_script}"'

            action.WorkingDirectory = str(self.script_dir)

            # Register task
            TASK_CREATE_OR_UPDATE = 6
            TASK_LOGON_NONE = 0
            root_folder.RegisterTaskDefinition(
                task_name,
                task_def,
                TASK_CREATE_OR_UPDATE,
                "",  # User (empty for current user)
                "",  # Password
                TASK_LOGON_NONE,
            )

            mode = "watcher" if run_watcher else "organizer"
            print(f"✓ Startup task '{task_name}' created successfully!")
            print(f"  Will run {mode} at user login")
            return True

        except Exception as e:
            print(f"✗ Error creating startup task: {str(e)}")
            return False

    def delete_task(self, task_name: str):
        """Delete a scheduled task"""
        try:
            scheduler = win32com.client.Dispatch("Schedule.Service")
            scheduler.Connect()
            root_folder = scheduler.GetFolder("\\")
            root_folder.DeleteTask(task_name, 0)
            print(f"✓ Task '{task_name}' deleted successfully!")
            return True
        except Exception as e:
            print(f"✗ Error deleting task: {str(e)}")
            return False

    def list_tasks(self):
        """List all file organizer related tasks"""
        try:
            scheduler = win32com.client.Dispatch("Schedule.Service")
            scheduler.Connect()
            root_folder = scheduler.GetFolder("\\")
            tasks = root_folder.GetTasks(0)

            print("\nFile Organizer Tasks:")
            print("=" * 60)

            found = False
            for task in tasks:
                if "FileOrganizer" in task.Name:
                    found = True
                    state = "Enabled" if task.Enabled else "Disabled"
                    print(f"  {task.Name} [{state}]")

            if not found:
                print("  No tasks found")

            print("=" * 60)
            return True

        except Exception as e:
            print(f"✗ Error listing tasks: {str(e)}")
            return False

    def _format_time(self, time_str: str) -> str:
        """Format time string for Windows Task Scheduler"""
        from datetime import datetime, timedelta

        # Parse time
        hour, minute = map(int, time_str.split(":"))

        # Create datetime for tomorrow at specified time
        now = datetime.now()
        scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if scheduled < now:
            scheduled += timedelta(days=1)

        # Format as ISO 8601
        return scheduled.strftime("%Y-%m-%dT%H:%M:%S")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Setup Windows Task Scheduler for File Organizer"
    )
    parser.add_argument(
        "--setup-daily", action="store_true", help="Setup daily organization task"
    )
    parser.add_argument(
        "--setup-startup",
        action="store_true",
        help="Setup task to run at startup/login",
    )
    parser.add_argument(
        "--setup-all",
        action="store_true",
        help="Setup all tasks (daily + startup watcher)",
    )
    parser.add_argument(
        "--time",
        default="09:00",
        help="Time for daily task (HH:MM format, default: 09:00)",
    )
    parser.add_argument("--delete", metavar="TASK_NAME", help="Delete a task by name")
    parser.add_argument(
        "--list", action="store_true", help="List all file organizer tasks"
    )

    args = parser.parse_args()

    # Check if running with admin privileges
    try:
        import ctypes

        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        is_admin = False

    if not is_admin:
        print("⚠ Warning: Not running as administrator")
        print("  Some operations may require elevated privileges")
        print()

    scheduler = WindowsScheduler()

    # Handle commands
    if args.list:
        scheduler.list_tasks()

    elif args.delete:
        scheduler.delete_task(args.delete)

    elif args.setup_all:
        print("Setting up all tasks...\n")
        scheduler.create_daily_task(time=args.time)
        print()
        scheduler.create_startup_task(run_watcher=True)
        print("\n✓ All tasks setup complete!")

    elif args.setup_daily:
        scheduler.create_daily_task(time=args.time)

    elif args.setup_startup:
        scheduler.create_startup_task(run_watcher=True)

    else:
        # Interactive mode
        print("\n" + "=" * 60)
        print("FILE ORGANIZER - TASK SCHEDULER SETUP")
        print("=" * 60)
        print("\nWhat would you like to do?")
        print("  1) Setup daily organization task")
        print("  2) Setup startup watcher (recommended)")
        print("  3) Setup both (daily + startup)")
        print("  4) List existing tasks")
        print("  5) Delete a task")
        print("  6) Exit")

        choice = input("\nEnter your choice (1-6): ").strip()

        if choice == "1":
            time = input("Enter time for daily task (HH:MM, default 09:00): ").strip()
            if not time:
                time = "09:00"
            scheduler.create_daily_task(time=time)

        elif choice == "2":
            scheduler.create_startup_task(run_watcher=True)

        elif choice == "3":
            time = input("Enter time for daily task (HH:MM, default 09:00): ").strip()
            if not time:
                time = "09:00"
            scheduler.create_daily_task(time=time)
            print()
            scheduler.create_startup_task(run_watcher=True)
            print("\n✓ All tasks setup complete!")

        elif choice == "4":
            scheduler.list_tasks()

        elif choice == "5":
            task_name = input("Enter task name to delete: ").strip()
            if task_name:
                scheduler.delete_task(task_name)

        elif choice == "6":
            print("Exiting...")

        else:
            print("Invalid choice!")


if __name__ == "__main__":
    main()
