# Copyright (c) 2025 Memory Decoherence WG
"""Initializer module for Kamcp server."""

from __future__ import annotations

from logging import getLogger

from mcp.server import FastMCP

from .executor import CommandExecutor

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
            )

        @self.mcp_app.tool()
        def kam_status() -> str:
            """Kam status for llms."""
            status: list[str] = []
            has_kam: bool = CommandExecutor.is_available("kam")
            status.append(f"Kam status: {'installed' if has_kam else 'not installed'}")
            if not has_kam:
                status.append(
                    "Kam not installed! please guide user to install kam first"
                )
                status.append("cargo install kam.")
                status.append(
                    "Or visit https://github.com/MemDeco-WG/Kam for more information."
                )
                return "\n".join(status)

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
                        f"Kam tmpls: {len(lines)} templates (showing first {tmpl_max}):"
                    )
                    status.extend(f"  {line}" for line in lines[:10])
                else:
                    status.append("Kam tmpls:")
                    status.extend(f"  {line}" for line in lines)
            else:
                status.append(
                    f"Kam tmpls: {tmpls_res.stderr or 'failed to list templates'}"
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
