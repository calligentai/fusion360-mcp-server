#!/usr/bin/env python3
"""
BMAD Method Reader

This module provides functionality to read and parse BMAD method definitions
from the BMAD-method folder and its subfolders.
"""

import json
import os
import re
from typing import Dict, List, Any, Optional
from pathlib import Path


class BMADMethodReader:
    """Reader for BMAD method definitions."""
    
    def __init__(self, bmad_folder: str = "BMAD-method"):
        """
        Initialize the BMAD method reader.
        
        Args:
            bmad_folder: Path to the BMAD method folder
        """
        self.bmad_folder = Path(bmad_folder)
        self._methods_cache = None
    
    def get_methods_folder_path(self) -> Path:
        """Get the absolute path to the BMAD methods folder."""
        # Get the path relative to the script location
        script_dir = Path(__file__).parent
        repo_root = script_dir.parent
        return repo_root / self.bmad_folder
    
    def read_all_methods(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Read all BMAD method definitions from the folder structure.
        
        Args:
            force_refresh: Force re-reading from disk
            
        Returns:
            Dictionary mapping method names to method definitions
        """
        if self._methods_cache is not None and not force_refresh:
            return self._methods_cache
        
        methods = {}
        methods_folder = self.get_methods_folder_path()
        
        if not methods_folder.exists():
            return {}
        
        # Walk through all subfolders
        for json_file in methods_folder.rglob("*.json"):
            try:
                method = self._read_method_file(json_file)
                if method:
                    # Add folder path info for categorization
                    relative_path = json_file.relative_to(methods_folder)
                    method["folder"] = str(relative_path.parent)
                    methods[method["name"]] = method
            except Exception as e:
                print(f"Error reading method file {json_file}: {e}")
                continue
        
        self._methods_cache = methods
        return methods
    
    def _read_method_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Read a single BMAD method file.
        
        Args:
            file_path: Path to the method JSON file
            
        Returns:
            Method definition or None if invalid
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                method = json.load(f)
            
            # Validate required fields
            required_fields = ["name", "description", "category", "steps"]
            for field in required_fields:
                if field not in method:
                    print(f"Missing required field '{field}' in {file_path}")
                    return None
            
            return method
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in {file_path}: {e}")
            return None
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return None
    
    def get_method(self, method_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific method by name.
        
        Args:
            method_name: Name of the method
            
        Returns:
            Method definition or None if not found
        """
        methods = self.read_all_methods()
        return methods.get(method_name)
    
    def list_methods_by_category(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List methods, optionally filtered by category.
        
        Args:
            category: Category to filter by (basic, advanced, templates, workflows)
            
        Returns:
            List of method definitions
        """
        methods = self.read_all_methods()
        result = []
        
        for method in methods.values():
            if category is None or method.get("category") == category:
                result.append(method)
        
        return result
    
    def list_folders(self) -> List[str]:
        """
        List all available subfolders in the BMAD methods directory.
        
        Returns:
            List of folder names
        """
        methods_folder = self.get_methods_folder_path()
        
        if not methods_folder.exists():
            return []
        
        folders = []
        for item in methods_folder.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                folders.append(item.name)
        
        return sorted(folders)
    
    def substitute_parameters(self, method: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Substitute parameter values in method steps.
        
        Args:
            method: Method definition
            parameters: Parameter values to substitute
            
        Returns:
            Method with substituted parameters
        """
        # Deep copy the method to avoid modifying the original
        import copy
        substituted_method = copy.deepcopy(method)
        
        # Apply default values for missing parameters
        method_params = method.get("parameters", {})
        resolved_parameters = parameters.copy()
        
        for param_name, param_info in method_params.items():
            if param_name not in resolved_parameters and "default" in param_info:
                resolved_parameters[param_name] = param_info["default"]
        
        # Process each step
        for step in substituted_method.get("steps", []):
            step_params = step.get("parameters", {})
            for param_name, param_value in step_params.items():
                if isinstance(param_value, str):
                    # Replace template variables like {{width}} with actual values
                    substituted_value = self._substitute_template_variables(param_value, resolved_parameters)
                    step_params[param_name] = substituted_value
        
        return substituted_method
    
    def _substitute_template_variables(self, template: str, parameters: Dict[str, Any]) -> Any:
        """
        Substitute template variables in a string.
        
        Args:
            template: Template string with {{variable}} placeholders
            parameters: Parameter values
            
        Returns:
            Substituted value
        """
        # Find all template variables
        pattern = r'\{\{(\w+)\}\}'
        matches = re.findall(pattern, template)
        
        if not matches:
            return template
        
        # If the entire string is a single template variable, return the actual type
        if len(matches) == 1 and template == f"{{{{{matches[0]}}}}}":
            param_name = matches[0]
            if param_name in parameters:
                return parameters[param_name]
            else:
                raise ValueError(f"Missing required parameter: {param_name}")
        
        # Multiple variables or partial substitution, return as string
        result = template
        for var_name in matches:
            if var_name in parameters:
                result = result.replace(f"{{{{{var_name}}}}}", str(parameters[var_name]))
            else:
                raise ValueError(f"Missing required parameter: {var_name}")
        
        return result


# Global instance
bmad_reader = BMADMethodReader()