from pathlib import Path

from ai_safe_context.cli import run


def test_cli_writes_context_file_and_prints_summary(tmp_path: Path, capsys):
    (tmp_path / "app.py").write_text("print('hi')\n", encoding="utf-8")
    output = tmp_path / "context.md"

    exit_code = run([str(tmp_path), "--output", str(output)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert output.exists()
    assert "Generated" in captured.out
    assert "context.md" in captured.out
    assert "app.py" in output.read_text(encoding="utf-8")


def test_cli_writes_machine_readable_json_summary(tmp_path: Path):
    (tmp_path / "app.py").write_text("print('hi')\n", encoding="utf-8")
    output = tmp_path / "context.md"
    summary = tmp_path / "summary.json"

    exit_code = run([str(tmp_path), "--output", str(output), "--json-summary", str(summary)])

    assert exit_code == 0
    assert summary.exists()
    text = summary.read_text(encoding="utf-8")
    assert '"included_files": 1' in text
    assert '"output"' in text
    assert "context.md" in text
