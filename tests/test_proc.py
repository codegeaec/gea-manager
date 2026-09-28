from gea import proc


def test_run_captures_output():
    out, err, code = proc.run(["python3", "-c", "print('hi')"])
    assert out.strip() == "hi"
    assert code == 0


def test_run_returns_1_on_missing_binary():
    out, err, code = proc.run(["this-binary-does-not-exist-xyz"])
    assert (out, err, code) == ("", "", 1)


def test_run_visible_returns_exit_code():
    assert proc.run_visible(["python3", "-c", "exit(0)"]) == 0
    assert proc.run_visible(["python3", "-c", "exit(3)"]) == 3


def test_run_visible_returns_1_on_missing_binary():
    assert proc.run_visible(["this-binary-does-not-exist-xyz"]) == 1
