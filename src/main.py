#!/usr/bin/env python3
"""
Fusion 360 MCP Server

This module implements a FastAPI server that exposes Fusion 360 tools as callable endpoints.
It also implements the Model Context Protocol (MCP) for integration with Cline.
"""

import json
import os
import sys
from typing import Dict, Any, List, Optional, Union

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Import script generator
from script_generator import (
    generate_script,
    generate_multi_tool_script,
    generate_bmad_method_script,
    TOOL_REGISTRY,
    TOOLS_BY_NAME,
)

# Import BMAD reader
from bmad_reader import bmad_reader

# Create FastAPI app
app = FastAPI(
    title="Fusion 360 MCP Server",
    description="MCP server for Fusion 360 API integration",
    version="0.1.0",
)

# Define request/response models
class ToolParameter(BaseModel):
    """Parameter for a tool call."""
    
    value: Any = Field(..., description="The parameter value")


class ToolCallRequest(BaseModel):
    """Request to call a single tool."""
    
    tool_name: str = Field(..., description="The name of the tool to call")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Parameters for the tool call"
    )


class MultiToolCallRequest(BaseModel):
    """Request to call multiple tools in sequence."""
    
    tool_calls: List[ToolCallRequest] = Field(
        ..., description="List of tool calls to execute in sequence"
    )


class ScriptResponse(BaseModel):
    """Response containing a generated script."""
    
    script: str = Field(..., description="The generated Fusion 360 Python script")
    message: str = Field(default="Success", description="Status message")


class ToolInfo(BaseModel):
    """Information about a tool."""
    
    name: str = Field(..., description="The name of the tool")
    description: str = Field(..., description="Description of what the tool does")
    parameters: Dict[str, Dict[str, Any]] = Field(
        ..., description="Parameters accepted by the tool"
    )
    docs: str = Field(..., description="Link to documentation for the tool")


class ToolListResponse(BaseModel):
    """Response containing a list of available tools."""
    
    tools: List[ToolInfo] = Field(..., description="List of available tools")


class BMADMethodCallRequest(BaseModel):
    """Request to call a BMAD method."""
    
    method_name: str = Field(..., description="The name of the BMAD method to call")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Parameters for the BMAD method call"
    )


class BMADMethodInfo(BaseModel):
    """Information about a BMAD method."""
    
    name: str = Field(..., description="The name of the method")
    description: str = Field(..., description="Description of what the method does")
    category: str = Field(..., description="Category of the method")
    folder: str = Field(..., description="Folder path containing the method")
    parameters: Dict[str, Dict[str, Any]] = Field(
        ..., description="Parameters accepted by the method"
    )
    steps: List[Dict[str, Any]] = Field(..., description="Steps in the method")


class BMADMethodListResponse(BaseModel):
    """Response containing a list of available BMAD methods."""
    
    methods: List[BMADMethodInfo] = Field(..., description="List of available BMAD methods")


class BMADFolderListResponse(BaseModel):
    """Response containing a list of BMAD method folders."""
    
    folders: List[str] = Field(..., description="List of available folders")


# Define API routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Fusion 360 MCP Server is running"}


@app.get("/tools", response_model=ToolListResponse)
async def list_tools():
    """List all available tools."""
    return {"tools": TOOL_REGISTRY}


@app.post("/call_tool", response_model=ScriptResponse)
async def call_tool(request: ToolCallRequest):
    """Call a single tool and generate a Fusion 360 script."""
    try:
        script = generate_script(request.tool_name, request.parameters)
        return {"script": script, "message": "Success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating script: {str(e)}")


@app.post("/call_tools", response_model=ScriptResponse)
async def call_tools(request: MultiToolCallRequest):
    """Call multiple tools in sequence and generate a Fusion 360 script."""
    try:
        tool_calls = [
            {"tool_name": call.tool_name, "parameters": call.parameters}
            for call in request.tool_calls
        ]
        script = generate_multi_tool_script(tool_calls)
        return {"script": script, "message": "Success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating script: {str(e)}")


@app.get("/bmad/methods", response_model=BMADMethodListResponse)
async def list_bmad_methods(category: Optional[str] = None):
    """List all available BMAD methods, optionally filtered by category."""
    try:
        methods = bmad_reader.list_methods_by_category(category)
        method_infos = []
        for method in methods:
            method_info = BMADMethodInfo(
                name=method["name"],
                description=method["description"],
                category=method["category"],
                folder=method.get("folder", ""),
                parameters=method.get("parameters", {}),
                steps=method.get("steps", [])
            )
            method_infos.append(method_info)
        return {"methods": method_infos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing BMAD methods: {str(e)}")


@app.get("/bmad/folders", response_model=BMADFolderListResponse)
async def list_bmad_folders():
    """List all available BMAD method folders."""
    try:
        folders = bmad_reader.list_folders()
        return {"folders": folders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing BMAD folders: {str(e)}")


@app.post("/bmad/call_method", response_model=ScriptResponse)
async def call_bmad_method(request: BMADMethodCallRequest):
    """Call a BMAD method and generate a Fusion 360 script."""
    try:
        script = generate_bmad_method_script(request.method_name, request.parameters)
        return {"script": script, "message": "Success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating script: {str(e)}")


# MCP Server implementation
class McpServer:
    """
    Model Context Protocol (MCP) server implementation.
    
    This class implements the MCP protocol for integration with Cline.
    It wraps the FastAPI server and exposes tools via the MCP protocol.
    """
    
    def __init__(self):
        """Initialize the MCP server."""
        self.tools = {tool["name"]: tool for tool in TOOL_REGISTRY}
        
        # Add BMAD methods as tools
        bmad_methods = bmad_reader.read_all_methods()
        for method_name, method in bmad_methods.items():
            # Convert BMAD method to MCP tool format
            mcp_tool = {
                "name": f"BMAD_{method_name}",
                "description": f"BMAD Method: {method['description']}",
                "parameters": method.get("parameters", {})
            }
            self.tools[mcp_tool["name"]] = mcp_tool
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an MCP request.
        
        Args:
            request: The MCP request.
            
        Returns:
            The MCP response.
        """
        method = request.get("method")
        
        if method == "list_tools":
            return self._handle_list_tools()
        elif method == "call_tool":
            return self._handle_call_tool(request.get("params", {}))
        elif method == "list_bmad_methods":
            return self._handle_list_bmad_methods()
        elif method == "list_bmad_folders":
            return self._handle_list_bmad_folders()
        else:
            return {
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                }
            }
    
    def _handle_list_tools(self) -> Dict[str, Any]:
        """
        Handle a list_tools request.
        
        Returns:
            The MCP response.
        """
        tools = []
        for tool in TOOL_REGISTRY:
            tools.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": {
                    "type": "object",
                    "properties": {
                        name: {
                            "type": param["type"],
                            "description": param["description"],
                        }
                        for name, param in tool["parameters"].items()
                    },
                    "required": [
                        name for name, param in tool["parameters"].items()
                        if "default" not in param
                    ],
                },
            })
        
        return {"result": {"tools": tools}}
    
    def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a call_tool request.
        
        Args:
            params: The parameters for the tool call.
            
        Returns:
            The MCP response.
        """
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not tool_name:
            return {
                "error": {
                    "code": -32602,
                    "message": "Invalid params: missing tool name",
                }
            }
        
        if tool_name not in self.tools:
            return {
                "error": {
                    "code": -32602,
                    "message": f"Invalid params: unknown tool: {tool_name}",
                }
            }
        
        try:
            # Check if it's a BMAD method (prefixed with BMAD_)
            if tool_name.startswith("BMAD_"):
                method_name = tool_name[5:]  # Remove "BMAD_" prefix
                script = generate_bmad_method_script(method_name, arguments)
            else:
                script = generate_script(tool_name, arguments)
            
            return {
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": script,
                        }
                    ]
                }
            }
        except ValueError as e:
            return {
                "error": {
                    "code": -32602,
                    "message": f"Invalid params: {str(e)}",
                }
            }
        except Exception as e:
            return {
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}",
                }
            }
    
    def _handle_list_bmad_methods(self) -> Dict[str, Any]:
        """
        Handle a list_bmad_methods request.
        
        Returns:
            The MCP response.
        """
        try:
            methods = bmad_reader.read_all_methods()
            return {"result": {"methods": list(methods.values())}}
        except Exception as e:
            return {
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}",
                }
            }
    
    def _handle_list_bmad_folders(self) -> Dict[str, Any]:
        """
        Handle a list_bmad_folders request.
        
        Returns:
            The MCP response.
        """
        try:
            folders = bmad_reader.list_folders()
            return {"result": {"folders": folders}}
        except Exception as e:
            return {
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}",
                }
            }


def run_mcp_server():
    """Run the MCP server."""
    server = McpServer()
    
    # Read from stdin, write to stdout
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = server.handle_request(request)
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except json.JSONDecodeError:
            sys.stderr.write(f"Error: Invalid JSON: {line}\n")
            sys.stderr.flush()
        except Exception as e:
            sys.stderr.write(f"Error: {str(e)}\n")
            sys.stderr.flush()


def run_http_server():
    """Run the HTTP server."""
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    # Check if running in MCP mode
    if len(sys.argv) > 1 and sys.argv[1] == "--mcp":
        run_mcp_server()
    else:
        run_http_server()
