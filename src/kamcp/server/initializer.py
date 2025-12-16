# Copyright (c) 2025 Memory Decoherence WG
"""Initializer module for Kamcp server."""

from __future__ import annotations

import shlex
import subprocess
from logging import getLogger

from mcp.server import FastMCP

logger = getLogger("kamcp.server")


class Initializer:
    """Initialize Kamcp with the given FastMCP application."""

    initialized: bool = False
    instance: Initializer | None = None

    def __init__(self, mcp_app: FastMCP) -> None:
        """Initialize Kamcp with the given FastMCP application."""
        self.mcp_app = mcp_app

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
            # Use an argument list (no shell) and shlex.split to avoid shell injection.
            logger.debug("Executing kam command: %s", kam_command)
            args = ["kam", *shlex.split(kam_command)]
            try:
                result = subprocess.run(
                    args, capture_output=True, text=True, check=True
                )
                stdout = result.stdout.strip()
                stderr = result.stderr.strip()
            except subprocess.CalledProcessError as exc:
                stdout = (exc.stdout or "").strip()
                stderr = (exc.stderr or str(exc)).strip()
                logger.debug("kam command failed: %s", exc)
            return f"stdout: {stdout}\nstderr: {stderr}"

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
            )
