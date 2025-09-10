#!/usr/bin/env python3
"""
Agent Configuration Parser

This module provides functionality to read and parse agent and team configuration files
from the .bmad-core directory.
"""

import json
import yaml
import os
from typing import Dict, List, Any, Optional, Union
from pathlib import Path


class AgentConfigParser:
    """Parser for agent and team configuration files."""
    
    def __init__(self, config_path: str = ".bmad-core"):
        """
        Initialize the agent config parser.
        
        Args:
            config_path: Path to the configuration directory
        """
        self.config_path = Path(config_path)
        self._agents_cache = None
        self._teams_cache = None
    
    def get_config_folder_path(self) -> Path:
        """Get the absolute path to the config folder."""
        # Get the path relative to the script location
        script_dir = Path(__file__).parent
        repo_root = script_dir.parent
        return repo_root / self.config_path
    
    def read_config_file(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Read the main agents configuration file.
        
        Args:
            force_refresh: Force re-reading from disk
            
        Returns:
            Configuration dictionary containing agents and teams
        """
        if self._agents_cache is not None and not force_refresh:
            return self._agents_cache
        
        config_folder = self.get_config_folder_path()
        
        # Try YAML first, then JSON
        for filename in ["agents.yaml", "agents.yml", "agents.json"]:
            config_file = config_folder / filename
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        if filename.endswith('.json'):
                            config = json.load(f)
                        else:
                            config = yaml.safe_load(f)
                    
                    self._agents_cache = config
                    return config
                except Exception as e:
                    print(f"Error reading config file {config_file}: {e}")
                    continue
        
        # Return empty config if no file found
        return {"agents": {}, "teams": {}}
    
    def get_agents(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Get all agent configurations.
        
        Args:
            force_refresh: Force re-reading from disk
            
        Returns:
            Dictionary mapping agent names to configurations
        """
        config = self.read_config_file(force_refresh)
        return config.get("agents", {})
    
    def get_teams(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Get all team configurations.
        
        Args:
            force_refresh: Force re-reading from disk
            
        Returns:
            Dictionary mapping team names to configurations
        """
        config = self.read_config_file(force_refresh)
        return config.get("teams", {})
    
    def get_agent(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific agent configuration.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Agent configuration or None if not found
        """
        agents = self.get_agents()
        return agents.get(agent_name)
    
    def get_team(self, team_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific team configuration.
        
        Args:
            team_name: Name of the team
            
        Returns:
            Team configuration or None if not found
        """
        teams = self.get_teams()
        return teams.get(team_name)
    
    def list_autonomous_agents(self) -> List[str]:
        """
        List all agents that have autonomous=true.
        
        Returns:
            List of autonomous agent names
        """
        agents = self.get_agents()
        return [
            name for name, config in agents.items() 
            if config.get("autonomous", False)
        ]
    
    def list_basic_agents(self) -> List[str]:
        """
        List all agents that have autonomous=false or not set.
        
        Returns:
            List of basic agent names
        """
        agents = self.get_agents()
        return [
            name for name, config in agents.items() 
            if not config.get("autonomous", False)
        ]
    
    def validate_agent_config(self, agent_config: Dict[str, Any]) -> List[str]:
        """
        Validate an agent configuration.
        
        Args:
            agent_config: Agent configuration to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Required fields
        required_fields = ["name", "description"]
        for field in required_fields:
            if field not in agent_config:
                errors.append(f"Missing required field: {field}")
        
        # Validate autonomous flag
        if "autonomous" in agent_config:
            if not isinstance(agent_config["autonomous"], bool):
                errors.append("Field 'autonomous' must be a boolean")
        
        # Validate parameters for autonomous agents
        if agent_config.get("autonomous", False):
            if "instructions" not in agent_config:
                errors.append("Autonomous agents require 'instructions' field")
        
        return errors
    
    def validate_team_config(self, team_config: Dict[str, Any]) -> List[str]:
        """
        Validate a team configuration.
        
        Args:
            team_config: Team configuration to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Required fields
        required_fields = ["name", "description", "members"]
        for field in required_fields:
            if field not in team_config:
                errors.append(f"Missing required field: {field}")
        
        # Validate members
        if "members" in team_config:
            if not isinstance(team_config["members"], list):
                errors.append("Field 'members' must be a list")
            else:
                agents = self.get_agents()
                for member in team_config["members"]:
                    if member not in agents:
                        errors.append(f"Unknown agent in team members: {member}")
        
        return errors


# Global instance
agent_config_parser = AgentConfigParser()