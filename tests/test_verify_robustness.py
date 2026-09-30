"""verify must never look hung, never leave orphans, and never pile up.
These use real (short) subprocesses: the bugs were about real process trees."""

import os
import signal
import subprocess
import sys
import textwrap
import threading
import time

from gea import proc, verify


def _alive(marker: str) -> bool:
    return subprocess.run(["pgrep", "-f", marker], capture_output=True).returncode == 0


def _wait_gone(marker: str, seconds: float = 15.0) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        if not _alive(marker):
            return True
        time.sleep(0.1)
    return False


def test_streaming_reports_a_heartbeat_and_returns_output():
    ticks = []
    out, err, code = proc.run_streaming(
        ["sh", "-c", "sleep 1.3; echo done"], timeout=30, on_tick=ticks.append, tick_every=0.5
    )
    assert (out.strip(), code) == ("done", 0) and len(ticks) >= 2


def test_timeout_kills_the_whole_process_group_not_just_the_shell():
    marker = "sleep 61.4711"
    out, err, code = proc.run_streaming(["sh", "-c", f"{marker} & wait"], timeout=1, tick_every=0.5)
    assert code == 124 and "timed out" in err
    assert _wait_gone(marker), "grandchild left running"


def test_missing_binary_is_a_127_not_a_traceback():
    assert proc.run_streaming(["definitely-not-a-binary-xyz"])[2] == 127


def test_interrupting_verify_exits_130_with_a_message_and_leaves_no_orphans(tmp_path):
    marker = "sleep 62.3391"
    (tmp_path / "gea.json").write_text(f'{{"verify": ["{marker} & wait"]}}')
    script = textwrap.dedent(
        f"""
        import sys
        from pathlib import Path
        from gea import verify
        sys.exit(verify.run_verify(Path({str(tmp_path)!r}), quiet=True))
        """
    )
    child = subprocess.Popen(
        [sys.executable, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, env={**os.environ, "GEA_LANG": "en"},
    )
    end = time.time() + 30
    while time.time() < end and not _alive(marker):
        time.sleep(0.1)
    assert _alive(marker)
    child.send_signal(signal.SIGINT)
    out, err = child.communicate(timeout=15)
    assert child.returncode == 130
    assert "interrupted (130)" in out and marker in out and "Traceback" not in err
    assert "→ " in err  # it announced the command it was running
    assert _wait_gone(marker), "verify left the command tree running"


def test_sigterm_is_handled_like_an_interrupt(tmp_path):
    marker = "sleep 63.5521"
    (tmp_path / "gea.json").write_text(f'{{"verify": ["{marker} & wait"]}}')
    script = (
        f"import sys\nfrom pathlib import Path\nfrom gea import verify\n"
        f"sys.exit(verify.run_verify(Path({str(tmp_path)!r})))\n"
    )
    child = subprocess.Popen([sys.executable, "-c", script], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True)
    end = time.time() + 30
    while time.time() < end and not _alive(marker):
        time.sleep(0.1)
    assert _alive(marker)
    child.send_signal(signal.SIGTERM)
    child.communicate(timeout=15)
    assert child.returncode == 130 and _wait_gone(marker)


def test_quiet_mode_still_prints_progress_to_stderr(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(verify, "HEARTBEAT_SECONDS", 0.4)
    (tmp_path / "gea.json").write_text('{"verify": ["sleep 1.2"]}')
    assert verify.run_verify(tmp_path, quiet=True) == 0
    captured = capsys.readouterr()
    assert "→ sleep 1.2" in captured.err and "… sleep 1.2 (" in captured.err
    assert "sleep 1.2" not in captured.out.replace("verify command", "")  # nothing else on stdout


def test_progress_can_be_turned_off_for_the_orchestrators_own_run(tmp_path, capsys):
    (tmp_path / "gea.json").write_text('{"verify": ["true"]}')
    verify.run_verify(tmp_path, quiet=True, progress=False)
    assert capsys.readouterr().err == ""


def test_the_last_duration_is_remembered_and_shown_next_time(tmp_path, capsys):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "gea.json").write_text('{"verify": ["sleep 1.1"]}')
    verify.run_verify(tmp_path, quiet=True)
    capsys.readouterr()
    verify.run_verify(tmp_path, quiet=True)
    assert "last time: 1s" in capsys.readouterr().err


def test_two_verifies_of_one_repo_run_one_after_the_other(tmp_path, capsys):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    state_dir = verify._state_dir(tmp_path)
    order = []

    def hold(name, seconds):
        with verify._one_at_a_time(state_dir, progress=True):
            order.append(f"{name}-start")
            time.sleep(seconds)
            order.append(f"{name}-end")

    first = threading.Thread(target=hold, args=("a", 0.8))
    first.start()
    time.sleep(0.2)
    second = threading.Thread(target=hold, args=("b", 0.1))
    second.start()
    first.join()
    second.join()
    assert order == ["a-start", "a-end", "b-start", "b-end"]
    assert "another verify is running" in capsys.readouterr().err
