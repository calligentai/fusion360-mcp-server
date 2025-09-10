# BMAD Method Directory

This directory contains BMAD (Basic Manufacturing and Design) method definitions organized in subfolders.

## Structure
- `basic/` - Basic manufacturing methods
- `advanced/` - Advanced manufacturing techniques  
- `templates/` - Reusable method templates
- `workflows/` - Complete design workflows

## Method File Format
Each method is defined as a JSON file with the following structure:

```json
{
  "name": "MethodName",
  "description": "Description of what the method does",
  "category": "basic|advanced|template|workflow", 
  "parameters": {
    "param_name": {
      "type": "string|number|boolean|array",
      "description": "Parameter description",
      "default": "optional_default_value"
    }
  },
  "steps": [
    {
      "tool": "ToolName",
      "parameters": {
        "param": "value_or_reference"
      }
    }
  ]
}
```