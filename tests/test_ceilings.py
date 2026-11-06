"""The ceilings ruff and complexipy do not check: Halstead difficulty, function and file length."""

from __future__ import annotations

from pathlib import Path

import ceilings

ROOT = Path(__file__).resolve().parent.parent


def test_the_repository_is_within_every_ceiling():
    assert ceilings.main([str(ROOT / "tools"), str(ROOT / "tests")]) == 0


def test_a_long_function_is_named(tmp_path):
    body = "\n".join(f"    x{n} = {n}" for n in range(ceilings.MAX_FUNCTION_LINES))
    src = tmp_path / "long.py"
    src.write_text(f"def long():\n{body}\n")
    assert ceilings.offences(src) == [f"{src}:1 long: 61 lines, ceiling {ceilings.MAX_FUNCTION_LINES}"]


def test_a_difficult_function_is_named(tmp_path, monkeypatch):
    # radon scores this at about 11.7; lower the ceiling rather than write a monster.
    monkeypatch.setattr(ceilings, "MAX_DIFFICULTY", 10)
    terms = " ".join(f"{op} a" for op in ("+", "-", "*", "/", "//", "%", "**", "<<", ">>", "&", "|", "^") * 3)
    src = tmp_path / "hard.py"
    src.write_text(f"def ok():\n    return 1\n\n\ndef hard(a, b):\n    return b {terms}\n")
    assert ceilings.offences(src) == [f"{src}:5 hard: Halstead difficulty 11.7, ceiling 10"]


def test_a_long_file_is_named(tmp_path):
    src = tmp_path / "big.py"
    src.write_text("x = 1\n" * (ceilings.MAX_FILE_LINES + 1))
    assert ceilings.offences(src) == [f"{src}: 501 lines, ceiling {ceilings.MAX_FILE_LINES}"]


def test_main_fails_and_reports_every_offence(tmp_path, capsys):
    (tmp_path / "big.py").write_text("x = 1\n" * (ceilings.MAX_FILE_LINES + 1))
    (tmp_path / "ok.py").write_text("def ok():\n    return 1\n")
    assert ceilings.main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "big.py: 501 lines" in out
    assert out.strip().endswith("ceilings: 2 files, 1 over")
