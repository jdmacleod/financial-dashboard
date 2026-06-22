"""Unit tests for seed_demo_data._confirm."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

_SCRIPTS_DIR = str(Path(__file__).resolve().parents[2] / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import seed_demo_data  # noqa: E402


class TestConfirm:
    def test_yes_flag_skips_input(self) -> None:
        assert seed_demo_data._confirm("Do the thing?", yes=True) is True

    def test_y_answer_returns_true(self) -> None:
        with patch("builtins.input", return_value="y"):
            assert seed_demo_data._confirm("Do the thing?", yes=False) is True

    def test_n_answer_returns_false(self) -> None:
        with patch("builtins.input", return_value="n"):
            assert seed_demo_data._confirm("Do the thing?", yes=False) is False

    def test_empty_answer_returns_false(self) -> None:
        with patch("builtins.input", return_value=""):
            assert seed_demo_data._confirm("Do the thing?", yes=False) is False
