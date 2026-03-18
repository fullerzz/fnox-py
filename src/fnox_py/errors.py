from __future__ import annotations


class FnoxError(Exception):
    """Base exception for fnox-py."""


class FnoxNotFoundError(FnoxError, FileNotFoundError):
    """The fnox binary could not be found."""


class FnoxCommandError(FnoxError):
    """fnox exited with a non-zero return code."""

    def __init__(self, returncode: int, stdout: str, stderr: str, cmd: list[str]) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.cmd = cmd
        super().__init__(f"fnox failed with exit code {returncode}: {stderr.strip() or stdout.strip()}")


class FnoxTimeoutError(FnoxError):
    """fnox subprocess timed out."""
