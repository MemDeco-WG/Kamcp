# Copyright (c) 2025 Memory Decoherence WG
"""Initializer module for Kamcp server."""

from __future__ import annotations

import json
import threading
from logging import getLogger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

logger = getLogger("kamcp.server")

# Termux-related constants used to build adb commands. These constants help
# construct the remote invocation for both one-shot and interactive modes.
# Keep them near the top so any future change to the invocation is done in
# one place.
TERMUX_DATA_DIR = "/data/data/com.termux/files"
TERMUX_ENV_REL = "usr/etc/termux/termux.env"
TERMUX_LOGIN_REL = "usr/bin/login"
TERMUX_SH_REL = "usr/bin/sh"
# Legacy adb-shell templates and convenience wrappers removed.
# One-shot / interactive invocations should use SSH over an adb port-forward
# instead of raw adb-shell + su-based pipelines.


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

        # Background daemon/session management (adb-shell-based) has been removed.
        # Termux interactions should now be performed via SSH (start sshd on the device
        # and use adb forward + ssh to connect).

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
        def init_basic_tools() -> str:
            """Lazy-register basic tools (kam_exec, kam_tips, kam_status).

            Returns:
                A JSON-encoded string indicating success or failure. On success
                the returned JSON contains ``{"ok": True, ...}``.

            """
            try:
                # Lazy import so heavy registration logic is only loaded when the
                # initialization command is invoked.
                from .tools.basic import register_basic_tools  # noqa: PLC0415

                register_basic_tools(self.mcp_app)
                return json.dumps({"ok": True, "message": "basic tools registered"})
            except Exception as e:
                logger.exception("Failed to register basic tools")
                return json.dumps({"ok": False, "error": str(e)})

        @self.mcp_app.tool()
        def init_termux_tools() -> str:
            """Lazy-register Termux tools (one-shot/daemon/session).

            Import and register the Termux tool group from
            ``kamcp.server.tools.termux``. This keeps the heavy termux
            initialization out of the module import path and supports
            on-demand (lazy) registration.

            Returns:
                A JSON-encoded string indicating success or failure.

            """
            try:
                # Delayed import: keep heavy termux initialization out of the module
                # import path so it is loaded only when requested.
                from .tools import termux as termux_tools  # noqa: PLC0415

                termux_tools.register_termux_tools(self.mcp_app, self)
                return json.dumps({"ok": True, "message": "termux tools registered"})
            except Exception as e:
                logger.exception("Failed to register termux tools")
                return json.dumps({"ok": False, "error": str(e)})
