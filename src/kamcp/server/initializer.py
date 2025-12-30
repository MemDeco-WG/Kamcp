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
        def init_basic_tools() -> None:
            """加载kam基础工具."""
            ...

        @self.mcp_app.tool()
        def init_termux_tools() -> None:
            """延迟加载全部kam termux工具.

            执行本工具/你将获得以下能力:
                - 连接到安卓设备的termux
                - 在这个设备执行一些命令

            何时启用本工具包?
                - 用户强调需要测试模块的时候

            启用后应该怎么做?
                - 先询问用户是否需要先clone仓库到termux的home
                - 或者进入现有的kam项目模块仓库
                - git pull # 如果有子模块还需要先初始化子模块
                - 检测安卓设备是否包含kam命令
                - 使用kam build 构建模块, 使用kam install进行安装

            """
            ...
