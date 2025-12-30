# Copyright (c) 2025 Memory Decoherence WG
"""Basic MCP tools (lazy registration).

Provides `register_basic_tools(mcp_app)` which registers several common
tools (kam_exec, kam_tips, kam_status). The tools are registered lazily
to avoid heavy imports at module import time.
"""

from __future__ import annotations

from logging import getLogger
from typing import Any, Protocol, Callable, TypeVar

from kamcp.server.executor import CommandExecutor

logger = getLogger("kamcp.server.tools.basic")

def _kam_exec_run(kam_command: str) -> str:
    """Run `kam` with given arguments and return the formatted result.

    This helper centralizes the actual invocation and formatting so the
    registered tool remains a small wrapper.
    """
    logger.debug("Executing kam command: %s", kam_command)
    result = CommandExecutor.run_kam(kam_command)
    return result.formatted()


# Protocol describing the minimal interface we expect from the MCP app
# object (an object exposing a `.tool()` decorator).
R = TypeVar("R")
class MCPAppProtocol(Protocol):
    def tool(self) -> Callable[[Callable[..., R]], Callable[..., R]]:
        ...


def _build_kam_status() -> str:
    """Collect and return the kam status as a single string.

    Returns:
        A string containing multiple status lines joined by newlines.
    """
    status: list[str] = []
    has_kam: bool = CommandExecutor.is_available("kam")
    status.append(f"Kam status: {'installed' if has_kam else 'not installed'}")
    if not has_kam:
        # Return a single helpful message if kam is not available.
        status.append(
            "Kam not installed! please guide user to install kam first "
            "(`cargo install kam`). Visit https://github.com/MemDeco-WG/Kam "
            "for more information.",
        )
        return "\n".join(status)


    def kam_exec(kam_command: str) -> str:
        """Execute a kam command and return its formatted capture.

        Returns:
            A formatted string with stdout and stderr from running the command.
        """
        return _kam_exec_run(kam_command)





    def kam_status() -> str:
        """Kam status for llms.

        Returns:
            A multi-line status string.
        """
        return _build_kam_status()

    # Termux tools are registered separately so they appear as top-level MCP tools.

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
            status.extend(f"  {line}" for line in lines[:tmpl_max])
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
        status.extend(
            [
                f"check result: stdout:/n{check_res.stdout}",
                f"check result: stderr:/n{check_res.stderr}",
            ]
        )
    else:
        status.append(f"Kam check: {check_res.stderr or 'failed'}")

    return "\n".join(status)


def register_basic_tools(mcp_app: MCPAppProtocol) -> None:
    """Register basic MCP tools on the provided mcp_app.

    Args:
        mcp_app: MCP app object which exposes a `.tool()` decorator for
                 registering tools.

    """

    # Register the tools on the provided MCP app using the decorators it
    # supplies. Keep the helper minimal to limit the complexity of this
    # registration function.
    tool_decorator = mcp_app.tool()
    tool_decorator(kam_exec)
    tool_decorator(kam_tips)
    tool_decorator(kam_status)

def _kam_tips_text() -> str:
    """Return the kam CLI tips text as a single string."""
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
        '  - `kam_exec(\"--help\")` -> show `kam` help\n'
        '  - `kam_exec(\"--version\")` -> show `kam` version\n'
        '  - `kam_exec(\"tmpl list\")` -> list templates\n'
        '  - `kam_exec(\"init --help\")` -> show `init` help\n'
        '  - `kam_exec(\"config show\")` -> show configuration\n'
        '  - `kam_exec(\"config --global set ui.language zh\")` -> set language\n'
        '  - `kam_exec(\"secret --help\")` -> show secret help\n'
        '  - `kam_exec(\"build --help\")` -> show build help\n'
        '  - `kam_exec(\"check --json\")` -> show check result\n'
        "\n"
        "Security note\n"
        "  - `kam_exec` runs the `kam` binary directly (no shell) to avoid\n"
        "    shell injection risks.\n"
        "\n"
        "Useful guides\n"
        '  - `kam_exec(\"-Ss <keyword>\")` -> Search the modules\n'
        "    registry for <keyword>\n"
        '  - `kam_exec(\"-S <moduleId>\")` -> Download the specified module\n'
        "  - Then extract the downloaded module archive and inspect its\n"
        "    contents to learn from it.\n"
        "  - KernelSU Module guide: https://kernelsu.org/guide/module.html\n"
        "  - Apatch Module guide: https://apatch.dev/apm-guide.html\n"
        "  - Magisk Module develop guide: https://topjohnwu.github.io/Magisk/guides.html\n"  # noqa: E501
        "\n"
    )


    @mcp_app.tool()
    def kam_tips() -> str:
        \"\"\"Get kam CLI tips.

        Returns:
            A multi-line string with tips and examples.
        \"\"\"
        return _kam_tips_text()
