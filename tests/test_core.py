from pathlib import Path

from ai_safe_context.core import PackOptions, pack_repository


def test_pack_repository_redacts_env_secret_and_includes_safe_source(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")
    (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-1234567890abcdef\n", encoding="utf-8")

    result = pack_repository(tmp_path, PackOptions())

    assert "src/app.py" in result.markdown
    assert "print('hello')" in result.markdown
    assert "sk-1234567890abcdef" not in result.markdown
    assert "[REDACTED:OPENAI_API_KEY]" in result.markdown
    assert result.summary.redactions >= 1


def test_pack_repository_respects_gitignore_and_skips_node_modules(tmp_path: Path):
    (tmp_path / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("should not appear", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "pkg.js").write_text("large dependency", encoding="utf-8")
    (tmp_path / "main.py").write_text("value = 1\n", encoding="utf-8")

    result = pack_repository(tmp_path, PackOptions())

    assert "main.py" in result.markdown
    assert "ignored.txt" not in result.markdown
    assert "node_modules/pkg.js" not in result.markdown
    assert result.summary.included_files == 1
    assert result.summary.skipped_files >= 2


def test_pack_repository_honors_max_file_size(tmp_path: Path):
    (tmp_path / "small.txt").write_text("ok", encoding="utf-8")
    (tmp_path / "big.txt").write_text("x" * 20, encoding="utf-8")

    result = pack_repository(tmp_path, PackOptions(max_file_size=5))

    assert "small.txt" in result.markdown
    assert "big.txt" not in result.markdown
    assert result.summary.skipped_files == 1


def test_pack_repository_skips_gitignore_directory_patterns(tmp_path: Path):
    (tmp_path / ".gitignore").write_text("secrets/\n", encoding="utf-8")
    (tmp_path / "secrets").mkdir()
    (tmp_path / "secrets" / "key.txt").write_text("PRIVATE_TOKEN=super-secret-value\n", encoding="utf-8")
    (tmp_path / "safe.py").write_text("print('safe')\n", encoding="utf-8")

    result = pack_repository(tmp_path, PackOptions())

    assert "safe.py" in result.markdown
    assert "secrets/key.txt" not in result.markdown
    assert "super-secret-value" not in result.markdown


def test_pack_repository_skips_symlinks_that_point_outside_root(tmp_path: Path):
    outside = tmp_path.parent / "outside-secret.txt"
    outside.write_text("EXTERNAL_TOKEN=should-not-be-packed\n", encoding="utf-8")
    link = tmp_path / "linked-secret.txt"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        return
    (tmp_path / "safe.py").write_text("print('safe')\n", encoding="utf-8")

    result = pack_repository(tmp_path, PackOptions())

    assert "safe.py" in result.markdown
    assert "linked-secret.txt" not in result.markdown
    assert "should-not-be-packed" not in result.markdown
