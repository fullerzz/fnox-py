from fnox_py.errors import FnoxCommandError, FnoxError, FnoxNotFoundError, FnoxTimeoutError


def test_inheritance_hierarchy() -> None:
    assert issubclass(FnoxNotFoundError, FnoxError)
    assert issubclass(FnoxNotFoundError, FileNotFoundError)
    assert issubclass(FnoxCommandError, FnoxError)
    assert issubclass(FnoxTimeoutError, FnoxError)


def test_command_error_attributes() -> None:
    err = FnoxCommandError(1, "out", "err msg", ["fnox", "get", "KEY"])
    assert err.returncode == 1
    assert err.stdout == "out"
    assert err.stderr == "err msg"
    assert err.cmd == ["fnox", "get", "KEY"]
    assert "exit code 1" in str(err)
    assert "err msg" in str(err)


def test_command_error_falls_back_to_stdout() -> None:
    err = FnoxCommandError(2, "stdout fallback", "", ["fnox"])
    assert "stdout fallback" in str(err)
