"""
MCP Server entry point for Cockpit image generation.

Usage:
    python -m server

Environment variables:
    COCKPIT_BASE_URL: Base URL of the Cockpit server (default: http://127.0.0.1:8787)
"""

import os
import sys
import json
import asyncio
from typing import Any, Dict

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("Error: MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

from .requests_cockpit_api_client import RequestsCockpitApiClient
from .mcp_tools import (
    workflows_list,
    workflow_get,
    images_generate,
    images_generate_many,
)


# Get base URL from environment
BASE_URL = os.environ.get("COCKPIT_BASE_URL", "http://127.0.0.1:8787")

# Create the MCP server
app = Server("cockpit-image-generator")

# Create the HTTP client
client = RequestsCockpitApiClient(base_url=BASE_URL)


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="workflows_list",
            description="List all available image generation workflows",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="workflow_get",
            description="Get details about a specific workflow (parameters, presets)",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {
                        "type": "string",
                        "description": "The workflow ID (e.g., 'flux2_klein_distilled')",
                    },
                },
                "required": ["workflow_id"],
            },
        ),
        Tool(
            name="images_generate",
            description=(
                "Generate images using a workflow. "
                "Waits for completion by default and returns image URLs. "
                "Can generate multiple images with the same params using 'count'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {
                        "type": "string",
                        "description": "Workflow ID (default: flux2_klein_distilled)",
                        "default": "flux2_klein_distilled",
                    },
                    "params": {
                        "type": "object",
                        "description": "Workflow parameters (e.g., {\"prompt\": \"a cat\", \"seed\": 42})",
                        "default": {},
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of images to generate (default: 1)",
                        "default": 1,
                    },
                    "wait": {
                        "type": "boolean",
                        "description": "Wait for completion (default: true)",
                        "default": True,
                    },
                    "timeout_sec": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 600)",
                        "default": 600,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="images_generate_many",
            description=(
                "Generate multiple images with different prompts in batch. "
                "Useful for generating variations (e.g., 10 different cat images). "
                "Waits for all to complete and returns URLs (unless wait=false)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of prompts (e.g., [\"a cat\", \"a dog\", \"a tree\"])",
                    },
                    "workflow_id": {
                        "type": "string",
                        "description": "Workflow ID (default: flux2_klein_distilled)",
                        "default": "flux2_klein_distilled",
                    },
                    "base_params": {
                        "type": "object",
                        "description": "Base parameters to merge with each prompt (e.g., {\"width\": 512})",
                        "default": {},
                    },
                    "wait": {
                        "type": "boolean",
                        "description": "Wait for all completions (default: true)",
                        "default": True,
                    },
                    "timeout_sec": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 600)",
                        "default": 600,
                    },
                },
                "required": ["prompts"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "workflows_list":
            result = workflows_list(client)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "workflow_get":
            workflow_id = arguments.get("workflow_id")
            if not workflow_id:
                raise ValueError("workflow_id is required")
            result = workflow_get(client, workflow_id)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "images_generate":
            workflow_id = arguments.get("workflow_id", "flux2_klein_distilled")
            params = arguments.get("params", {})
            count = arguments.get("count", 1)
            wait = arguments.get("wait", True)
            timeout_sec = arguments.get("timeout_sec", 600)

            result = images_generate(
                client,
                workflow_id=workflow_id,
                params=params,
                count=count,
                wait=wait,
                timeout_sec=timeout_sec,
                base_url=BASE_URL,
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "images_generate_many":
            prompts = arguments.get("prompts")
            if not prompts:
                raise ValueError("prompts is required")
            workflow_id = arguments.get("workflow_id", "flux2_klein_distilled")
            base_params = arguments.get("base_params", {})
            wait = arguments.get("wait", True)
            timeout_sec = arguments.get("timeout_sec", 600)

            result = images_generate_many(
                client,
                prompts=prompts,
                workflow_id=workflow_id,
                base_params=base_params,
                wait=wait,
                timeout_sec=timeout_sec,
                base_url=BASE_URL,
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        error_msg = f"Error calling {name}: {str(e)}"
        return [TextContent(type="text", text=json.dumps({"error": error_msg}))]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    print(f"Starting Cockpit MCP server (base_url={BASE_URL})...", file=sys.stderr)
    asyncio.run(main())
