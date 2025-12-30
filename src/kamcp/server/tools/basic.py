# Copyright (c) 2025 Memory Decoherence WG
"""Basic MCP tools (lazy registration).

Provides `register_basic_tools(mcp_app)` which registers several common
tools (kam_exec, kam_tips, kam_status). The tools are registered lazily
to avoid heavy imports at module import time.
"""

from __future__ import annotations
