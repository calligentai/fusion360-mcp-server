# Fusion 360 MCP Server

A Model Context Protocol (MCP) server that interfaces between Cline and Autodesk Fusion 360. This server exposes Fusion 360 toolbar-level commands as callable tools that map directly to Fusion's API.

## 🧠 Overview

This project allows Cline to:
- Parse natural language prompts (e.g., "Make a box with rounded corners")
- Resolve them into Fusion tool actions (e.g., CreateSketch → DrawRectangle → Extrude → Fillet)
- Call those tools through this MCP server
- Return Python scripts that can be executed in Fusion 360

## 🛠️ Installation

### Prerequisites

- Python 3.9 or higher
- Autodesk Fusion 360

### Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/fusion360-mcp-server.git
   cd fusion360-mcp-server
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Usage

### Running the HTTP Server

```bash
cd src
python main.py
```

This will start the FastAPI server at `http://127.0.0.1:8000`.

### Running as an MCP Server

```bash
cd src
python main.py --mcp
```

This will start the server in MCP mode, reading from stdin and writing to stdout.

### API Endpoints

- `GET /`: Check if the server is running
- `GET /tools`: List all available tools
- `POST /call_tool`: Call a single tool and generate a script
- `POST /call_tools`: Call multiple tools in sequence and generate a script
- `GET /bmad/folders`: List all BMAD method folders
- `GET /bmad/methods`: List all BMAD methods (optionally filter by category)
- `POST /bmad/call_method`: Call a BMAD method and generate a script

### Example API Calls

#### List Tools

```bash
curl -X GET http://127.0.0.1:8000/tools
```

#### Call a Single Tool

```bash
curl -X POST http://127.0.0.1:8000/call_tool \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "CreateSketch",
    "parameters": {
      "plane": "xy"
    }
  }'
```

#### Call Multiple Tools

```bash
curl -X POST http://127.0.0.1:8000/call_tools \
  -H "Content-Type: application/json" \
  -d '{
    "tool_calls": [
      {
        "tool_name": "CreateSketch",
        "parameters": {
          "plane": "xy"
        }
      },
      {
        "tool_name": "DrawRectangle",
        "parameters": {
          "width": 10,
          "depth": 10
        }
      },
      {
        "tool_name": "Extrude",
        "parameters": {
          "height": 5
        }
      }
    ]
  }'
```

#### List BMAD Methods

```bash
curl -X GET http://127.0.0.1:8000/bmad/methods
```

#### Call a BMAD Method

```bash
curl -X POST http://127.0.0.1:8000/bmad/call_method \
  -H "Content-Type: application/json" \
  -d '{
    "method_name": "SimpleBox",
    "parameters": {
      "width": 25,
      "depth": 15,
      "height": 10
    }
  }'
```

## 📦 Available Tools

The server currently supports the following Fusion 360 tools:

### Create
- **CreateSketch**: Creates a new sketch on a specified plane
- **DrawRectangle**: Draws a rectangle in the active sketch
- **DrawCircle**: Draws a circle in the active sketch
- **Extrude**: Extrudes a profile into a 3D body
- **Revolve**: Revolves a profile around an axis

### Modify
- **Fillet**: Adds a fillet to selected edges
- **Chamfer**: Adds a chamfer to selected edges
- **Shell**: Hollows out a solid body with a specified wall thickness
- **Combine**: Combines two bodies using boolean operations

### Export
- **ExportBody**: Exports a body to a file

## 🏗️ BMAD Methods

The server also includes BMAD (Basic Manufacturing and Design) methods - predefined workflows that combine multiple tools to create common CAD features. BMAD methods are organized in the `BMAD-method/` folder structure:

### Available BMAD Methods

#### Basic Methods (`basic/`)
- **SimpleBox**: Creates a simple rectangular box with specified dimensions
- **Cylinder**: Creates a cylinder with specified radius and height

#### Advanced Methods (`advanced/`)
- **RoundedBox**: Creates a box with filleted corners

#### Workflows (`workflows/`)
- **BasicEnclosure**: Creates a hollowed-out enclosure with specified wall thickness

### Using BMAD Methods

BMAD methods accept parameters just like individual tools, but execute a sequence of operations automatically. For example, the `SimpleBox` method creates a sketch, draws a rectangle, and extrudes it in one call.

## 🔌 MCP Integration

To use this server with Cline, add it to your MCP settings configuration file:

```json
{
  "mcpServers": {
    "fusion360": {
      "command": "python",
      "args": ["/path/to/fusion360-mcp-server/src/main.py", "--mcp"],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## 🧩 Tool Registry

Tools are defined in `src/tool_registry.json`. Each tool has:
- **name**: The name of the tool
- **description**: What the tool does
- **parameters**: The parameters the tool accepts
- **docs**: Link to relevant Fusion API documentation

Example tool definition:

```json
{
  "name": "Extrude",
  "description": "Extrudes a profile into a 3D body.",
  "parameters": {
    "profile_index": {
      "type": "integer",
      "description": "Index of the profile to extrude.",
      "default": 0
    },
    "height": {
      "type": "number",
      "description": "Height of the extrusion in mm."
    },
    "operation": {
      "type": "string",
      "description": "The operation type (e.g., 'new', 'join', 'cut', 'intersect').",
      "default": "new"
    }
  },
  "docs": "https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-6D381FCD-22AB-4F08-B4BB-5D3A130189AC"
}
```

## 📝 Script Generation

The server generates Fusion 360 Python scripts based on the tool calls. These scripts can be executed in Fusion 360's Script Editor.

Example generated script:

```python
import adsk.core, adsk.fusion, traceback

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = app.activeProduct
        
        # Get the active component in the design
        component = design.rootComponent
        
        # Create a new sketch on the xy plane
        sketches = component.sketches
        xyPlane = component.xYConstructionPlane
        sketch = sketches.add(xyPlane)
        
        # Draw a rectangle
        rectangle = sketch.sketchCurves.sketchLines.addTwoPointRectangle(
            adsk.core.Point3D.create(0, 0, 0),
            adsk.core.Point3D.create(10, 10, 0)
        )
        
        # Extrude the profile
        prof = sketch.profiles.item(0)
        extrudes = component.features.extrudeFeatures
        extInput = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        distance = adsk.core.ValueInput.createByReal(5)
        extInput.setDistanceExtent(False, distance)
        extrude = extrudes.add(extInput)
        
        ui.messageBox('Operation completed successfully')
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
```

## 🧪 Extending the Server

### Adding New Tools

1. Add a new tool definition to `src/tool_registry.json`
2. Add a script template to `SCRIPT_TEMPLATES` in `src/script_generator.py`
3. Add parameter processing logic to `_process_parameters` in `src/script_generator.py`

## 📚 Documentation Links

- [Fusion 360 API Docs](https://help.autodesk.com/view/fusion360/ENU/)
- [Python API Class Reference](https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-4190E5AD-BE6F-4682-A6D1-67D944D3DD58)
- [Feature API](https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-22D93F54-B84E-4C0B-97D3-CAEA7D2BAFFE)
- [Sketch API](https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-2533FC11-8BD3-4B3A-B52C-F8B470DC4065)

## 🔄 Future Enhancements

- Session state tracking for context-aware operations
- Dynamic tool registration
- Automation via socket or file polling
- More Fusion commands

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
