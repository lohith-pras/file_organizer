from pathlib import Path
import json
import sys
from typing import cast

import pytest

import watcher


class DummyOrganizer:
    def __init__(self):
        self.called = []

    def organize_file(self, file_path: Path):
        self.called.append(file_path)


class DummyObserver:
    def __init__(self):
        self.scheduled = []
        self.started = False
        self.stopped = False
        self.joined = False

    def schedule(self, handler, path, recursive=False):
        self.scheduled.append((handler, path, recursive))

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def join(self):
        self.joined = True


class DummyEvent:
    def __init__(self, src_path=None, dest_path=None, is_directory=False):
        self.src_path = src_path
        self.dest_path = dest_path
        self.is_directory = is_directory


def test_handler_process_file_stable(tmp_path: Path, monkeypatch):
    organizer = DummyOrganizer()
    handler = watcher.FileOrganizerHandler(cast(watcher.FileOrganizer, organizer))

    file_path = tmp_path / "file.txt"
    file_path.write_text("hello", encoding="utf-8")

    monkeypatch.setattr(watcher.time, "sleep", lambda _t: None)

    handler._process_file(file_path, "created")
    assert organizer.called == [file_path]


def test_handler_process_file_size_changes(tmp_path: Path, monkeypatch):
    organizer = DummyOrganizer()
    handler = watcher.FileOrganizerHandler(cast(watcher.FileOrganizer, organizer))

    file_path = tmp_path / "file.txt"
    file_path.write_text("hello", encoding="utf-8")

    calls = {"count": 0}

    def fake_sleep(_t):
        calls["count"] += 1
        if calls["count"] == 2:
            file_path.write_text("hello world", encoding="utf-8")

    debug_called = {"count": 0}

    def fake_debug(_msg):
        debug_called["count"] += 1

    monkeypatch.setattr(handler.logger, "debug", fake_debug)
    monkeypatch.setattr(watcher.time, "sleep", fake_sleep)

    handler._process_file(file_path, "created")
    assert organizer.called == []
    assert debug_called["count"] == 1


def test_handler_skip_if_processing(tmp_path: Path, monkeypatch):
    organizer = DummyOrganizer()
    handler = watcher.FileOrganizerHandler(cast(watcher.FileOrganizer, organizer))

    file_path = tmp_path / "file.txt"
    file_path.write_text("hello", encoding="utf-8")
    handler.processing_files.add(str(file_path))

    monkeypatch.setattr(watcher.time, "sleep", lambda _t: None)
    handler._process_file(file_path, "created")
    assert organizer.called == []


def test_on_created_ignores_directory(tmp_path: Path):
    organizer = DummyOrganizer()
    handler = watcher.FileOrganizerHandler(cast(watcher.FileOrganizer, organizer))
    event = DummyEvent(src_path=str(tmp_path), is_directory=True)

    handler.on_created(event)
    assert organizer.called == []


def test_on_moved_ignores_directory(tmp_path: Path):
    organizer = DummyOrganizer()
    handler = watcher.FileOrganizerHandler(cast(watcher.FileOrganizer, organizer))
    event = DummyEvent(dest_path=str(tmp_path), is_directory=True)

    handler.on_moved(event)
    assert organizer.called == []


def test_on_created_processes_file(tmp_path: Path, monkeypatch):
    organizer = DummyOrganizer()
    handler = watcher.FileOrganizerHandler(cast(watcher.FileOrganizer, organizer))

    file_path = tmp_path / "file.txt"
    file_path.write_text("hello", encoding="utf-8")

    called = {"path": None}

    def fake_process(path, event_type):
        called["path"] = (path, event_type)

    monkeypatch.setattr(handler, "_process_file", fake_process)

    event = DummyEvent(src_path=str(file_path), is_directory=False)
    handler.on_created(event)
    assert called["path"][0] == file_path
    assert called["path"][1] == "created"


def test_on_moved_processes_file(tmp_path: Path, monkeypatch):
    organizer = DummyOrganizer()
    handler = watcher.FileOrganizerHandler(cast(watcher.FileOrganizer, organizer))

    file_path = tmp_path / "file.txt"
    file_path.write_text("hello", encoding="utf-8")

    called = {"path": None}

    def fake_process(path, event_type):
        called["path"] = (path, event_type)

    monkeypatch.setattr(handler, "_process_file", fake_process)

    event = DummyEvent(dest_path=str(file_path), is_directory=False)
    handler.on_moved(event)
    assert called["path"][0] == file_path
    assert called["path"][1] == "moved"


def test_handler_process_file_missing(tmp_path: Path, monkeypatch):
    organizer = DummyOrganizer()
    handler = watcher.FileOrganizerHandler(cast(watcher.FileOrganizer, organizer))

    file_path = tmp_path / "missing.txt"

    monkeypatch.setattr(watcher.time, "sleep", lambda _t: None)

    handler._process_file(file_path, "created")
    assert organizer.called == []


def test_handler_process_file_deleted_midway(tmp_path: Path, monkeypatch):
    organizer = DummyOrganizer()
    handler = watcher.FileOrganizerHandler(cast(watcher.FileOrganizer, organizer))

    file_path = tmp_path / "file.txt"
    file_path.write_text("hello", encoding="utf-8")

    calls = {"count": 0}

    def fake_sleep(_t):
        calls["count"] += 1
        if calls["count"] == 2:
            file_path.unlink()

    monkeypatch.setattr(watcher.time, "sleep", fake_sleep)

    handler._process_file(file_path, "created")
    assert organizer.called == []


def test_handler_process_file_exception(tmp_path: Path, monkeypatch):
    organizer = DummyOrganizer()
    handler = watcher.FileOrganizerHandler(cast(watcher.FileOrganizer, organizer))

    file_path = tmp_path / "file.txt"
    file_path.write_text("hello", encoding="utf-8")

    monkeypatch.setattr(watcher.time, "sleep", lambda _t: None)

    original_stat = watcher.Path.stat

    def fake_stat(self):
        if self == file_path:
            raise RuntimeError("boom")
        return original_stat(self)

    monkeypatch.setattr(watcher.Path, "stat", fake_stat)

    handler._process_file(file_path, "created")
    assert organizer.called == []

    other_path = tmp_path / "other.txt"
    other_path.write_text("ok", encoding="utf-8")
    other_path.stat()


def test_watcher_start_no_dirs_exits(tmp_path: Path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"watch_directories": []}), encoding="utf-8")

    with pytest.raises(SystemExit):
        watcher.FileWatcher(str(config_path)).start()


def test_watcher_start_skips_missing_dirs_exits(tmp_path: Path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"watch_directories": [str(tmp_path / "missing")]}),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        watcher.FileWatcher(str(config_path)).start()


def test_watcher_start_success(tmp_path: Path, monkeypatch):
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"watch_directories": [str(watch_dir)]}),
        encoding="utf-8",
    )

    monkeypatch.setattr(watcher, "Observer", DummyObserver)

    fw = watcher.FileWatcher(str(config_path))
    fw.start()

    assert len(fw.observers) == 1
    observer = fw.observers[0]
    assert observer.started is True

    fw.stop()
    assert observer.stopped is True
    assert observer.joined is True


def test_watcher_run_keyboard_interrupt(tmp_path: Path, monkeypatch):
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"watch_directories": [str(watch_dir)]}),
        encoding="utf-8",
    )

    monkeypatch.setattr(watcher, "Observer", DummyObserver)
    monkeypatch.setattr(
        watcher.time, "sleep", lambda _t: (_ for _ in ()).throw(KeyboardInterrupt())
    )

    fw = watcher.FileWatcher(str(config_path))
    fw.run()


def test_watcher_run_unexpected_exception(tmp_path: Path, monkeypatch):
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"watch_directories": [str(watch_dir)]}),
        encoding="utf-8",
    )

    monkeypatch.setattr(watcher, "Observer", DummyObserver)

    def raise_error(_t):
        raise RuntimeError("boom")

    monkeypatch.setattr(watcher.time, "sleep", raise_error)

    fw = watcher.FileWatcher(str(config_path))
    with pytest.raises(SystemExit):
        fw.run()


def test_main_organize_first(tmp_path: Path, monkeypatch):
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"watch_directories": [str(watch_dir)]}),
        encoding="utf-8",
    )

    called = {"run": 0}

    class DummyOrganizer:
        def __init__(self, *_args, **_kwargs):
            pass

        def run(self):
            called["run"] += 1

    class DummyWatcher:
        def __init__(self, *_args, **_kwargs):
            pass

        def run(self):
            called["run"] += 1

    monkeypatch.setattr(watcher, "FileOrganizer", DummyOrganizer)
    monkeypatch.setattr(watcher, "FileWatcher", DummyWatcher)
    monkeypatch.setattr(
        sys, "argv", ["watcher.py", "--config", str(config_path), "--organize-first"]
    )

    watcher.main()
    assert called["run"] == 2


def test_main_default(tmp_path: Path, monkeypatch):
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"watch_directories": [str(watch_dir)]}),
        encoding="utf-8",
    )

    called = {"run": 0}

    class DummyWatcher:
        def __init__(self, *_args, **_kwargs):
            pass

        def run(self):
            called["run"] += 1

    monkeypatch.setattr(watcher, "FileWatcher", DummyWatcher)
    monkeypatch.setattr(sys, "argv", ["watcher.py", "--config", str(config_path)])

    watcher.main()
    assert called["run"] == 1


def test_module_entrypoint(tmp_path: Path, monkeypatch):
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"watch_directories": [str(watch_dir)]}),
        encoding="utf-8",
    )

    DummyWatcher = type(
        "DummyWatcher",
        (),
        {"__init__": lambda self, *_a, **_k: None, "run": lambda self: None},
    )

    monkeypatch.setattr(watcher, "FileWatcher", DummyWatcher)
    monkeypatch.setattr(sys, "argv", ["watcher.py", "--config", str(config_path)])

    import runpy

    runpy.run_module("watcher", run_name="__main__")
