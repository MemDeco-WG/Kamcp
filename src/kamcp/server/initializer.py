# Copyright (c) 2025 Memory Decoherence WG
"""Initializer module for Kamcp server."""

from __future__ import annotations

import shlex
import subprocess
from logging import getLogger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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
                kam_command (str): The kam command to execute,
                    such as "--help".
                    equal to "kam --help".

            Returns:
                str: The output of the command.

            """
            # Use an argument list (no shell) and shlex.split to avoid shell injection.
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
            return f"stdout: {stdout}\nstderr: {stderr}"

        @self.mcp_app.tool()
        def kam_tips() -> str:
            """Get kam CLI tips.

            Returns:
                str: A multi-line string with usage tips.

            """
            return (
                "How to install Kam ? cargo install kam! "
                "what is kamcp ,kamcp is kam's mcp server, kamcp --help"
                "Tips: Use 'kam_exec' to execute a kam command.\n"
                "Tips: Use 'kam_exec(\"--help\")' to get help.\n"
                "Tips: Use 'kam_exec(\"--version")' to get kam version."
                "Tips: Use 'kam_exec(\"version\")' to get version.(project version.)\n"
                "Tips: Use 'Kam_exec(tmpl list)' to list all templates.\n"
                "Tips: Use 'Kam_exec(init --help)' to get init help.\n"
                "Tips: Use 'kam_exec(\"config show\")' some buildin configs.\n"
                "Tips: Use 'kam_exec(\"config --global set ui.language zh\", zh/en)' "
                "to set language.\n"
                "Tips: Use 'kam_exec(kam secret --help)' to get kam secret help"
                "(set secret_key).\n"
                "Tips: Use 'kam_exec(kam build --help)' to get kam build help.\n"
                "KernelSU Module develop guide: https://kernelsu.org/guide/module.html"
                "Apatch Module develop guide: https://apatch.dev/apm-guide.html"
                "Magisk Module develop guide: https://topjohnwu.github.io/Magisk/guides.html"
            )
