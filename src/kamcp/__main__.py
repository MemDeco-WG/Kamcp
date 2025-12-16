# Copyright (c) 2025 Memory Decoherence WG
"""CLI entry point for kamcp."""

from importlib.metadata import version as get_version
from logging import INFO, basicConfig, getLogger

from click import Context, group, pass_context
from mcp.server import FastMCP
from rich.logging import RichHandler

from kamcp.server import Initializer

basicConfig(level=INFO, handlers=[RichHandler()])
logger = getLogger("kamcp")


@group()
@pass_context
def kamcp(ctx: Context) -> None:
    """Kamcp Click command group."""
    kam_app = FastMCP("kam_use")
    ctx.obj = {}

    logger.info("Kamcp Loading . . .")
    initializer = Initializer.from_app(kam_app)
    if isinstance(initializer, Initializer):
        initializer.init_tools()
        kam_app = initializer.mcp_app
    else:
        kam_app = initializer
    ctx.obj["mcp_app"] = kam_app


@kamcp.command()
@pass_context
def stdio(ctx: Context) -> None:
    """Stdio."""
    kam_app: FastMCP = ctx.obj["mcp_app"]
    kam_app.run()


@kamcp.command()
@pass_context
def sse(ctx: Context) -> None:
    """Not recommended."""
    kam_app: FastMCP = ctx.obj["mcp_app"]
    kam_app.run(transport="sse")


@kamcp.command()
@pass_context
def http(ctx: Context) -> None:
    """streamable-http."""
    kam_app: FastMCP = ctx.obj["mcp_app"]
    kam_app.run(transport="streamable-http")


@kamcp.command()
def version() -> None:
    """Show version."""
    kamcp_version = get_version("kamcp")
    logger.info(kamcp_version)


if __name__ == "__main__":
    kamcp()
