import sys
import types
import datetime as datetime_module
from pathlib import Path

import pytest

import scheduler_setup


class DummyFolder:
    def __init__(self):
        self.registered = []
        self.deleted = []
        self.tasks = []

    def RegisterTaskDefinition(self, *args):
        self.registered.append(args)

    def DeleteTask(self, task_name, _flags):
        self.deleted.append(task_name)

    def GetTasks(self, _flags):
        return self.tasks


class DummyTask:
    def __init__(self, name, enabled=True):
        self.Name = name
        self.Enabled = enabled


class DummyTrigger:
    def __init__(self):
        self.StartBoundary = None
        self.DaysInterval = None
        self.Enabled = None
        self.Delay = None


class DummyAction:
    def __init__(self):
        self.Path = None
        self.Arguments = None
        self.WorkingDirectory = None


class DummyTriggers:
    def __init__(self):
        self.created = []

    def Create(self, _trigger_type):
        trigger = DummyTrigger()
        self.created.append(trigger)
        return trigger


class DummyActions:
    def __init__(self):
        self.created = []

    def Create(self, _action_type):
        action = DummyAction()
        self.created.append(action)
        return action


class DummySettings:
    def __init__(self):
        self.Enabled = None
        self.StopIfGoingOnBatteries = None
        self.DisallowStartIfOnBatteries = None
        self.AllowDemandStart = None
        self.StartWhenAvailable = None
        self.RunOnlyIfNetworkAvailable = None
        self.AllowHardTerminate = None
        self.ExecutionTimeLimit = None


class DummyRegistrationInfo:
    def __init__(self):
        self.Description = None
        self.Author = None


class DummyTaskDef:
    def __init__(self):
        self.RegistrationInfo = DummyRegistrationInfo()
        self.Settings = DummySettings()
        self.Triggers = DummyTriggers()
        self.Actions = DummyActions()


class DummyScheduler:
    def __init__(self, folder: DummyFolder):
        self.folder = folder

    def Connect(self):
        return None

    def GetFolder(self, _path):
        return self.folder

    def NewTask(self, _flags):
        return DummyTaskDef()


class DummyClient:
    def __init__(self, folder: DummyFolder):
        self.folder = folder

    def Dispatch(self, _name):
        return DummyScheduler(self.folder)


def test_create_daily_task_success(monkeypatch, tmp_path: Path):
    folder = DummyFolder()
    dummy_client = DummyClient(folder)
    monkeypatch.setattr(scheduler_setup.win32com, "client", dummy_client)

    scheduler = scheduler_setup.WindowsScheduler(str(tmp_path))
    assert scheduler.create_daily_task(task_name="TestDaily", time="10:00") is True
    assert folder.registered


def test_create_daily_task_failure(monkeypatch, tmp_path: Path):
    def raise_error(_name):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        scheduler_setup.win32com, "client", type("X", (), {"Dispatch": raise_error})
    )

    scheduler = scheduler_setup.WindowsScheduler(str(tmp_path))
    assert scheduler.create_daily_task(task_name="TestDaily") is False


def test_create_startup_task_success(monkeypatch, tmp_path: Path):
    folder = DummyFolder()
    dummy_client = DummyClient(folder)
    monkeypatch.setattr(scheduler_setup.win32com, "client", dummy_client)

    scheduler = scheduler_setup.WindowsScheduler(str(tmp_path))
    assert (
        scheduler.create_startup_task(task_name="TestStartup", run_watcher=True) is True
    )
    assert folder.registered


def test_create_startup_task_success_no_watcher(monkeypatch, tmp_path: Path):
    folder = DummyFolder()
    dummy_client = DummyClient(folder)
    monkeypatch.setattr(scheduler_setup.win32com, "client", dummy_client)

    scheduler = scheduler_setup.WindowsScheduler(str(tmp_path))
    assert (
        scheduler.create_startup_task(task_name="TestStartup", run_watcher=False)
        is True
    )
    assert folder.registered


def test_create_startup_task_failure(monkeypatch, tmp_path: Path):
    def raise_error(_name):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        scheduler_setup.win32com, "client", type("X", (), {"Dispatch": raise_error})
    )

    scheduler = scheduler_setup.WindowsScheduler(str(tmp_path))
    assert (
        scheduler.create_startup_task(task_name="TestStartup", run_watcher=False)
        is False
    )


def test_delete_task_success(monkeypatch, tmp_path: Path):
    folder = DummyFolder()
    dummy_client = DummyClient(folder)
    monkeypatch.setattr(scheduler_setup.win32com, "client", dummy_client)

    scheduler = scheduler_setup.WindowsScheduler(str(tmp_path))
    assert scheduler.delete_task("TestTask") is True
    assert folder.deleted == ["TestTask"]


def test_delete_task_failure(monkeypatch, tmp_path: Path):
    def raise_error(_name):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        scheduler_setup.win32com, "client", type("X", (), {"Dispatch": raise_error})
    )

    scheduler = scheduler_setup.WindowsScheduler(str(tmp_path))
    assert scheduler.delete_task("TestTask") is False


def test_list_tasks(monkeypatch, tmp_path: Path, capsys):
    folder = DummyFolder()
    folder.tasks = [DummyTask("FileOrganizerDaily", True), DummyTask("Other", False)]
    dummy_client = DummyClient(folder)
    monkeypatch.setattr(scheduler_setup.win32com, "client", dummy_client)

    scheduler = scheduler_setup.WindowsScheduler(str(tmp_path))
    assert scheduler.list_tasks() is True
    captured = capsys.readouterr()
    assert "FileOrganizerDaily" in captured.out


def test_list_tasks_none_found(monkeypatch, tmp_path: Path, capsys):
    folder = DummyFolder()
    folder.tasks = [DummyTask("Other", False)]
    dummy_client = DummyClient(folder)
    monkeypatch.setattr(scheduler_setup.win32com, "client", dummy_client)

    scheduler = scheduler_setup.WindowsScheduler(str(tmp_path))
    assert scheduler.list_tasks() is True
    captured = capsys.readouterr()
    assert "No tasks found" in captured.out


def test_list_tasks_failure(monkeypatch, tmp_path: Path):
    def raise_error(_name):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        scheduler_setup.win32com, "client", type("X", (), {"Dispatch": raise_error})
    )

    scheduler = scheduler_setup.WindowsScheduler(str(tmp_path))
    assert scheduler.list_tasks() is False


def test_format_time():
    scheduler = scheduler_setup.WindowsScheduler(str(Path.cwd()))
    formatted = scheduler._format_time("09:30")
    assert "T" in formatted


def test_format_time_rolls_to_next_day(monkeypatch):
    class FakeDateTime(datetime_module.datetime):
        @classmethod
        def now(cls):
            return cls(2026, 2, 4, 23, 0, 0)

    monkeypatch.setattr(datetime_module, "datetime", FakeDateTime)

    scheduler = scheduler_setup.WindowsScheduler(str(Path.cwd()))
    formatted = scheduler._format_time("01:00")
    assert formatted.startswith("2026-02-05T")


def test_main_branches(monkeypatch, tmp_path: Path):
    called = {"daily": 0, "startup": 0, "list": 0, "delete": 0}

    def fake_daily(self, *args, **kwargs):
        called["daily"] += 1
        return True

    def fake_startup(self, *args, **kwargs):
        called["startup"] += 1
        return True

    def fake_list(self, *args, **kwargs):
        called["list"] += 1
        return True

    def fake_delete(self, *args, **kwargs):
        called["delete"] += 1
        return True

    monkeypatch.setattr(
        scheduler_setup.WindowsScheduler, "create_daily_task", fake_daily
    )
    monkeypatch.setattr(
        scheduler_setup.WindowsScheduler, "create_startup_task", fake_startup
    )
    monkeypatch.setattr(scheduler_setup.WindowsScheduler, "list_tasks", fake_list)
    monkeypatch.setattr(scheduler_setup.WindowsScheduler, "delete_task", fake_delete)

    monkeypatch.setattr(
        sys, "argv", ["scheduler_setup.py", "--setup-daily", "--time", "08:00"]
    )
    scheduler_setup.main()

    monkeypatch.setattr(sys, "argv", ["scheduler_setup.py", "--setup-startup"])
    scheduler_setup.main()

    monkeypatch.setattr(sys, "argv", ["scheduler_setup.py", "--setup-all"])
    scheduler_setup.main()

    monkeypatch.setattr(sys, "argv", ["scheduler_setup.py", "--list"])
    scheduler_setup.main()

    monkeypatch.setattr(
        sys, "argv", ["scheduler_setup.py", "--delete", "FileOrganizerDaily"]
    )
    scheduler_setup.main()

    assert called["daily"] >= 2
    assert called["startup"] >= 2
    assert called["list"] == 1
    assert called["delete"] == 1


def test_main_interactive_exit(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["scheduler_setup.py"])
    monkeypatch.setattr("builtins.input", lambda _prompt: "6")

    scheduler_setup.main()


def test_main_not_admin_warning(monkeypatch, capsys):
    dummy_ctypes = types.SimpleNamespace(
        windll=types.SimpleNamespace(
            shell32=types.SimpleNamespace(IsUserAnAdmin=lambda: 0)
        )
    )
    monkeypatch.setitem(sys.modules, "ctypes", dummy_ctypes)
    monkeypatch.setattr(sys, "argv", ["scheduler_setup.py", "--list"])

    def fake_list(self):
        return True

    monkeypatch.setattr(scheduler_setup.WindowsScheduler, "list_tasks", fake_list)
    scheduler_setup.main()
    captured = capsys.readouterr()
    assert "Not running as administrator" in captured.out


def test_main_admin_check_exception(monkeypatch):
    class BrokenCtypes:
        @property
        def windll(self):
            raise RuntimeError("boom")

    monkeypatch.setitem(sys.modules, "ctypes", BrokenCtypes())
    monkeypatch.setattr(sys, "argv", ["scheduler_setup.py", "--list"])

    def fake_list(self):
        return True

    monkeypatch.setattr(scheduler_setup.WindowsScheduler, "list_tasks", fake_list)
    scheduler_setup.main()


def test_main_interactive_choices(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["scheduler_setup.py"])

    calls = {"daily": 0, "startup": 0, "list": 0, "delete": 0}

    def fake_daily(self, *args, **kwargs):
        calls["daily"] += 1
        return True

    def fake_startup(self, *args, **kwargs):
        calls["startup"] += 1
        return True

    def fake_list(self, *args, **kwargs):
        calls["list"] += 1
        return True

    def fake_delete(self, *args, **kwargs):
        calls["delete"] += 1
        return True

    monkeypatch.setattr(
        scheduler_setup.WindowsScheduler, "create_daily_task", fake_daily
    )
    monkeypatch.setattr(
        scheduler_setup.WindowsScheduler, "create_startup_task", fake_startup
    )
    monkeypatch.setattr(scheduler_setup.WindowsScheduler, "list_tasks", fake_list)
    monkeypatch.setattr(scheduler_setup.WindowsScheduler, "delete_task", fake_delete)

    inputs = iter(
        [
            "1",  # choice daily
            "",  # default time
            "2",  # startup
            "3",  # both
            "",  # default time
            "4",  # list
            "5",  # delete
            "TaskName",
            "7",  # invalid
            "6",  # exit
        ]
    )

    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))

    scheduler_setup.main()
    scheduler_setup.main()
    scheduler_setup.main()
    scheduler_setup.main()
    scheduler_setup.main()
    scheduler_setup.main()
    scheduler_setup.main()

    assert calls["daily"] >= 2
    assert calls["startup"] >= 2
    assert calls["list"] == 1
    assert calls["delete"] == 1


def test_module_entrypoint(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["scheduler_setup.py", "--list"])

    folder = DummyFolder()
    dummy_client = DummyClient(folder)
    dummy_win32com = types.SimpleNamespace(client=dummy_client)
    monkeypatch.setitem(sys.modules, "win32com", dummy_win32com)

    import runpy

    runpy.run_module("scheduler_setup", run_name="__main__")
