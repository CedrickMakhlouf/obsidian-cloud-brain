"""Tests voor de ingestion-module."""

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.upload_vault import compute_md5, parse_note


def test_compute_md5():
    text = "hallo wereld"
    expected = hashlib.md5(text.encode("utf-8")).hexdigest()
    assert compute_md5(text) == expected


def test_parse_note(tmp_path: Path):
    note_content = """---
title: Test Notitie
tags: [azure, python]
---
Dit is de inhoud van mijn testnotitie.
"""
    note_file = tmp_path / "test_note.md"
    note_file.write_text(note_content, encoding="utf-8")

    result = parse_note(note_file)

    assert result["title"] == "test_note"
    assert "azure" in result["tags"]
    assert "python" in result["tags"]
    assert "Dit is de inhoud" in result["content"]
    assert result["md5"] == compute_md5(result["content"])


def test_parse_note_no_frontmatter(tmp_path: Path):
    note_file = tmp_path / "plain.md"
    note_file.write_text("Geen frontmatter hier.", encoding="utf-8")

    result = parse_note(note_file)

    assert result["title"] == "plain"
    assert result["tags"] == []
    assert "Geen frontmatter" in result["content"]
