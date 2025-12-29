# Copyright (c) 2025 Memory Decoherence WG
"""Initializer module for Kamcp server."""

from __future__ import annotations

import base64
import contextlib
import os
import pathlib
import pty
import select
import subprocess
import threading
import uuid
from logging import getLogger
from typing import TYPE_CHECKING

from .executor import CommandExecutor
from .utils import is_android_host

if TYPE_CHECKING:
    from mcp.server import FastMCP

logger = getLogger("kamcp.server")

# Termux constants used to build remote adb commands for both one-shot and interactive modes.
# Keep them near the top so any future change to the invocation is done in one place.
TERMUX_DATA_DIR = "/data/data/com.termux/files"
TERMUX_ENV_REL = "usr/etc/termux/termux.env"
TERMUX_LOGIN_REL = "usr/bin/login"
TERMUX_SH_REL = "usr/bin/sh"
# One-shot template (inner command without the outer `su -c` wrapper).
TERMUX_ONESHOT_INNER = 'D={}; U=$(stat -c %u $D/home)\
; echo {} \
| base64 -d \
| exec su $U -c "cd $D/home && . $D/{}\
; exec $D/{} -l -s"'
# Interactive login template (inner command).
TERMUX_LOGIN_INNER = (
    'D={}; U=$(stat -c %u $D/home); exec su $U -c "cd $D/home && . $D/{}; exec $D/{}"'
)
# Convenience wrappers for adb usage (outer `su -c '...'`)
# to keep backwards-compatible shapes.
TERMUX_ONESHOT_FMT = f"su -c '{TERMUX_ONESHOT_INNER}'"
TERMUX_LOGIN_FMT = f"su -c '{TERMUX_LOGIN_INNER}'"


# `is_android_host` helper moved to kamcp.server.utils
# to avoid duplicated ad-hoc helpers.
# Use `from .utils import is_android_host` to access the shared implementation.


class Initializer:
    """Initialize Kamcp with the given FastMCP application."""

    initialized: bool = False
    instance: Initializer | None = None

    def __init__(self, mcp_app: FastMCP) -> None:
        """Initialize Kamcp with the given FastMCP application."""
        self.mcp_app = mcp_app

        # Termux session management for MCP:
        # sessions: mapping session_id -> {"proc": Popen, "fd": master_fd, "device": str| None}
        self._termux_sessions: dict[str, dict] = {}
        self._termux_lock = threading.Lock()

    @classmethod
    def from_app(cls, mcp_app: FastMCP) -> Initializer | None:
        """Initialize Kamcp with the given FastMCP application.

        Returns:
            Initializer | None: The initialized Kamcp instance or None.

        """
        if not Initializer.initialized:
            instance: Initializer = cls(mcp_app)
            Initializer.instance = instance
            Initializer.initialized = True
            return instance
        logger.warning("Kamcp is already initialized")
        return Initializer.instance

    def init_tools(self) -> None:
        """Initialize tools for Kamcp."""

        @self.mcp_app.tool()
        def kam_exec(kam_command: str) -> str:
            """Execute a kam command.

            Args:
                kam_command (str): The command string to pass to the `kam` CLI
                    (for example: '--help', 'init --help', 'tmpl list').

            Returns:
                str: A multi-line string prefixed with 'stdout:' and 'stderr:'
                    that contains the captured standard output and standard error.

            """
            logger.debug("Executing kam command: %s", kam_command)
            result = CommandExecutor.run_kam(kam_command)
            return result.formatted()

        @self.mcp_app.tool()
        def kam_tips() -> str:
            """Get kam CLI tips.

            Returns:
                str: A multi-line string with usage tips.

            """
            return (
                "kam CLI tips\n"
                "\n"
                "Install\n"
                "  - Using Rust/Cargo: `cargo install kam`\n"
                "\n"
                "Basic usage\n"
                "  - `kam --help` or `kam <subcommand> --help` to get help\n"
                "  - `kam --version` or `kam version` to show version\n"
                "\n"
                "Examples using `kam_exec` tool\n"
                '  - `kam_exec("--help")` -> show `kam` help\n'
                '  - `kam_exec("--version")` -> show `kam` version\n'
                '  - `kam_exec("tmpl list")` -> list templates\n'
                '  - `kam_exec("init --help")` -> show `init` help\n'
                '  - `kam_exec("config show")` -> show configuration\n'
                '  - `kam_exec("config --global set ui.language zh")` -> set language\n'
                '  - `kam_exec("secret --help")` -> show secret help\n'
                '  - `kam_exec("build --help")` -> show build help\n'
                '  - `kam_exec("check --json")` -> show check result\n'
                "\n"
                "Security note\n"
                "  - `kam_exec` runs the `kam` binary directly (no shell) and uses\n"
                "     to avoid shell injection\n"
                "\n"
                "Useful guides\n"
                '  - `kam_exec("-Ss <keyword>")` -> Search the modules registry for <keyword>\n'
                '  - `kam_exec("-S <moduleId>")` -> Download the specified module\n'
                "  - Then extract the downloaded module archive and inspect its contents to learn from it.\n"
                "  - KernelSU Module guide: https://kernelsu.org/guide/module.html\n"
                "  - Apatch Module guide: https://apatch.dev/apm-guide.html\n"
                "  - Magisk Module develop guide: https://topjohnwu.github.io/Magisk/guides.html\n"
                "\n"
                "Termux & adb (MCP integration)\n"
                "  - One-shot (execute a single command):\n"
                "      Use `kam_termux_exec(cmd, device=None)` to run a command inside Termux and return stdout/stderr.\n"
                '      Example: `kam_termux_exec("ls -la ~", device=None)`\n'
                "  - Interactive session (start/read/write/close):\n"
                "      Start a session with `sid = kam_termux_start(device=None)`.\n"
                '      Repeatedly call `kam_termux_read(sid)` to fetch buffered output and `kam_termux_write(sid, "line\\n")` to send input.\n'
                "      Close the session with `kam_termux_close(sid)` when done.\n"
                "  - Local usage (no MCP):\n"
                '      `kam termux -c "<cmd>"` runs a single command via adb and prints the result; `kam termux` opens an interactive Termux shell locally (requires adb and a connected device).\n'
                "      Example adb usage:\n"
                '        adb shell -t "su -c \'D=/data/data/com.termux/files; U=$(stat -c %u $D/home); exec su $U -c "cd $D/home && . $D/usr/etc/termux/termux.env; exec $D/usr/bin/login"\'"\n'
                "  - Notes & security: the server-side tools invoke `adb` on the host where the MCP server runs. Ensure proper access controls and that the MCP server is trusted before enabling remote Termux sessions.\n"
                "\n"
            )

        @self.mcp_app.tool()
        def kam_status() -> str:
            """Kam status for llms."""
            status: list[str] = []
            has_kam: bool = CommandExecutor.is_available("kam")
            status.append(f"Kam status: {'installed' if has_kam else 'not installed'}")
            if not has_kam:
                status.extend(
                    (
                        "Kam not installed! please guide user to install kam first",
                        "cargo install kam.",
                        "Or visit https://github.com/MemDeco-WG/Kam for more information.",
                    )
                )
                return "\n".join(status)

            # Termux tools moved outside kam_status scope (defined below) so they are available
            # as top-level MCP tools within init_tools().

            # Get kam version
            version_res = CommandExecutor.run_kam("--version")
            if version_res.stdout:
                status.append(f"Kam version: {version_res.stdout}")
            elif version_res.stderr:
                status.append(f"Kam version (error): {version_res.stderr}")
            else:
                status.append("Kam version: unknown")

            # Get templates
            tmpls_res = CommandExecutor.run_kam("tmpl list")
            if tmpls_res.is_success() and tmpls_res.stdout:
                lines = tmpls_res.stdout.splitlines()
                tmpl_max = 10
                if not lines:
                    status.append("Kam tmpls: (none)")
                elif len(lines) > tmpl_max:
                    status.append(
                        f"Kam tmpls: {len(lines)} templates (showing first {tmpl_max}):",
                    )
                    status.extend(f"  {line}" for line in lines[:10])
                else:
                    status.append("Kam tmpls:")
                    status.extend(f"  {line}" for line in lines)
            else:
                status.append(
                    f"Kam tmpls: {tmpls_res.stderr or 'failed to list templates'}",
                )

            # Try to gather project info (may not exist if not in a project)
            proj_res = CommandExecutor.run_kam("tmpl list")
            if proj_res.is_success() and proj_res.stdout:
                status.append("Kam project info:")
                status.extend(f"  {line}" for line in proj_res.stdout.splitlines())
            else:
                status.append(f"Kam project info: {proj_res.stderr or 'not available'}")

            # Check result
            check_res = CommandExecutor.run_kam("check --json")
            if check_res.is_success():
                status.append(f"check result: stdout:/n{check_res.stdout}")
                status.extend(f"check result: stderr:/n{check_res.stderr}")
            else:
                status.append(f"Kam check: {check_res.stderr or 'failed'}")

            return "\n".join(status)

        # --- Termux integration tools for MCP (start/read/write/exec/close) ---
        @self.mcp_app.tool()
        def kam_termux_exec(
            cmd: str, device: str | None = None, timeout: int = 60
        ) -> str:
            """Execute a one-shot command inside Termux on a connected device via adb.

            This uses base64-encoding to safely transmit the user command to the device
            and then executes it via the user's Termux shell, avoiding complex host-side
            quoting issues.

            Args:
                cmd: The command to run inside Termux (single-line).
                device: Optional adb device id (passed to `adb -s ...`).
                timeout: Timeout in seconds for the command.

            Returns:
                str: A multi-line string prefixed with 'stdout:' and 'stderr:' containing the result.

            """
            logger.debug("kam_termux_exec: device=%s cmd=%s", device, cmd)
            # Base64-encode the command so it survives host shell quoting and is safe to decode on-device
            try:
                encoded = base64.b64encode(cmd.encode("utf-8")).decode("ascii")
            except Exception as e:
                logger.exception("Failed to base64-encode termux command: %s", e)
                return f"error: {e}"

            try:
                # If running on an Android host, execute the Termux invocation locally via `su -c`.
                if is_android_host():
                    cmd_inner = TERMUX_ONESHOT_INNER.format(
                        TERMUX_DATA_DIR,
                        encoded,
                        TERMUX_ENV_REL,
                        TERMUX_SH_REL,
                    )
                    res = subprocess.run(
                        ["su", "-c", cmd_inner],
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                    )
                    return f"stdout: {res.stdout}\nstderr: {res.stderr}"

                # Otherwise, fall back to using adb to run the command on a connected device.
                p = subprocess.run(
                    ["adb", "version"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if p.returncode != 0:
                    return f"error: adb not available: {p.stderr or p.stdout}"

                remote_inner = TERMUX_ONESHOT_INNER.format(
                    TERMUX_DATA_DIR,
                    encoded,
                    TERMUX_ENV_REL,
                    TERMUX_SH_REL,
                )
                remote = f"su -c '{remote_inner}'"

                adb_args = ["adb"]
                if device:
                    adb_args += ["-s", device]
                adb_args += ["shell", "-t", remote]

                res = subprocess.run(
                    adb_args,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                return f"stdout: {res.stdout}\nstderr: {res.stderr}"
            except subprocess.TimeoutExpired as e:
                return f"error: timeout: {e}"
            except Exception as e:  # pragma: no cover - defensive
                logger.exception("termux_exec failed: %s", e)
                return f"error: {e}"
