# Termux tools registration (lazy-load)
# Provides `register_termux_tools(mcp_app, initializer)` which will register
# Termux-related MCP tools (one-shot exec, daemon management and interactive sessions)
# when invoked. The registration is intended to be lazy (import/register on demand).
from __future__ import annotations

import json
import os
import shlex
import subprocess
from logging import getLogger
from typing import Any

from kamcp.server.executor import CommandExecutor

logger = getLogger("kamcp.server.tools.termux")


def _parse_pid_from_text(s: str) -> int | None:
    import re

    if not s:
        return None
    m = re.search(r"\bpid\b[:\s]*([0-9]+)", s, re.IGNORECASE)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    # fallback to first reasonable integer
    m2 = re.search(r"(\d{2,})", s)
    if m2:
        try:
            return int(m2.group(1))
        except Exception:
            return None
    return None


def _parse_logs_from_text(s: str) -> str | None:
    import re

    if not s:
        return None
    m = re.search(r"Logs:\s*(.+)", s)
    if m:
        return m.group(1).strip()
    return None


def register_termux_tools(mcp_app: Any, initializer: Any) -> None:
    """Register Termux-related tools on the provided mcp_app.

    This registers a compact `termux` tool that supports executing commands
    inside Termux (one-shot execution via `command` / -c). The previous
    daemon/list/kill operations (background adb-shell sessions) have been
    removed in favor of a safer SSH-based workflow (see `--ssh-*` helpers).

    The implementation is intentionally conservative: it uses `adb` (via
    `CommandExecutor`) to set up port forwarding for SSH-based access when needed.
    """
    # Import the TERMUX constants lazily to avoid import-time cycles when
    # this module is imported by the initializer.
    from kamcp.server.initializer import (
        TERMUX_DATA_DIR,
        TERMUX_ENV_REL,
        TERMUX_LOGIN_REL,
        TERMUX_SH_REL,
    )

    def _adb_prefix(device: str | None) -> list[str]:
        return ["adb", "-s", device] if device else ["adb"]

    def _adb_shell_args(device: str | None, inner_cmd: str) -> list[str]:
        args = _adb_prefix(device) + ["shell", inner_cmd]
        return args

    def _ensure_adb_available() -> str | None:
        if not CommandExecutor.is_available("adb"):
            return json.dumps(
                {"ok": False, "error": "adb tool not available on server"},
            )
        return None

    @mcp_app.tool()
    def termux(
        device: str | None = None,
        command: str | None = None,
        timeout: int = 60,
    ) -> str:
        """Termux helper tool.

        Parameters mirror the CLI helper this server supports:
          - device: optional adb device id
          - command: one-shot command to execute inside Termux
          - daemon: start a persistent Termux session in background
          - list: list current daemon sessions
          - kill: kill daemon sessions (all, or filtered by device)
          - timeout: timeout in seconds for one-shot commands
        """
        # Check availability of adb early (fail-fast).
        missing = _ensure_adb_available()
        if missing:
            return missing

        # One-shot execution inside Termux.
        if command:
            # Construct a conservative invocation that:
            #  1) cd to Termux home
            #  2) try to source the termux env (if present)
            #  3) exec the Termux login shell to run the given command
            inner = (
                'su -c "cd {home} && . {env} 2>/dev/null || true && '
                'exec {sh} -l -c {cmd}"'.format(
                    home=TERMUX_DATA_DIR + "/home",
                    env=f"{TERMUX_DATA_DIR}/{TERMUX_ENV_REL}",
                    sh=f"{TERMUX_DATA_DIR}/{TERMUX_SH_REL}",
                    cmd=shlex.quote(command),
                )
            )
            adb_args = _adb_shell_args(device, inner)
            res = CommandExecutor.run(adb_args, timeout=timeout)
            return res.formatted()

        # (daemon/list/kill functionality removed)
        # The previous behavior that started a background adb-shell Termux session
        # has been removed in favor of an SSH-based workflow. Use `--ssh-setup`,
        # `--ssh-forward`, `--ssh-push-key`, `--ssh-connect` on the client side.

        # (list/kill functionality removed)
        # Previously the tool supported listing/killing background adb-based sessions;
        # that functionality has been removed. Use SSH-based workflows instead.

        # (kill functionality removed)
        # Background session management via adb-shell is no longer supported.

        # No action specified - return a helpful message.
        return json.dumps(
            {
                "ok": False,
                "error": "no action specified. Use 'command' or SSH-based workflow (see docs).",
            },
        )
