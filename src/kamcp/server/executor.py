# Copyright (c) 2025 Memory Decoherence WG
"""Command executor helper for running external commands like the `kam` CLI.

This module provides a small, well-typed wrapper around `subprocess.run`
to standardize how we invoke the `kam` binary (and other commands) across
the codebase, while avoiding shell injection and returning a structured
result.

Example:
    >>> from kamcp.server.command_executor import CommandExecutor
    >>> CommandExecutor.is_available("kam")
    True
    >>> res = CommandExecutor.run_kam("--version")
    >>> print(res.formatted())
    stdout: kam x.y.z
    stderr:

"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from logging import getLogger
from multiprocessing import Lock

logger = getLogger("kamcp.server")


@dataclass(frozen=True)
class CommandResult:
    """Result of running a command."""

    stdout: str
    stderr: str
    returncode: int

    def is_success(self) -> bool:
        """Return True if the command exited with return code 0."""
        return self.returncode == 0

    def formatted(self) -> str:
        """Return a compact, human-readable representation similar to the old tool.

        This matches the previous `kam_exec` tool output format used in the
        project ("stdout: ...\nstderr: ...").
        """
        return f"stdout: {self.stdout}\nstderr: {self.stderr}"


class CommandExecutor:
    """Utility class for executing external commands in a safe and testable way."""

    @classmethod
    def is_available(cls, executable: str = "kam") -> bool:
        """Return True if `executable` is discoverable in PATH.

        Uses `shutil.which` which is portable and avoids relying on shell
        builtins like `command -v`.
        """
        available = shutil.which(executable) is not None
        logger.debug("Checking availability of %s: %s", executable, available)
        return available

    @classmethod
    def _normalize_args(cls, cmd: str | Iterable[str]) -> list[str]:
        """Normalize a command given as a string or iterable into an args list.

        If `cmd` is a string it will be split with `shlex.split` to avoid
        shell interpretation and potential injection issues.
        """
        if isinstance(cmd, str):
            return shlex.split(cmd)
        return list(cmd)

    @classmethod
    def run(
        cls,
        cmd: str | Iterable[str],
        *,
        executable: str | None = None,
        capture_output: bool = True,
        check: bool = False,
        timeout: float | None = None,
    ) -> CommandResult:
        """Run the command and return a CommandResult.

        Args:
            cmd: Command to run. If a string, will be split via `shlex.split`.
            executable: If provided, it will be prepended to the args (useful for
                running `kam` with `cmd` being its arguments).
            capture_output: Whether to capture stdout/stderr (default True).
            check: If True, raise CalledProcessError on non-zero exit. When False,
                a CommandResult with the return code will be returned instead.
            timeout: Optional timeout in seconds.

        The function always avoids using a shell, constructing an argv list and
        invoking the command directly.
        """
        args = cls._normalize_args(cmd)
        if executable:
            args = [executable, *args]

        logger.debug("Executing command: %s", args)
        try:
            completed = subprocess.run(
                args,
                capture_output=capture_output,
                text=True,
                check=check,
                timeout=timeout,
            )

            def _to_str(value: object) -> str:
                if isinstance(value, bytes):
                    return value.decode(errors="replace").strip()
                return str(value or "").strip()

            stdout = _to_str(completed.stdout)
            stderr = _to_str(completed.stderr)
            logger.debug("Command finished: %s (rc=%s)", args, completed.returncode)
            return CommandResult(
                stdout=stdout, stderr=stderr, returncode=completed.returncode
            )
        except subprocess.CalledProcessError as exc:
            # CalledProcessError provides stdout/stderr when `check=True` caused this.
            stdout = str(getattr(exc, "stdout", ""))
            stderr = str(getattr(exc, "stderr", str(exc)))
            logger.debug(
                "Command failed (CalledProcessError): %s (rc=%s)", args, exc.returncode
            )
            return CommandResult(
                stdout=stdout, stderr=stderr, returncode=exc.returncode
            )
        except subprocess.TimeoutExpired as exc:
            stdout = str(getattr(exc, "stdout", ""))
            stderr = str(getattr(exc, "stderr", str(exc)))
            logger.debug("Command timed out: %s", args)
            return CommandResult(stdout=stdout, stderr=stderr, returncode=1)
        except Exception as exc:  # pragma: no cover - defensive
            # Any unexpected exception should not crash the caller; return a non-zero result.
            logger.exception(
                "Unexpected error while executing command %s: %s", args, exc
            )
            return CommandResult(stdout="", stderr=str(exc), returncode=1)

    @classmethod
    def run_kam(
        cls,
        kam_command: str,
        *,
        capture_output: bool = True,
        check: bool = False,
        timeout: float | None = None,
    ) -> CommandResult:
        """Convenience wrapper for running `kam` with the given arguments string."""
        return cls.run(
            kam_command,
            executable="kam",
            capture_output=capture_output,
            check=check,
            timeout=timeout,
        )


__all__ = ["CommandExecutor", "CommandResult"]
