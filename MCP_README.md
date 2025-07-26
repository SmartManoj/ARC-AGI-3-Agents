# MCP Integration with FastMCP

This document describes the MCP (Model Context Protocol) integration for ARC-AGI-3-Agents using FastMCP.

## Overview

The MCP integration allows external clients to control ARC-AGI-3 game agents through a standardized protocol. The implementation uses FastMCP for efficient, event-driven communication.

## Features

- ✅ **FastMCP Integration** - Uses FastMCP for efficient MCP communication
- ✅ **Direct Action Execution** - Actions are executed immediately when received
- ✅ **All 6 Game Actions** - Supports RESET, ACTION1-6 with coordinates/object numbers
- ✅ **No Threading Issues** - Runs directly in main method
- ✅ **Event-Driven** - FastMCP handles events automatically

## Installation

```bash
# Install FastMCP requirements
pip install -r requirements_mcp.txt
```

## Usage

### Running the MCP Agent

```bash
# Run MCP agent with FastMCP
python main.py -a mcpagent
```

### Available Actions

The MCP agent supports all 6 game actions:

- **RESET** - Initialize/restart game
- **ACTION1-5** - Basic game actions (no-op in current game)
- **ACTION6** - Click with coordinates or object numbers

### FastMCP Tool Registration

The agent automatically registers a `game_action` tool with FastMCP:

```python
@fastmcp.tool()
async def game_action(action: str, x: int = None, y: int = None, object_number: int = None):
    """Execute a game action (RESET, ACTION1-6)."""
    # Handles action execution
```

