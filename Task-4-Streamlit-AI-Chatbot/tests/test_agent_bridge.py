import sys

from chatbot.agent_bridge import load_agent_runner, normalize_agent_output
from chatbot.config import load_config


def _cfg(tmp_path, **extra):
    env = {"GOOGLE_API_KEY": "k" * 12, "ENABLE_TASK3_AGENT": "true", "TASK3_AGENT_DIR": str(tmp_path)}
    env.update(extra)
    return load_config(env=env)


def _isolate_imports(monkeypatch):
    """Let pytest undo the sys.path change the bridge makes (module names are unique per test)."""
    monkeypatch.setattr(sys, "path", list(sys.path))


def test_disabled_by_default():
    status = load_agent_runner(load_config(env={"GOOGLE_API_KEY": "k" * 12}))
    assert not status.available and "turned off" in status.reason and status.runner is None


def test_missing_folder_does_not_crash(tmp_path):
    status = load_agent_runner(_cfg(tmp_path / "does-not-exist"))
    assert not status.available and "not found" in status.reason


def test_missing_module(tmp_path):
    status = load_agent_runner(_cfg(tmp_path, TASK3_AGENT_MODULE="nothing_here"))
    assert not status.available and "nothing_here" in status.reason


def test_invalid_names_are_rejected(tmp_path):
    for bad in ("os; import sys", "../evil", "a b"):
        status = load_agent_runner(_cfg(tmp_path, TASK3_AGENT_MODULE=bad))
        assert not status.available and "valid Python names" in status.reason


def test_working_agent_is_loaded_and_called(tmp_path, monkeypatch):
    _isolate_imports(monkeypatch)
    (tmp_path / "fake_t3_ok.py").write_text("def run_agent(q):\n    return 'answer: ' + q\n")
    status = load_agent_runner(_cfg(tmp_path, TASK3_AGENT_MODULE="fake_t3_ok"))
    assert status.available and status.runner("hi") == "answer: hi"


def test_dict_output_is_unwrapped(tmp_path, monkeypatch):
    _isolate_imports(monkeypatch)
    (tmp_path / "fake_t3_dict.py").write_text("def run_agent(q):\n    return {'output': 'done'}\n")
    status = load_agent_runner(_cfg(tmp_path, TASK3_AGENT_MODULE="fake_t3_dict"))
    assert status.runner("x") == "done"


def test_missing_function(tmp_path, monkeypatch):
    _isolate_imports(monkeypatch)
    (tmp_path / "fake_t3_nofunc.py").write_text("x = 1\n")
    status = load_agent_runner(_cfg(tmp_path, TASK3_AGENT_MODULE="fake_t3_nofunc"))
    assert not status.available and "no function" in status.reason


def test_import_error_inside_task3_is_contained(tmp_path, monkeypatch):
    _isolate_imports(monkeypatch)
    (tmp_path / "fake_t3_broken.py").write_text("import module_that_does_not_exist_xyz\n")
    status = load_agent_runner(_cfg(tmp_path, TASK3_AGENT_MODULE="fake_t3_broken"))
    assert not status.available and "Could not import" in status.reason


def test_sys_exit_inside_task3_is_contained(tmp_path, monkeypatch):
    _isolate_imports(monkeypatch)
    (tmp_path / "fake_t3_exit.py").write_text("raise SystemExit('bye')\n")
    status = load_agent_runner(_cfg(tmp_path, TASK3_AGENT_MODULE="fake_t3_exit"))
    assert not status.available


def test_normalize_agent_output():
    assert normalize_agent_output("text") == "text"
    assert normalize_agent_output({"output": "o"}) == "o"
    assert normalize_agent_output(42) == "42"
