#!/usr/bin/env python3
"""
Autonomous Agent Implementation

This module provides the AutonomousAgent class that implements a goal-driven loop
(plan -> act -> report) for autonomous CAD design tasks.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
import json


class AgentState(Enum):
    """States of an autonomous agent."""
    CREATED = "created"
    PLANNING = "planning"
    ACTING = "acting"
    REPORTING = "reporting"
    COMPLETED = "completed"
    ERROR = "error"
    STOPPED = "stopped"


class AutonomousAgent:
    """
    Autonomous agent that runs a goal-driven loop for CAD design tasks.
    
    The agent follows a plan -> act -> report cycle:
    1. Plan: Analyze requirements and create an execution plan
    2. Act: Execute the planned actions using available tools
    3. Report: Evaluate results and provide status updates
    """
    
    def __init__(
        self, 
        agent_id: str,
        name: str,
        config: Dict[str, Any],
        tool_executor: Optional[Callable] = None
    ):
        """
        Initialize the autonomous agent.
        
        Args:
            agent_id: Unique identifier for this agent instance
            name: Name of the agent
            config: Agent configuration from .bmad-core
            tool_executor: Function to execute tools (for testing, can be mocked)
        """
        self.agent_id = agent_id
        self.name = name
        self.config = config
        self.tool_executor = tool_executor
        
        # Agent state
        self.state = AgentState.CREATED
        self.current_goal = None
        self.current_plan = []
        self.execution_log = []
        self.error_message = None
        
        # Control flags
        self._stop_requested = False
        self._running = False
        
        # Configuration parameters
        self.max_iterations = config.get("parameters", {}).get("max_iterations", 10)
        self.timeout_seconds = config.get("parameters", {}).get("timeout_seconds", 300)
        
        # Setup logging
        self.logger = logging.getLogger(f"AutonomousAgent.{agent_id}")
        
        # Statistics
        self.start_time = None
        self.end_time = None
        self.iterations_completed = 0
        
    def start(self, goal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Start the autonomous agent with a specific goal.
        
        Args:
            goal: The goal/objective for the agent
            context: Optional context information
            
        Returns:
            Initial status information
        """
        if self._running:
            raise ValueError("Agent is already running")
        
        self.current_goal = goal
        self.state = AgentState.PLANNING
        self._stop_requested = False
        self.start_time = time.time()
        self.error_message = None
        self.execution_log = []
        self.iterations_completed = 0
        
        self.logger.info(f"Starting agent {self.agent_id} with goal: {goal}")
        
        return self.get_status()
    
    def stop(self) -> Dict[str, Any]:
        """
        Request the agent to stop execution.
        
        Returns:
            Final status information
        """
        self._stop_requested = True
        self.logger.info(f"Stop requested for agent {self.agent_id}")
        
        if self.state not in [AgentState.COMPLETED, AgentState.ERROR, AgentState.STOPPED]:
            self.state = AgentState.STOPPED
            self.end_time = time.time()
        
        return self.get_status()
    
    async def run_loop(self) -> Dict[str, Any]:
        """
        Run the main autonomous loop: plan -> act -> report.
        
        Returns:
            Final execution results
        """
        if not self.current_goal:
            raise ValueError("No goal set for the agent")
        
        self._running = True
        
        try:
            while (
                self.iterations_completed < self.max_iterations 
                and not self._stop_requested
                and self._check_timeout()
            ):
                self.logger.info(f"Starting iteration {self.iterations_completed + 1}")
                
                # Plan phase
                await self._plan_phase()
                if self._should_stop():
                    break
                
                # Act phase
                await self._act_phase()
                if self._should_stop():
                    break
                
                # Report phase
                result = await self._report_phase()
                if self._should_stop():
                    break
                
                # Check if goal is completed
                if result.get("goal_completed", False):
                    self.state = AgentState.COMPLETED
                    break
                
                self.iterations_completed += 1
            
            # Final state determination
            if not self._stop_requested and self.state != AgentState.COMPLETED:
                if self.iterations_completed >= self.max_iterations:
                    self.state = AgentState.COMPLETED
                    self.logger.info("Agent completed maximum iterations")
                elif not self._check_timeout():
                    self.state = AgentState.ERROR
                    self.error_message = "Execution timeout exceeded"
                    self.logger.warning("Agent execution timed out")
            
        except Exception as e:
            self.state = AgentState.ERROR
            self.error_message = str(e)
            self.logger.error(f"Agent execution failed: {e}")
        
        finally:
            self._running = False
            self.end_time = time.time()
        
        return self.get_status()
    
    async def _plan_phase(self) -> None:
        """Execute the planning phase."""
        self.state = AgentState.PLANNING
        self.logger.info("Entering planning phase")
        
        # Simulate planning logic (TODO: Integrate with actual planning system)
        await asyncio.sleep(0.1)  # Simulate processing time
        
        # Create a basic plan based on the goal
        self.current_plan = self._create_plan_for_goal(self.current_goal)
        
        self.execution_log.append({
            "phase": "plan",
            "timestamp": time.time(),
            "plan": self.current_plan,
            "iteration": self.iterations_completed
        })
    
    async def _act_phase(self) -> None:
        """Execute the acting phase."""
        self.state = AgentState.ACTING
        self.logger.info("Entering acting phase")
        
        # Execute planned actions
        for action in self.current_plan:
            if self._should_stop():
                break
            
            try:
                result = await self._execute_action(action)
                action["result"] = result
                action["status"] = "completed"
            except Exception as e:
                action["result"] = str(e)
                action["status"] = "error"
                self.logger.error(f"Action execution failed: {e}")
        
        self.execution_log.append({
            "phase": "act",
            "timestamp": time.time(),
            "actions_executed": len([a for a in self.current_plan if a.get("status") == "completed"]),
            "actions_failed": len([a for a in self.current_plan if a.get("status") == "error"]),
            "iteration": self.iterations_completed
        })
    
    async def _report_phase(self) -> Dict[str, Any]:
        """Execute the reporting phase."""
        self.state = AgentState.REPORTING
        self.logger.info("Entering reporting phase")
        
        # Simulate reporting/evaluation logic
        await asyncio.sleep(0.1)
        
        # Evaluate if goal is completed
        completed_actions = len([a for a in self.current_plan if a.get("status") == "completed"])
        total_actions = len(self.current_plan)
        
        # Simple heuristic: goal completed if all actions succeeded
        goal_completed = total_actions > 0 and completed_actions == total_actions
        
        report = {
            "goal_completed": goal_completed,
            "actions_completed": completed_actions,
            "total_actions": total_actions,
            "success_rate": completed_actions / total_actions if total_actions > 0 else 0,
            "iteration": self.iterations_completed
        }
        
        self.execution_log.append({
            "phase": "report",
            "timestamp": time.time(),
            "report": report,
            "iteration": self.iterations_completed
        })
        
        return report
    
    def _create_plan_for_goal(self, goal: str) -> List[Dict[str, Any]]:
        """
        Create an execution plan for the given goal.
        
        Args:
            goal: The goal to create a plan for
            
        Returns:
            List of planned actions
        """
        # Simple goal-to-plan mapping (TODO: Integrate with actual planning logic)
        plan = []
        
        goal_lower = goal.lower()
        
        if "box" in goal_lower or "cube" in goal_lower:
            plan = [
                {"action": "CreateSketch", "parameters": {"plane": "xy"}},
                {"action": "DrawRectangle", "parameters": {"width": 10, "depth": 10}},
                {"action": "Extrude", "parameters": {"height": 5}}
            ]
        elif "circle" in goal_lower or "cylinder" in goal_lower:
            plan = [
                {"action": "CreateSketch", "parameters": {"plane": "xy"}},
                {"action": "DrawCircle", "parameters": {"radius": 5}},
                {"action": "Extrude", "parameters": {"height": 10}}
            ]
        else:
            # Default simple action for unknown goals
            plan = [
                {"action": "CreateSketch", "parameters": {"plane": "xy"}}
            ]
        
        return plan
    
    async def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single action.
        
        Args:
            action: The action to execute
            
        Returns:
            Execution result
        """
        if self.tool_executor:
            # Use provided tool executor (for testing/integration)
            return await self.tool_executor(action)
        else:
            # Simulate action execution
            await asyncio.sleep(0.05)  # Simulate processing time
            return {
                "status": "simulated",
                "action": action["action"],
                "message": f"Simulated execution of {action['action']}"
            }
    
    def _should_stop(self) -> bool:
        """Check if the agent should stop execution."""
        return (
            self._stop_requested 
            or self.state == AgentState.ERROR 
            or not self._check_timeout()
        )
    
    def _check_timeout(self) -> bool:
        """Check if execution has exceeded timeout."""
        if self.start_time is None:
            return True
        
        elapsed = time.time() - self.start_time
        return elapsed < self.timeout_seconds
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the agent.
        
        Returns:
            Status information
        """
        elapsed_time = 0
        if self.start_time:
            end_time = self.end_time or time.time()
            elapsed_time = end_time - self.start_time
        
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "state": self.state.value,
            "current_goal": self.current_goal,
            "iterations_completed": self.iterations_completed,
            "max_iterations": self.max_iterations,
            "elapsed_time": elapsed_time,
            "timeout_seconds": self.timeout_seconds,
            "error_message": self.error_message,
            "running": self._running,
            "execution_log_length": len(self.execution_log)
        }
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """
        Get detailed status including execution log.
        
        Returns:
            Detailed status information
        """
        status = self.get_status()
        status["execution_log"] = self.execution_log
        status["current_plan"] = self.current_plan
        return status


class BasicAgent:
    """
    Basic agent implementation for non-autonomous operations.
    
    This is a simple agent that can execute single commands or sequences
    without autonomous planning.
    """
    
    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        """
        Initialize the basic agent.
        
        Args:
            agent_id: Unique identifier for this agent instance
            name: Name of the agent
            config: Agent configuration
        """
        self.agent_id = agent_id
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"BasicAgent.{agent_id}")
    
    def execute_command(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single command.
        
        Args:
            command: Command to execute
            parameters: Command parameters
            
        Returns:
            Execution result
        """
        self.logger.info(f"Executing command: {command}")
        
        # Simulate command execution
        return {
            "status": "completed",
            "command": command,
            "parameters": parameters,
            "message": f"Basic agent executed {command}"
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of the basic agent."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "type": "basic",
            "autonomous": False
        }