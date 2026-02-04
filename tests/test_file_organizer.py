import json
import runpy
import sys
from pathlib import Path

import pytest

import file_organizer
from file_organizer import FileOrganizer, main


def write_config(tmp_path: Path, overrides: dict | None = None) -> Path:
    config = {
        "watch_directories": [str(tmp_path / "watch")],
        "organize_rules": {
            "Documents": {
                "extensions": [".txt"],
                "target_folder": str(tmp_path / "organized" / "Documents"),
            },
            "Images": {
                "extensions": [".png"],
                "target_folder": str(tmp_path / "organized" / "Images"),
            },
        },
        "organize_by_date": False,
        "date_format": "%Y-%m",
        "ignore_extensions": [".tmp"],
        "ignore_files": ["ignore.me"],
        "duplicate_handling": "rename",
        "recursive": False,
        "dry_run": False,
        "enable_logging": False,
        "log_level": "INFO",
    }
    if overrides:
        config.update(overrides)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return config_path


def test_load_config_missing(tmp_path: Path):
    with pytest.raises(SystemExit):
        FileOrganizer(str(tmp_path / "missing.json"))


def test_load_config_invalid_json(tmp_path: Path):
    config_path = tmp_path / "config.json"
    config_path.write_text("{invalid}", encoding="utf-8")
    with pytest.raises(SystemExit):
        FileOrganizer(str(config_path))


def test_get_file_category_ignored_extension(tmp_path: Path):
    config_path = write_config(tmp_path)
    organizer = FileOrganizer(str(config_path))
    file_path = tmp_path / "file.tmp"
    file_path.write_text("x", encoding="utf-8")
    assert organizer._get_file_category(file_path) is None


def test_get_file_category_ignored_file(tmp_path: Path):
    config_path = write_config(tmp_path)
    organizer = FileOrganizer(str(config_path))
    file_path = tmp_path / "ignore.me"
    file_path.write_text("x", encoding="utf-8")
    assert organizer._get_file_category(file_path) is None


def test_get_file_category_extras(tmp_path: Path):
    config_path = write_config(tmp_path)
    organizer = FileOrganizer(str(config_path))
    file_path = tmp_path / "file.unknown"
    file_path.write_text("x", encoding="utf-8")
    assert organizer._get_file_category(file_path) == "Extras"


def test_get_target_path_extras(tmp_path: Path):
    config_path = write_config(tmp_path)
    organizer = FileOrganizer(str(config_path))
    file_path = tmp_path / "file.unknown"
    file_path.write_text("x", encoding="utf-8")
    target = organizer._get_target_path(file_path, "Extras")
    assert target.parent.name == "Extras"


def test_get_target_path_extras_default_folder(tmp_path: Path, monkeypatch):
    config_path = write_config(tmp_path, {"organize_rules": {}})
    organizer = FileOrganizer(str(config_path))
    file_path = tmp_path / "file.unknown"
    file_path.write_text("x", encoding="utf-8")

    monkeypatch.setattr(file_organizer.Path, "mkdir", lambda *_a, **_k: None)

    target = organizer._get_target_path(file_path, "Extras")
    assert target.name == "file.unknown"


def test_get_target_path_with_date(tmp_path: Path):
    config_path = write_config(
        tmp_path, {"organize_by_date": True, "date_format": "%Y-%m"}
    )
    organizer = FileOrganizer(str(config_path))
    file_path = tmp_path / "doc.txt"
    file_path.write_text("x", encoding="utf-8")
    target = organizer._get_target_path(file_path, "Documents")
    assert target.parent.name.count("-") == 1


def test_handle_duplicate_skip(tmp_path: Path):
    config_path = write_config(tmp_path, {"duplicate_handling": "skip"})
    organizer = FileOrganizer(str(config_path))
    target = tmp_path / "organized" / "Documents" / "file.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("a", encoding="utf-8")
    assert organizer._handle_duplicate(target) is None


def test_handle_duplicate_overwrite(tmp_path: Path):
    config_path = write_config(tmp_path, {"duplicate_handling": "overwrite"})
    organizer = FileOrganizer(str(config_path))
    target = tmp_path / "organized" / "Documents" / "file.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("a", encoding="utf-8")
    assert organizer._handle_duplicate(target) == target


def test_handle_duplicate_rename(tmp_path: Path):
    config_path = write_config(tmp_path, {"duplicate_handling": "rename"})
    organizer = FileOrganizer(str(config_path))
    target = tmp_path / "organized" / "Documents" / "file.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("a", encoding="utf-8")
    new_target = organizer._handle_duplicate(target)
    assert new_target is not None
    assert new_target.name.startswith("file_")


def test_organize_file_dry_run(tmp_path: Path):
    config_path = write_config(tmp_path, {"dry_run": True})
    organizer = FileOrganizer(str(config_path))
    src_dir = tmp_path / "watch"
    src_dir.mkdir()
    file_path = src_dir / "doc.txt"
    file_path.write_text("hello", encoding="utf-8")

    assert organizer.organize_file(file_path) is True
    assert file_path.exists()
    assert organizer.stats["moved"] == 1


def test_organize_file_move(tmp_path: Path):
    config_path = write_config(tmp_path)
    organizer = FileOrganizer(str(config_path))
    src_dir = tmp_path / "watch"
    src_dir.mkdir()
    file_path = src_dir / "doc.txt"
    file_path.write_text("hello", encoding="utf-8")

    assert organizer.organize_file(file_path) is True
    target = tmp_path / "organized" / "Documents" / "doc.txt"
    assert target.exists()
    assert organizer.stats["moved"] == 1


def test_organize_file_ignored(tmp_path: Path):
    config_path = write_config(tmp_path)
    organizer = FileOrganizer(str(config_path))
    file_path = tmp_path / "file.tmp"
    file_path.write_text("x", encoding="utf-8")

    assert organizer.organize_file(file_path) is False
    assert organizer.stats["skipped"] == 1


def test_organize_file_duplicate_skipped(tmp_path: Path):
    config_path = write_config(tmp_path, {"duplicate_handling": "skip"})
    organizer = FileOrganizer(str(config_path))
    src_dir = tmp_path / "watch"
    src_dir.mkdir()
    file_path = src_dir / "doc.txt"
    file_path.write_text("hello", encoding="utf-8")

    target = tmp_path / "organized" / "Documents" / "doc.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("existing", encoding="utf-8")

    assert organizer.organize_file(file_path) is False
    assert organizer.stats["skipped"] == 1


def test_organize_file_directory(tmp_path: Path):
    config_path = write_config(tmp_path)
    organizer = FileOrganizer(str(config_path))
    dir_path = tmp_path / "dir"
    dir_path.mkdir()

    assert organizer.organize_file(dir_path) is False


def test_organize_file_permission_error(tmp_path: Path, monkeypatch):
    config_path = write_config(tmp_path)
    organizer = FileOrganizer(str(config_path))
    src_dir = tmp_path / "watch"
    src_dir.mkdir()
    file_path = src_dir / "doc.txt"
    file_path.write_text("hello", encoding="utf-8")

    def raise_permission_error(*_args, **_kwargs):
        raise PermissionError("no")

    monkeypatch.setattr("shutil.move", raise_permission_error)
    assert organizer.organize_file(file_path) is False
    assert organizer.stats["errors"] == 1


def test_organize_file_generic_error(tmp_path: Path, monkeypatch):
    config_path = write_config(tmp_path)
    organizer = FileOrganizer(str(config_path))
    src_dir = tmp_path / "watch"
    src_dir.mkdir()
    file_path = src_dir / "doc.txt"
    file_path.write_text("hello", encoding="utf-8")

    def raise_error(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("shutil.move", raise_error)
    assert organizer.organize_file(file_path) is False
    assert organizer.stats["errors"] == 1


def test_organize_directory_nonexistent(tmp_path: Path):
    config_path = write_config(tmp_path)
    organizer = FileOrganizer(str(config_path))
    organizer.organize_directory(str(tmp_path / "missing"))
    assert organizer.stats == {"moved": 0, "skipped": 0, "errors": 0}


def test_organize_directory_not_dir(tmp_path: Path):
    config_path = write_config(tmp_path)
    organizer = FileOrganizer(str(config_path))
    file_path = tmp_path / "not_dir.txt"
    file_path.write_text("x", encoding="utf-8")
    organizer.organize_directory(str(file_path))
    assert organizer.stats == {"moved": 0, "skipped": 0, "errors": 0}


def test_organize_directory_recursive(tmp_path: Path):
    config_path = write_config(tmp_path, {"recursive": True})
    organizer = FileOrganizer(str(config_path))
    watch_dir = tmp_path / "watch"
    nested = watch_dir / "nested"
    nested.mkdir(parents=True)
    file_path = nested / "doc.txt"
    file_path.write_text("hello", encoding="utf-8")

    organizer.organize_directory(str(watch_dir))
    target = tmp_path / "organized" / "Documents" / "doc.txt"
    assert target.exists()


def test_organize_directory_non_recursive(tmp_path: Path):
    config_path = write_config(tmp_path, {"recursive": False})
    organizer = FileOrganizer(str(config_path))
    watch_dir = tmp_path / "watch"
    nested = watch_dir / "nested"
    nested.mkdir(parents=True)
    file_path = nested / "doc.txt"
    file_path.write_text("hello", encoding="utf-8")

    organizer.organize_directory(str(watch_dir))
    target = tmp_path / "organized" / "Documents" / "doc.txt"
    assert not target.exists()


def test_run_no_watch_dirs(tmp_path: Path):
    config_path = write_config(tmp_path, {"watch_directories": []})
    organizer = FileOrganizer(str(config_path))
    organizer.run()
    assert organizer.stats == {"moved": 0, "skipped": 0, "errors": 0}


def test_run_with_watch_dirs_calls_organize(tmp_path: Path, monkeypatch):
    config_path = write_config(tmp_path)
    organizer = FileOrganizer(str(config_path))
    called = {"count": 0}

    def fake_organize(_directory):
        called["count"] += 1

    monkeypatch.setattr(organizer, "organize_directory", fake_organize)
    organizer.run()
    assert called["count"] == 1


def test_print_config_info(tmp_path: Path, capsys):
    config_path = write_config(tmp_path)
    organizer = FileOrganizer(str(config_path))
    organizer.print_config_info()
    captured = capsys.readouterr()
    assert "FILE ORGANIZER CONFIGURATION" in captured.out


def test_main_show_config(tmp_path: Path, monkeypatch, capsys):
    config_path = write_config(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["file_organizer.py", "--config", str(config_path), "--show-config"],
    )
    main()
    captured = capsys.readouterr()
    assert "FILE ORGANIZER CONFIGURATION" in captured.out


def test_main_dry_run_sets_flag(tmp_path: Path, monkeypatch):
    config_path = write_config(tmp_path)
    monkeypatch.setattr(
        sys, "argv", ["file_organizer.py", "--config", str(config_path), "--dry-run"]
    )

    called = {"run": False}

    def fake_run(self):
        called["run"] = True
        assert self.config["dry_run"] is True

    monkeypatch.setattr(FileOrganizer, "run", fake_run)
    main()
    assert called["run"] is True


def test_module_entrypoint(tmp_path: Path, monkeypatch, capsys):
    config_path = write_config(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["file_organizer.py", "--config", str(config_path), "--show-config"],
    )
    runpy.run_module("file_organizer", run_name="__main__")
    captured = capsys.readouterr()
    assert "FILE ORGANIZER CONFIGURATION" in captured.out
