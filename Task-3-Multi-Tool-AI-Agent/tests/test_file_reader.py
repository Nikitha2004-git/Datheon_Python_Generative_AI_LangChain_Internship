import os

import pytest

from agent.tools.file_reader import (FileReadError, list_permitted_files, read_file,
                                     read_file_content, resolve_safe_path)


def test_reads_txt_md_json(workspace):
    assert read_file_content("notes.txt", workspace) == "hello notes"
    assert read_file_content("readme.md", workspace).startswith("# Title")
    assert '"a": 1' in read_file_content("data.json", workspace)  # pretty-printed


def test_reads_subfolder_file(workspace):
    assert read_file_content("sub/inner.txt", workspace) == "inner"


def test_tool_output_wraps_untrusted_label(workspace):
    out = read_file("notes.txt", workspace)
    assert "untrusted data" in out and "hello notes" in out


def test_missing_file(workspace):
    with pytest.raises(FileReadError, match="not found"):
        read_file_content("nope.txt", workspace)
    assert read_file("nope.txt", workspace).startswith("File reader error")


@pytest.mark.parametrize("name", ["script.py", "notes.exe", "notes", "image.png"])
def test_unsupported_extension(workspace, name):
    with pytest.raises(FileReadError):
        read_file_content(name, workspace)


@pytest.mark.parametrize("name", [
    "../outside.txt", "../../etc/passwd", "sub/../../outside.txt", "..\\outside.txt",
    "/etc/passwd", "C:\\Windows\\win.ini", "sub/../../ws/../outside.txt",
])
def test_path_traversal_blocked(workspace, name):
    out = read_file(name, workspace)
    assert out.startswith("File reader error")
    assert "outside secret" not in out


def test_absolute_path_inside_workspace_still_blocked(workspace):
    out = read_file(str(workspace / "notes.txt"), workspace)
    assert out.startswith("File reader error")


@pytest.mark.parametrize("name", [".env", ".env.local", "api_key.txt", "sub/.hidden.txt",
                                  "my_secret.txt", "credentials.json", "token.md"])
def test_sensitive_files_blocked(workspace, name):
    out = read_file(name, workspace)
    assert out.startswith("File reader error")
    assert "SECRET123" not in out


def test_symlink_escape_blocked(workspace, tmp_path):
    link = workspace / "link.txt"
    try:
        os.symlink(tmp_path / "outside.txt", link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this system")
    out = read_file("link.txt", workspace)
    assert out.startswith("File reader error") and "outside secret" not in out


def test_size_limit(workspace):
    (workspace / "big.txt").write_text("x" * 2000, encoding="utf-8")
    with pytest.raises(FileReadError, match="too large"):
        read_file_content("big.txt", workspace, max_bytes=1000)
    assert read_file_content("big.txt", workspace, max_bytes=5000) == "x" * 2000


def test_encoding_error(workspace):
    (workspace / "bad.txt").write_bytes(b"\xff\xfe\x00bad\x80")
    with pytest.raises(FileReadError, match="UTF-8"):
        read_file_content("bad.txt", workspace)


def test_malformed_json_returned_raw(workspace):
    (workspace / "broken.json").write_text("{not json", encoding="utf-8")
    assert read_file_content("broken.json", workspace) == "{not json"


def test_directory_is_not_a_file(workspace):
    (workspace / "folder.txt").mkdir()
    with pytest.raises(FileReadError):
        read_file_content("folder.txt", workspace)


@pytest.mark.parametrize("name", ["", "   ", None])
def test_empty_name(workspace, name):
    assert read_file(name, workspace).startswith("File reader error")


def test_listing_excludes_sensitive(workspace):
    files = list_permitted_files(workspace)
    assert "notes.txt" in files and "sub/inner.txt" in files
    assert ".env" not in files and "api_key.txt" not in files and "script.py" not in files
    assert "notes.txt" in read_file(".", workspace)


def test_reader_never_modifies_files(workspace):
    before = (workspace / "notes.txt").read_bytes()
    read_file("notes.txt", workspace)
    assert (workspace / "notes.txt").read_bytes() == before


def test_resolve_safe_path_null_byte(workspace):
    with pytest.raises(FileReadError):
        resolve_safe_path("notes.txt\x00.png", workspace)
