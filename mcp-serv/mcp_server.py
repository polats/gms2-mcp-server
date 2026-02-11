#!/usr/bin/env python3
"""
MCP Server for GameMaker Studio 2 project analysis.
Provides tools for parsing and analyzing GMS2 projects.
"""

import asyncio
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolResult
from dotenv import load_dotenv

from gms2_parser import GMS2ProjectParser


class GMS2MCPServer:
    """MCP Server for GameMaker Studio 2"""

    def __init__(self, project_path: Optional[str] = None):
        self.project_path = project_path
        print(f"GMS2MCPServer initialized with project_path: {project_path}", file=sys.stderr)

    def _get_project_path(self, arguments: Dict[str, Any]) -> str:
        """Gets the correct project path from arguments or config.env"""
        provided_path = arguments.get("project_path")

        # Use provided path if it's a real project path (not the MCP server root)
        if provided_path:
            current_dir = os.getcwd()
            if os.path.abspath(provided_path) != os.path.abspath(current_dir):
                return provided_path

        # Fall back to configured path
        if self.project_path:
            return self.project_path

        # Last resort: try config.env
        config_file = os.path.join(os.path.dirname(__file__), 'config.env')
        print(f"Looking for config.env at: {config_file}", file=sys.stderr)
        load_dotenv(config_file)
        config_path = os.getenv('GMS2_PROJECT_PATH')
        if config_path:
            print(f"Loading project path from config.env: {config_path}", file=sys.stderr)
            return config_path

        raise ValueError(
            "Project path not configured. Set GMS2_PROJECT_PATH in config.env "
            "or pass --project-path argument."
        )

    def _error(self, message: str) -> CallToolResult:
        """Returns an MCP error result with isError=True"""
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {message}")],
            isError=True,
        )

    def get_tools(self) -> List[Tool]:
        """Returns the list of available tools"""
        return [
            Tool(
                name="scan_gms2_project",
                description="Scans a GameMaker Studio 2 project and returns its file structure",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to GMS2 project folder (optional, uses config default)"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="get_gml_file_content",
                description="Gets the content of a specific GML file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to GMS2 project folder (optional, uses config default)"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Path to GML file (relative or absolute)"
                        }
                    },
                    "required": ["file_path"]
                }
            ),
            Tool(
                name="get_room_info",
                description="Gets detailed room information from a .yy file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to GMS2 project folder (optional, uses config default)"
                        },
                        "room_name": {
                            "type": "string",
                            "description": "Name of the room"
                        }
                    },
                    "required": ["room_name"]
                }
            ),
            Tool(
                name="get_object_info",
                description="Gets detailed object information from a .yy file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to GMS2 project folder (optional, uses config default)"
                        },
                        "object_name": {
                            "type": "string",
                            "description": "Name of the object"
                        }
                    },
                    "required": ["object_name"]
                }
            ),
            Tool(
                name="get_sprite_info",
                description="Gets sprite information including frames and metadata",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to GMS2 project folder (optional, uses config default)"
                        },
                        "sprite_name": {
                            "type": "string",
                            "description": "Name of the sprite"
                        }
                    },
                    "required": ["sprite_name"]
                }
            ),
            Tool(
                name="export_project_data",
                description="Exports all project data to text format (vibe2gml compatible)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to GMS2 project folder (optional, uses config default)"
                        },
                        "save_to_file": {
                            "type": "boolean",
                            "description": "Save result to file (default false)",
                            "default": False
                        },
                        "output_file": {
                            "type": "string",
                            "description": "Output file path (when save_to_file=true)"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="list_project_assets",
                description="Lists all project assets organized by category",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to GMS2 project folder (optional, uses config default)"
                        },
                        "category": {
                            "type": "string",
                            "description": "Filter by category",
                            "enum": ["Objects", "Scripts", "Rooms", "Sprites", "Notes", "Tile Sets", "Timelines", "Fonts", "Sounds", "Extensions"]
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="duplicate_object",
                description="Duplicates an existing GMS2 object with a new name, copies events, and registers it in the project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to GMS2 project folder (optional, uses config default)"
                        },
                        "source_object": {
                            "type": "string",
                            "description": "Name of the object to duplicate"
                        },
                        "new_object_name": {
                            "type": "string",
                            "description": "Name for the new duplicated object"
                        },
                        "property_overrides": {
                            "type": "object",
                            "description": "Object variable values to change in the duplicate (e.g. {\"target_yoffset\": \"-40\"})",
                            "additionalProperties": {"type": "string"}
                        }
                    },
                    "required": ["source_object", "new_object_name"]
                }
            ),
            Tool(
                name="add_room_instance",
                description="Adds an object instance to a room at a specified position",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to GMS2 project folder (optional, uses config default)"
                        },
                        "room_name": {
                            "type": "string",
                            "description": "Name of the room to add the instance to"
                        },
                        "object_name": {
                            "type": "string",
                            "description": "Name of the object to instantiate"
                        },
                        "x": {
                            "type": "number",
                            "description": "X position in the room"
                        },
                        "y": {
                            "type": "number",
                            "description": "Y position in the room"
                        },
                        "scale_x": {
                            "type": "number",
                            "description": "Horizontal scale (default 1.0)",
                            "default": 1.0
                        },
                        "scale_y": {
                            "type": "number",
                            "description": "Vertical scale (default 1.0)",
                            "default": 1.0
                        },
                        "rotation": {
                            "type": "number",
                            "description": "Rotation in degrees (default 0.0)",
                            "default": 0.0
                        },
                        "layer_name": {
                            "type": "string",
                            "description": "Target layer name (default 'Instances')",
                            "default": "Instances"
                        },
                        "property_overrides": {
                            "type": "object",
                            "description": "Object variable overrides for this instance",
                            "additionalProperties": {"type": "string"}
                        }
                    },
                    "required": ["room_name", "object_name", "x", "y"]
                }
            ),
            Tool(
                name="write_gml_file",
                description="Writes or updates the content of a GML file in the project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to GMS2 project folder (optional, uses config default)"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Path to GML file (relative to project root or absolute)"
                        },
                        "content": {
                            "type": "string",
                            "description": "The GML code to write to the file"
                        }
                    },
                    "required": ["file_path", "content"]
                }
            )
        ]

    async def handle_tool_call(self, name: str, arguments: Dict[str, Any]):
        """Handles tool calls"""
        try:
            if name == "scan_gms2_project":
                return await self._scan_project(arguments)
            elif name == "get_gml_file_content":
                return await self._get_gml_content(arguments)
            elif name == "get_room_info":
                return await self._get_room_info(arguments)
            elif name == "get_object_info":
                return await self._get_object_info(arguments)
            elif name == "get_sprite_info":
                return await self._get_sprite_info(arguments)
            elif name == "export_project_data":
                return await self._export_project_data(arguments)
            elif name == "list_project_assets":
                return await self._list_project_assets(arguments)
            elif name == "duplicate_object":
                return await self._duplicate_object(arguments)
            elif name == "add_room_instance":
                return await self._add_room_instance(arguments)
            elif name == "write_gml_file":
                return await self._write_gml_file(arguments)
            else:
                return self._error(f"Unknown tool: {name}")
        except Exception as e:
            return self._error(f"Error executing tool {name}: {str(e)}")

    async def _scan_project(self, arguments: Dict[str, Any]):
        """Scans a GMS2 project"""
        try:
            project_path = self._get_project_path(arguments)
        except ValueError as e:
            return self._error(str(e))

        parser = GMS2ProjectParser(project_path)
        result = parser.scan_project()

        if "error" in result:
            return self._error(result['error'])

        output = []
        output.append(f"GameMaker Studio 2 Project: {result['project_name']}")
        output.append(f"Path: {result['project_path']}")
        output.append(f"Total GML Files: {result['total_gml_files']}")
        output.append("")

        for category, info in result['categories'].items():
            if info['assets']:
                output.append(f"{category}: {len(info['assets'])} assets")
                for asset in info['assets']:
                    gml_count = len(asset['gml_files'])
                    yy_status = "+" if asset['yy_file'] else "-"
                    output.append(f"  - {asset['name']} (GML: {gml_count}, YY: {yy_status})")

        output.append("")
        output.append("Recent GML Files:")
        for i, (display_name, _, relative_path, _) in enumerate(result['gml_files'][:10]):
            output.append(f"  {i+1}. {display_name} ({relative_path})")

        if len(result['gml_files']) > 10:
            output.append(f"  ... and {len(result['gml_files']) - 10} more files")

        return [TextContent(type="text", text="\n".join(output))]

    async def _get_gml_content(self, arguments: Dict[str, Any]):
        """Gets the content of a GML file"""
        try:
            project_path = self._get_project_path(arguments)
        except ValueError as e:
            return self._error(str(e))

        file_path = arguments.get("file_path")
        if not file_path:
            return self._error("file_path is required")

        parser = GMS2ProjectParser(project_path)

        if not os.path.isabs(file_path):
            file_path = os.path.join(project_path, file_path)

        result = parser.get_gml_content(file_path)

        if "error" in result:
            return self._error(result['error'])

        output = []
        output.append(f"GML File: {result['relative_path']}")
        output.append(f"Lines: {result['line_count']}")
        output.append("-" * 50)
        output.append(result['content'])

        return [TextContent(type="text", text="\n".join(output))]

    async def _get_room_info(self, arguments: Dict[str, Any]):
        """Gets room information"""
        try:
            project_path = self._get_project_path(arguments)
        except ValueError as e:
            return self._error(str(e))

        room_name = arguments.get("room_name")
        if not room_name:
            return self._error("room_name is required")

        parser = GMS2ProjectParser(project_path)
        result = parser.get_room_info(room_name)

        if "error" in result:
            return self._error(result['error'])

        output = []
        output.append(f"Room Information: {result['room_name']}")
        output.append("=" * 50)
        output.append("")
        output.append("Formatted View:")
        output.append(result['formatted_info'])
        output.append("")
        output.append("Raw Data Available:")
        output.append(f"- YY File: {result['yy_path']}")
        output.append(f"- Layers: {len(result['data'].get('layers', []))}")
        output.append(f"- Room Settings: {'Yes' if result['data'].get('roomSettings') else 'No'}")

        return [TextContent(type="text", text="\n".join(output))]

    async def _get_object_info(self, arguments: Dict[str, Any]):
        """Gets object information"""
        try:
            project_path = self._get_project_path(arguments)
        except ValueError as e:
            return self._error(str(e))

        object_name = arguments.get("object_name")
        if not object_name:
            return self._error("object_name is required")

        parser = GMS2ProjectParser(project_path)
        result = parser.get_object_info(object_name)

        if "error" in result:
            return self._error(result['error'])

        output = []
        output.append(f"Object Information: {result['object_name']}")
        output.append("=" * 50)
        output.append("")
        output.append("Formatted View:")
        output.append(result['formatted_info'])
        output.append("")
        output.append("Raw Data Available:")
        output.append(f"- YY File: {result['yy_path']}")
        output.append(f"- Events: {len(result['data'].get('eventList', []))}")
        output.append(f"- Physics: {'Enabled' if result['data'].get('physicsObject') else 'Disabled'}")

        return [TextContent(type="text", text="\n".join(output))]

    async def _get_sprite_info(self, arguments: Dict[str, Any]):
        """Gets sprite information"""
        try:
            project_path = self._get_project_path(arguments)
        except ValueError as e:
            return self._error(str(e))

        sprite_name = arguments.get("sprite_name")
        if not sprite_name:
            return self._error("sprite_name is required")

        parser = GMS2ProjectParser(project_path)
        result = parser.get_sprite_info(sprite_name)

        if "error" in result:
            return self._error(result['error'])

        output = []
        output.append(f"Sprite Information: {result['sprite_name']}")
        output.append("=" * 50)
        output.append("")
        output.append(f"Sprite Path: {result['sprite_path']}")
        output.append(f"YY File: {'Yes' if result['yy_path'] else 'No'}")
        output.append(f"Frame Count: {len(result['frames'])}")

        if result['frames']:
            output.append("")
            output.append("Frames:")
            for i, frame in enumerate(result['frames']):
                output.append(f"  {i+1}. {frame['filename']}")

        return [TextContent(type="text", text="\n".join(output))]

    async def _export_project_data(self, arguments: Dict[str, Any]):
        """Exports all project data"""
        try:
            project_path = self._get_project_path(arguments)
        except ValueError as e:
            return self._error(str(e))

        save_to_file = arguments.get("save_to_file", False)
        output_file = arguments.get("output_file")

        parser = GMS2ProjectParser(project_path)
        export_data = parser.export_all_data()

        if save_to_file:
            if not output_file:
                project_name = os.path.basename(project_path)
                output_file = f"{project_name}_export.txt"

            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(export_data)

                return [TextContent(type="text", text=f"Project data exported to: {output_file}\n\nFile size: {len(export_data)} characters")]
            except Exception as e:
                return self._error(f"Error saving file: {str(e)}")
        else:
            return [TextContent(type="text", text=export_data)]

    async def _duplicate_object(self, arguments: Dict[str, Any]):
        """Duplicates a GMS2 object"""
        try:
            project_path = self._get_project_path(arguments)
        except ValueError as e:
            return self._error(str(e))

        source = arguments.get("source_object")
        new_name = arguments.get("new_object_name")
        overrides = arguments.get("property_overrides")

        if not source:
            return self._error("source_object is required")
        if not new_name:
            return self._error("new_object_name is required")

        parser = GMS2ProjectParser(project_path)
        result = parser.duplicate_object(source, new_name, overrides)

        if "error" in result:
            return self._error(result['error'])

        output = []
        output.append(f"Duplicated object '{result['source']}' -> '{result['new_name']}'")
        output.append(f"Path: {result['new_path']}")
        output.append(f"YY file: {result['yy_file']}")
        output.append(f"GML files copied: {', '.join(result['gml_files']) or '(none)'}")
        output.append(f"Registered in .yyp: {'Yes' if result['registered_in_yyp'] else 'No'}")
        if result['property_overrides']:
            output.append("Property overrides:")
            for k, v in result['property_overrides'].items():
                output.append(f"  {k} = {v}")

        return [TextContent(type="text", text="\n".join(output))]

    async def _add_room_instance(self, arguments: Dict[str, Any]):
        """Adds an instance to a room"""
        try:
            project_path = self._get_project_path(arguments)
        except ValueError as e:
            return self._error(str(e))

        room_name = arguments.get("room_name")
        object_name = arguments.get("object_name")
        x = arguments.get("x")
        y = arguments.get("y")

        if not room_name:
            return self._error("room_name is required")
        if not object_name:
            return self._error("object_name is required")
        if x is None or y is None:
            return self._error("x and y are required")

        parser = GMS2ProjectParser(project_path)
        result = parser.add_room_instance(
            room_name=room_name,
            object_name=object_name,
            x=float(x),
            y=float(y),
            scale_x=float(arguments.get("scale_x", 1.0)),
            scale_y=float(arguments.get("scale_y", 1.0)),
            rotation=float(arguments.get("rotation", 0.0)),
            layer_name=arguments.get("layer_name", "Instances"),
            property_overrides=arguments.get("property_overrides"),
        )

        if "error" in result:
            return self._error(result['error'])

        output = []
        output.append(f"Added instance '{result['instance_id']}' to room '{result['room_name']}'")
        output.append(f"Object: {result['object_name']}")
        output.append(f"Layer: {result['layer']}")
        output.append(f"Position: ({result['position']['x']}, {result['position']['y']})")
        if result['scale']['x'] != 1.0 or result['scale']['y'] != 1.0:
            output.append(f"Scale: ({result['scale']['x']}, {result['scale']['y']})")
        if result['rotation'] != 0.0:
            output.append(f"Rotation: {result['rotation']}")
        if result['property_overrides']:
            output.append("Property overrides:")
            for k, v in result['property_overrides'].items():
                output.append(f"  {k} = {v}")

        return [TextContent(type="text", text="\n".join(output))]

    async def _write_gml_file(self, arguments: Dict[str, Any]):
        """Writes content to a GML file"""
        try:
            project_path = self._get_project_path(arguments)
        except ValueError as e:
            return self._error(str(e))

        file_path = arguments.get("file_path")
        content = arguments.get("content")
        if not file_path:
            return self._error("file_path is required")
        if content is None:
            return self._error("content is required")

        parser = GMS2ProjectParser(project_path)
        result = parser.write_gml_file(file_path, content)

        if "error" in result:
            return self._error(result['error'])

        output = []
        output.append(f"Successfully wrote GML file: {result['relative_path']}")
        output.append(f"Lines: {result['line_count']}")
        output.append(f"Size: {result['char_count']} characters")

        return [TextContent(type="text", text="\n".join(output))]

    async def _list_project_assets(self, arguments: Dict[str, Any]):
        """Lists project assets"""
        try:
            project_path = self._get_project_path(arguments)
        except ValueError as e:
            return self._error(str(e))

        category_filter = arguments.get("category")

        parser = GMS2ProjectParser(project_path)
        result = parser.scan_project()

        if "error" in result:
            return self._error(result['error'])

        output = []
        output.append(f"Assets in {result['project_name']}:")
        output.append("=" * 50)

        categories_to_show = [category_filter] if category_filter else result['categories'].keys()

        for category in categories_to_show:
            if category in result['categories']:
                info = result['categories'][category]
                if info['assets']:
                    output.append(f"\n{category} ({len(info['assets'])} items):")
                    for asset in info['assets']:
                        gml_files = len(asset['gml_files'])
                        yy_file = "+" if asset['yy_file'] else "-"
                        output.append(f"  - {asset['name']} (GML: {gml_files}, YY: {yy_file})")

                        if gml_files > 0 and gml_files <= 5:
                            for gml in asset['gml_files']:
                                output.append(f"    * {gml['name']}")

        return [TextContent(type="text", text="\n".join(output))]


async def main():
    """Main server entry point"""
    config_file = os.path.join(os.path.dirname(__file__), 'config.env')
    load_dotenv(config_file)

    parser = argparse.ArgumentParser(description="GameMaker Studio 2 MCP Server")
    parser.add_argument("--project-path", type=str, help="Path to GMS2 project (overrides config.env)")
    args = parser.parse_args()

    project_path = args.project_path or os.getenv('GMS2_PROJECT_PATH')

    if project_path and not os.path.exists(project_path):
        print(f"Warning: Project path does not exist: {project_path}", file=sys.stderr)

    mcp_server = GMS2MCPServer(project_path)

    if project_path:
        print(f"MCP Server initialized with project path: {project_path}", file=sys.stderr)

    server = Server("gms2-mcp-server")

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return mcp_server.get_tools()

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict):
        return await mcp_server.handle_tool_call(name, arguments)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    try:
        print("Starting MCP server...", file=sys.stderr)
        asyncio.run(main())
    except Exception as e:
        print(f"Error starting MCP server: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
