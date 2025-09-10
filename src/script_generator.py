"""
Script Generator for Fusion 360 MCP Server

This module generates Fusion 360 Python scripts based on tool parameters.
"""

import json
import os
from typing import Dict, Any, List, Optional, Union

# Import BMAD method reader
from bmad_reader import bmad_reader

# Load tool registry
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOL_REGISTRY_PATH = os.path.join(SCRIPT_DIR, "tool_registry.json")

with open(TOOL_REGISTRY_PATH, "r") as f:
    TOOL_REGISTRY = json.load(f)

# Create a lookup dictionary for tools
TOOLS_BY_NAME = {tool["name"]: tool for tool in TOOL_REGISTRY}

# Script templates for each tool
SCRIPT_TEMPLATES = {
    "CreateSketch": """
# Create a new sketch on the {plane} plane
sketches = component.sketches
{plane_code}
sketch = sketches.add({plane_var})
""",
    "DrawRectangle": """
# Draw a rectangle
rectangle = sketch.sketchCurves.sketchLines.addTwoPointRectangle(
    adsk.core.Point3D.create({origin_x}, {origin_y}, {origin_z}),
    adsk.core.Point3D.create({origin_x} + {width}, {origin_y} + {depth}, {origin_z})
)
""",
    "DrawCircle": """
# Draw a circle
circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(
    adsk.core.Point3D.create({center_x}, {center_y}, {center_z}),
    {radius}
)
""",
    "Extrude": """
# Extrude the profile
prof = sketch.profiles.item({profile_index})
extrudes = component.features.extrudeFeatures
extInput = extrudes.createInput(prof, adsk.fusion.FeatureOperations.{operation_code}FeatureOperation)
distance = adsk.core.ValueInput.createByReal({height})
extInput.setDistanceExtent(False, distance)
extrude = extrudes.add(extInput)
""",
    "Revolve": """
# Revolve the profile
prof = sketch.profiles.item({profile_index})
revolves = component.features.revolveFeatures
revInput = revolves.createInput(prof, adsk.fusion.FeatureOperations.{operation_code}FeatureOperation)
axis = adsk.core.Line3D.create(
    adsk.core.Point3D.create({axis_origin_x}, {axis_origin_y}, {axis_origin_z}),
    adsk.core.Vector3D.create({axis_direction_x}, {axis_direction_y}, {axis_direction_z})
)
revInput.setRevolutionExtent(False, adsk.core.ValueInput.createByString("{angle} deg"))
revInput.revolutionAxis = axis
revolve = revolves.add(revInput)
""",
    "Fillet": """
# Fillet edges
fillets = component.features.filletFeatures
edgeCollection = adsk.core.ObjectCollection.create()
body = component.bRepBodies.item({body_index})
{edge_collection_code}
filletInput = fillets.createInput()
filletInput.addConstantRadiusEdgeSet(edgeCollection, adsk.core.ValueInput.createByReal({radius}), True)
fillet = fillets.add(filletInput)
""",
    "Chamfer": """
# Chamfer edges
chamfers = component.features.chamferFeatures
edgeCollection = adsk.core.ObjectCollection.create()
body = component.bRepBodies.item({body_index})
{edge_collection_code}
chamferInput = chamfers.createInput(edgeCollection, True)
chamferInput.setToEqualDistance(adsk.core.ValueInput.createByReal({distance}))
chamfer = chamfers.add(chamferInput)
""",
    "Shell": """
# Shell the body
shells = component.features.shellFeatures
body = component.bRepBodies.item({body_index})
faceCollection = adsk.core.ObjectCollection.create()
{face_collection_code}
shellInput = shells.createInput([body], faceCollection)
shellInput.insideThickness = adsk.core.ValueInput.createByReal({thickness})
shell = shells.add(shellInput)
""",
    "Combine": """
# Combine bodies
combines = component.features.combineFeatures
targetBody = component.bRepBodies.item({target_body_index})
toolBodies = adsk.core.ObjectCollection.create()
toolBody = component.bRepBodies.item({tool_body_index})
toolBodies.add(toolBody)
combineInput = combines.createInput(targetBody, toolBodies)
combineInput.operation = adsk.fusion.FeatureOperations.{operation_code}FeatureOperation
combine = combines.add(combineInput)
""",
    "ExportBody": """
# Export body
body = component.bRepBodies.item({body_index})
exportMgr = adsk.fusion.ExportManager.cast(design.exportManager)
{export_options_code}
exportMgr.execute('{filename}', '{directory}', options)
"""
}

# Base script template
BASE_SCRIPT_TEMPLATE = """import adsk.core, adsk.fusion, traceback

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = app.activeProduct
        
        # Get the active component in the design
        component = design.rootComponent
        
{tool_scripts}
        
        ui.messageBox('Operation completed successfully')
    except:
        if ui:
            ui.messageBox('Failed:\\n{{}}'.format(traceback.format_exc()))
"""

def generate_script(tool_name: str, parameters: Dict[str, Any]) -> str:
    """
    Generate a Fusion 360 Python script for the specified tool and parameters.
    
    Args:
        tool_name: The name of the tool to generate a script for.
        parameters: A dictionary of parameter values for the tool.
        
    Returns:
        A string containing the generated Python script.
    """
    if tool_name not in TOOLS_BY_NAME:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    tool = TOOLS_BY_NAME[tool_name]
    template = SCRIPT_TEMPLATES.get(tool_name)
    
    if not template:
        raise ValueError(f"No script template available for tool: {tool_name}")
    
    # Process parameters based on tool type
    processed_params = _process_parameters(tool_name, parameters)
    
    # Format the tool script with the processed parameters
    tool_script = template.format(**processed_params)
    
    # Indent the tool script for inclusion in the base template
    indented_tool_script = "\n".join(f"        {line}" for line in tool_script.strip().split("\n"))
    
    # Generate the full script
    full_script = BASE_SCRIPT_TEMPLATE.format(tool_scripts=indented_tool_script)
    
    return full_script

def _process_parameters(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process and validate parameters for a specific tool.
    
    Args:
        tool_name: The name of the tool.
        parameters: The raw parameters provided for the tool.
        
    Returns:
        A dictionary of processed parameters ready for script generation.
    """
    processed = parameters.copy()
    
    # Apply default values for missing parameters
    tool = TOOLS_BY_NAME[tool_name]
    for param_name, param_info in tool["parameters"].items():
        if param_name not in processed and "default" in param_info:
            processed[param_name] = param_info["default"]
    
    # Tool-specific parameter processing
    if tool_name == "CreateSketch":
        plane = processed.get("plane", "xy").lower()
        if plane == "xy":
            processed["plane_code"] = "xyPlane = component.xYConstructionPlane"
            processed["plane_var"] = "xyPlane"
        elif plane == "yz":
            processed["plane_code"] = "yzPlane = component.yZConstructionPlane"
            processed["plane_var"] = "yzPlane"
        elif plane == "xz":
            processed["plane_code"] = "xzPlane = component.xZConstructionPlane"
            processed["plane_var"] = "xzPlane"
        else:
            raise ValueError(f"Invalid plane: {plane}. Must be one of: xy, yz, xz")
    
    elif tool_name == "Extrude":
        operation = processed.get("operation", "new").lower()
        if operation == "new":
            processed["operation_code"] = "NewBody"
        elif operation == "join":
            processed["operation_code"] = "JoinFeature"
        elif operation == "cut":
            processed["operation_code"] = "CutFeature"
        elif operation == "intersect":
            processed["operation_code"] = "IntersectFeature"
        else:
            raise ValueError(f"Invalid operation: {operation}. Must be one of: new, join, cut, intersect")
    
    elif tool_name == "Revolve":
        operation = processed.get("operation", "new").lower()
        if operation == "new":
            processed["operation_code"] = "NewBody"
        elif operation == "join":
            processed["operation_code"] = "JoinFeature"
        elif operation == "cut":
            processed["operation_code"] = "CutFeature"
        elif operation == "intersect":
            processed["operation_code"] = "IntersectFeature"
        else:
            raise ValueError(f"Invalid operation: {operation}. Must be one of: new, join, cut, intersect")
    
    elif tool_name == "Fillet":
        edge_indices = processed.get("edge_indices", [])
        if edge_indices:
            edge_code_lines = []
            for idx in edge_indices:
                edge_code_lines.append(f"edge = body.edges.item({idx})")
                edge_code_lines.append("edgeCollection.add(edge)")
            processed["edge_collection_code"] = "\n".join(edge_code_lines)
        else:
            processed["edge_collection_code"] = "for edge in body.edges:\n    edgeCollection.add(edge)"
    
    elif tool_name == "Chamfer":
        edge_indices = processed.get("edge_indices", [])
        if edge_indices:
            edge_code_lines = []
            for idx in edge_indices:
                edge_code_lines.append(f"edge = body.edges.item({idx})")
                edge_code_lines.append("edgeCollection.add(edge)")
            processed["edge_collection_code"] = "\n".join(edge_code_lines)
        else:
            processed["edge_collection_code"] = "for edge in body.edges:\n    edgeCollection.add(edge)"
    
    elif tool_name == "Shell":
        face_indices = processed.get("face_indices", [])
        if face_indices:
            face_code_lines = []
            for idx in face_indices:
                face_code_lines.append(f"face = body.faces.item({idx})")
                face_code_lines.append("faceCollection.add(face)")
            processed["face_collection_code"] = "\n".join(face_code_lines)
        else:
            processed["face_collection_code"] = "# No faces selected for removal"
    
    elif tool_name == "Combine":
        operation = processed.get("operation", "join").lower()
        if operation == "join":
            processed["operation_code"] = "JoinFeature"
        elif operation == "cut":
            processed["operation_code"] = "CutFeature"
        elif operation == "intersect":
            processed["operation_code"] = "IntersectFeature"
        else:
            raise ValueError(f"Invalid operation: {operation}. Must be one of: join, cut, intersect")
    
    elif tool_name == "ExportBody":
        format = processed.get("format", "stl").lower()
        if format == "stl":
            processed["export_options_code"] = "options = exportMgr.createSTLExportOptions(body)"
        elif format == "obj":
            processed["export_options_code"] = "options = exportMgr.createOBJExportOptions(body)"
        elif format == "step":
            processed["export_options_code"] = "options = exportMgr.createSTEPExportOptions()"
        elif format == "iges":
            processed["export_options_code"] = "options = exportMgr.createIGESExportOptions()"
        elif format == "sat":
            processed["export_options_code"] = "options = exportMgr.createSATExportOptions()"
        else:
            raise ValueError(f"Invalid format: {format}. Must be one of: stl, obj, step, iges, sat")
        
        # Set directory to the user's desktop by default
        processed["directory"] = os.path.expanduser("~/Desktop")
    
    return processed

def generate_multi_tool_script(tool_calls: List[Dict[str, Any]]) -> str:
    """
    Generate a Fusion 360 Python script for multiple tool calls.
    
    Args:
        tool_calls: A list of dictionaries, each containing 'tool_name' and 'parameters' keys.
        
    Returns:
        A string containing the generated Python script.
    """
    tool_scripts = []
    
    for call in tool_calls:
        tool_name = call["tool_name"]
        parameters = call["parameters"]
        
        if tool_name not in TOOLS_BY_NAME:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        template = SCRIPT_TEMPLATES.get(tool_name)
        if not template:
            raise ValueError(f"No script template available for tool: {tool_name}")
        
        processed_params = _process_parameters(tool_name, parameters)
        tool_script = template.format(**processed_params)
        tool_scripts.append(tool_script)
    
    # Combine all tool scripts
    combined_tool_script = "\n".join(tool_scripts)
    
    # Indent the combined tool script for inclusion in the base template
    indented_tool_script = "\n".join(f"        {line}" for line in combined_tool_script.strip().split("\n"))
    
    # Generate the full script
    full_script = BASE_SCRIPT_TEMPLATE.format(tool_scripts=indented_tool_script)
    
    return full_script


def generate_bmad_method_script(method_name: str, parameters: Dict[str, Any]) -> str:
    """
    Generate a Fusion 360 Python script for a BMAD method.
    
    Args:
        method_name: The name of the BMAD method to generate a script for.
        parameters: A dictionary of parameter values for the method.
        
    Returns:
        A string containing the generated Python script.
    """
    # Get the method definition
    method = bmad_reader.get_method(method_name)
    if not method:
        raise ValueError(f"Unknown BMAD method: {method_name}")
    
    # Substitute parameters in the method steps
    substituted_method = bmad_reader.substitute_parameters(method, parameters)
    
    # Convert method steps to tool calls
    tool_calls = []
    for step in substituted_method.get("steps", []):
        tool_calls.append({
            "tool_name": step["tool"],
            "parameters": step.get("parameters", {})
        })
    
    # Generate script using the existing multi-tool generator
    return generate_multi_tool_script(tool_calls)
