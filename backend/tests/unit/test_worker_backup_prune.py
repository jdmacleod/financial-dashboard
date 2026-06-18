"""Unit tests for backup_tasks._prune_old_backups."""

from __future__ import annotations

import os
import pathlib
import time


def test_prune_old_backups_removes_expired_file(tmp_path: pathlib.Path) -> None:
    """Files older than retention_days are deleted."""
    from app.worker.tasks.backup_tasks import _prune_old_backups

    old_file = tmp_path / "hearthledger_backup_2020-01-01T00-00-00Z.dump.enc"
    old_file.write_bytes(b"old backup")
    old_mtime = time.time() - (60 * 86400)  # 60 days ago
    os.utime(old_file, (old_mtime, old_mtime))

    _prune_old_backups(str(tmp_path), retention_days=30)

    assert not old_file.exists()


def test_prune_old_backups_keeps_recent_file(tmp_path: pathlib.Path) -> None:
    """Files within retention_days are not deleted."""
    from app.worker.tasks.backup_tasks import _prune_old_backups

    recent_file = tmp_path / "hearthledger_backup_2099-01-01T00-00-00Z.dump.enc"
    recent_file.write_bytes(b"recent backup")

    _prune_old_backups(str(tmp_path), retention_days=30)

    assert recent_file.exists()


def test_prune_old_backups_ignores_non_matching_files(tmp_path: pathlib.Path) -> None:
    """Files that don't match the hearthledger_backup_*.dump.enc glob are untouched."""
    from app.worker.tasks.backup_tasks import _prune_old_backups

    other_file = tmp_path / "some_other_file.txt"
    other_file.write_bytes(b"unrelated")
    old_mtime = time.time() - (365 * 86400)
    os.utime(other_file, (old_mtime, old_mtime))

    _prune_old_backups(str(tmp_path), retention_days=30)

    assert other_file.exists()
