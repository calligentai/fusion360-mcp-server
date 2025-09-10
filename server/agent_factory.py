#!/usr/bin/env python3
"""
Agent Factory

This module provides the AgentFactory class that creates appropriate agent instances
based on configuration (BasicAgent vs AutonomousAgent) and manages the agent registry.
"""

import uuid
import asyncio
import threading
from typing import Dict, Any, Optional, List
from .agent_config_parser import agent_config_parser
from .autonomous_agent import AutonomousAgent, BasicAgent


class AgentRegistry:
    """Registry for managing running agent instances."""
    
    def __init__(self):
        """Initialize the agent registry."""
        self._agents: Dict[str, Any] = {}  # agent_id -> agent_instance
        self._lock = threading.Lock()
    
    def register_agent(self, agent_id: str, agent: Any) -> None:
        """
        Register an agent instance.
        
        Args:
            agent_id: Unique agent identifier
            agent: Agent instance
        """
        with self._lock:
            self._agents[agent_id] = agent
    
    def unregister_agent(self, agent_id: str) -> Optional[Any]:
        """
        Unregister an agent instance.
        
        Args:
            agent_id: Agent identifier to remove
            
        Returns:
            Removed agent instance or None if not found
        """
        with self._lock:
            return self._agents.pop(agent_id, None)
    
    def get_agent(self, agent_id: str) -> Optional[Any]:
        """
        Get an agent instance by ID.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent instance or None if not found
        """
        with self._lock:
            return self._agents.get(agent_id)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """
        List all registered agents.
        
        Returns:
            List of agent status information
        """
        with self._lock:
            return [agent.get_status() for agent in self._agents.values()]
    
    def list_running_agents(self) -> List[Dict[str, Any]]:
        """
        List all currently running agents.
        
        Returns:
            List of running agent status information
        """
        with self._lock:
            return [
                agent.get_status() 
                for agent in self._agents.values() 
                if getattr(agent, '_running', False)
            ]
    
    def stop_all_agents(self) -> List[str]:
        """
        Stop all running agents.
        
        Returns:
            List of stopped agent IDs
        """
        stopped_agents = []
        with self._lock:
            for agent_id, agent in self._agents.items():
                if hasattr(agent, 'stop') and getattr(agent, '_running', False):
                    agent.stop()
                    stopped_agents.append(agent_id)
        return stopped_agents


class AgentFactory:
    """Factory for creating and managing agent instances."""
    
    def __init__(self):
        """Initialize the agent factory."""
        self.registry = AgentRegistry()
        self._running_tasks: Dict[str, asyncio.Task] = {}
    
    def create_agent(
        self, 
        agent_name: str, 
        tool_executor: Optional[Any] = None
    ) -> Optional[Any]:
        """
        Create an agent instance based on configuration.
        
        Args:
            agent_name: Name of the agent configuration
            tool_executor: Optional tool executor for autonomous agents
            
        Returns:
            Agent instance or None if configuration not found
        """
        # Get agent configuration
        config = agent_config_parser.get_agent(agent_name)
        if not config:
            raise ValueError(f"Agent configuration not found: {agent_name}")
        
        # Validate configuration
        validation_errors = agent_config_parser.validate_agent_config(config)
        if validation_errors:
            raise ValueError(f"Invalid agent configuration: {'; '.join(validation_errors)}")
        
        # Generate unique instance ID
        agent_id = f"{agent_name}_{str(uuid.uuid4())[:8]}"
        
        # Create appropriate agent type
        if config.get("autonomous", False):
            agent = AutonomousAgent(
                agent_id=agent_id,
                name=config["name"],
                config=config,
                tool_executor=tool_executor
            )
        else:
            agent = BasicAgent(
                agent_id=agent_id,
                name=config["name"],
                config=config
            )
        
        return agent
    
    def start_autonomous_agent(
        self, 
        agent_name: str, 
        goal: str, 
        context: Optional[Dict[str, Any]] = None,
        tool_executor: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Create and start an autonomous agent.
        
        Args:
            agent_name: Name of the agent configuration
            goal: Goal for the autonomous agent
            context: Optional context information
            tool_executor: Optional tool executor
            
        Returns:
            Agent status information including agent_id
        """
        # Create agent
        agent = self.create_agent(agent_name, tool_executor)
        if not isinstance(agent, AutonomousAgent):
            raise ValueError(f"Agent {agent_name} is not configured as autonomous")
        
        # Register agent
        self.registry.register_agent(agent.agent_id, agent)
        
        # Start agent
        status = agent.start(goal, context)
        
        # Start the async loop in a background task
        task = asyncio.create_task(self._run_agent_loop(agent))
        self._running_tasks[agent.agent_id] = task
        
        return status
    
    async def _run_agent_loop(self, agent: AutonomousAgent) -> None:
        """
        Run the agent loop in the background.
        
        Args:
            agent: Autonomous agent to run
        """
        try:
            await agent.run_loop()
        except Exception as e:
            agent.logger.error(f"Agent loop failed: {e}")
        finally:
            # Clean up task reference
            if agent.agent_id in self._running_tasks:
                del self._running_tasks[agent.agent_id]
    
    def stop_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Stop a running agent.
        
        Args:
            agent_id: ID of the agent to stop
            
        Returns:
            Final agent status or None if agent not found
        """
        agent = self.registry.get_agent(agent_id)
        if not agent:
            return None
        
        # Stop the agent
        if hasattr(agent, 'stop'):
            status = agent.stop()
        else:
            status = agent.get_status()
        
        # Cancel background task if it exists
        if agent_id in self._running_tasks:
            self._running_tasks[agent_id].cancel()
            del self._running_tasks[agent_id]
        
        return status
    
    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a specific agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent status or None if not found
        """
        agent = self.registry.get_agent(agent_id)
        return agent.get_status() if agent else None
    
    def get_agent_detailed_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed status of a specific agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Detailed agent status or None if not found
        """
        agent = self.registry.get_agent(agent_id)
        if agent and hasattr(agent, 'get_detailed_status'):
            return agent.get_detailed_status()
        elif agent:
            return agent.get_status()
        else:
            return None
    
    def list_running_agents(self) -> List[Dict[str, Any]]:
        """
        List all currently running agents.
        
        Returns:
            List of running agent status information
        """
        return self.registry.list_running_agents()
    
    def list_all_agents(self) -> List[Dict[str, Any]]:
        """
        List all registered agents (running and stopped).
        
        Returns:
            List of all agent status information
        """
        return self.registry.list_agents()
    
    def get_available_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available agent configurations.
        
        Returns:
            Dictionary of agent configurations with metadata
        """
        agents = agent_config_parser.get_agents()
        teams = agent_config_parser.get_teams()
        
        # Add metadata to agents
        agent_list = {}
        for name, config in agents.items():
            agent_list[name] = {
                "name": config.get("name", name),
                "description": config.get("description", ""),
                "autonomous": config.get("autonomous", False),
                "instructions": config.get("instructions", ""),
                "capabilities": config.get("capabilities", []),
                "parameters": config.get("parameters", {})
            }
        
        # Add teams
        team_list = {}
        for name, config in teams.items():
            team_list[name] = {
                "name": config.get("name", name),
                "description": config.get("description", ""),
                "members": config.get("members", []),
                "workflow": config.get("workflow", [])
            }
        
        return {
            "agents": agent_list,
            "teams": team_list
        }
    
    def cleanup(self) -> None:
        """Clean up all agents and tasks."""
        # Stop all agents
        self.registry.stop_all_agents()
        
        # Cancel all running tasks
        for task in self._running_tasks.values():
            task.cancel()
        self._running_tasks.clear()


# Global instance
agent_factory = AgentFactory()