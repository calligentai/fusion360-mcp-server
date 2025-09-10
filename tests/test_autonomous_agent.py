#!/usr/bin/env python3
"""
Test script for autonomous agent functionality.

This module contains unit tests for the agent configuration parser,
autonomous agent implementation, and agent factory.
"""

import asyncio
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, AsyncMock
from pathlib import Path

# Add the parent directories to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from server.agent_config_parser import AgentConfigParser
from server.autonomous_agent import AutonomousAgent, BasicAgent, AgentState
from server.agent_factory import AgentFactory, AgentRegistry


class TestAgentConfigParser(unittest.TestCase):
    """Test cases for agent configuration parser."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / ".bmad-core"
        self.config_path.mkdir(exist_ok=True)
        
        # Create test config file
        test_config = {
            "agents": {
                "test_autonomous": {
                    "name": "Test Autonomous Agent",
                    "description": "A test autonomous agent",
                    "autonomous": True,
                    "instructions": "Test instructions",
                    "capabilities": ["test_capability"],
                    "parameters": {
                        "max_iterations": 5,
                        "timeout_seconds": 60
                    }
                },
                "test_basic": {
                    "name": "Test Basic Agent", 
                    "description": "A test basic agent",
                    "autonomous": False,
                    "capabilities": ["basic_capability"]
                }
            },
            "teams": {
                "test_team": {
                    "name": "Test Team",
                    "description": "A test team",
                    "members": ["test_autonomous", "test_basic"],
                    "workflow": []
                }
            }
        }
        
        config_file = self.config_path / "agents.yaml"
        import yaml
        with open(config_file, 'w') as f:
            yaml.dump(test_config, f)
        
        self.parser = AgentConfigParser(str(self.config_path))
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_read_config_file(self):
        """Test reading configuration file."""
        config = self.parser.read_config_file()
        self.assertIn("agents", config)
        self.assertIn("teams", config)
        self.assertEqual(len(config["agents"]), 2)
        self.assertEqual(len(config["teams"]), 1)
    
    def test_get_agents(self):
        """Test getting agent configurations."""
        agents = self.parser.get_agents()
        self.assertIn("test_autonomous", agents)
        self.assertIn("test_basic", agents)
        
        autonomous_agent = agents["test_autonomous"]
        self.assertTrue(autonomous_agent["autonomous"])
        self.assertEqual(autonomous_agent["name"], "Test Autonomous Agent")
    
    def test_get_teams(self):
        """Test getting team configurations."""
        teams = self.parser.get_teams()
        self.assertIn("test_team", teams)
        
        test_team = teams["test_team"]
        self.assertEqual(len(test_team["members"]), 2)
        self.assertIn("test_autonomous", test_team["members"])
    
    def test_list_autonomous_agents(self):
        """Test listing autonomous agents."""
        autonomous_agents = self.parser.list_autonomous_agents()
        self.assertEqual(len(autonomous_agents), 1)
        self.assertIn("test_autonomous", autonomous_agents)
    
    def test_list_basic_agents(self):
        """Test listing basic agents."""
        basic_agents = self.parser.list_basic_agents()
        self.assertEqual(len(basic_agents), 1)
        self.assertIn("test_basic", basic_agents)
    
    def test_validate_agent_config(self):
        """Test agent configuration validation."""
        # Valid config
        valid_config = {
            "name": "Test Agent",
            "description": "Test description",
            "autonomous": True,
            "instructions": "Test instructions"
        }
        errors = self.parser.validate_agent_config(valid_config)
        self.assertEqual(len(errors), 0)
        
        # Invalid config - missing name
        invalid_config = {
            "description": "Test description"
        }
        errors = self.parser.validate_agent_config(invalid_config)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("name" in error for error in errors))
    
    def test_validate_team_config(self):
        """Test team configuration validation."""
        # Valid config
        valid_config = {
            "name": "Test Team",
            "description": "Test description",
            "members": ["test_autonomous"]
        }
        errors = self.parser.validate_team_config(valid_config)
        self.assertEqual(len(errors), 0)
        
        # Invalid config - unknown member
        invalid_config = {
            "name": "Test Team",
            "description": "Test description", 
            "members": ["unknown_agent"]
        }
        errors = self.parser.validate_team_config(invalid_config)
        self.assertGreater(len(errors), 0)


class TestAutonomousAgent(unittest.TestCase):
    """Test cases for autonomous agent."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "name": "Test Agent",
            "description": "Test autonomous agent",
            "autonomous": True,
            "instructions": "Test instructions",
            "parameters": {
                "max_iterations": 3,
                "timeout_seconds": 30
            }
        }
        
        self.mock_tool_executor = AsyncMock()
        self.agent = AutonomousAgent(
            agent_id="test_agent_123",
            name="Test Agent",
            config=self.config,
            tool_executor=self.mock_tool_executor
        )
    
    def test_agent_initialization(self):
        """Test agent initialization."""
        self.assertEqual(self.agent.agent_id, "test_agent_123")
        self.assertEqual(self.agent.name, "Test Agent")
        self.assertEqual(self.agent.state, AgentState.CREATED)
        self.assertEqual(self.agent.max_iterations, 3)
        self.assertEqual(self.agent.timeout_seconds, 30)
    
    def test_start_agent(self):
        """Test starting the agent."""
        goal = "Create a simple box"
        status = self.agent.start(goal)
        
        self.assertEqual(self.agent.current_goal, goal)
        self.assertEqual(self.agent.state, AgentState.PLANNING)
        self.assertIsNotNone(self.agent.start_time)
        self.assertIn("agent_id", status)
        self.assertIn("state", status)
    
    def test_stop_agent(self):
        """Test stopping the agent."""
        self.agent.start("Test goal")
        status = self.agent.stop()
        
        self.assertTrue(self.agent._stop_requested)
        self.assertEqual(self.agent.state, AgentState.STOPPED)
        self.assertIn("state", status)
    
    def test_get_status(self):
        """Test getting agent status."""
        status = self.agent.get_status()
        
        required_fields = [
            "agent_id", "name", "state", "iterations_completed",
            "max_iterations", "elapsed_time", "timeout_seconds",
            "running", "execution_log_length"
        ]
        
        for field in required_fields:
            self.assertIn(field, status)
    
    def test_create_plan_for_goal(self):
        """Test plan creation for different goals."""
        # Test box creation
        box_plan = self.agent._create_plan_for_goal("create a box")
        self.assertGreater(len(box_plan), 0)
        self.assertTrue(any(action["action"] == "CreateSketch" for action in box_plan))
        
        # Test circle creation
        circle_plan = self.agent._create_plan_for_goal("create a circle")
        self.assertGreater(len(circle_plan), 0)
        self.assertTrue(any(action["action"] == "DrawCircle" for action in circle_plan))
    
    async def test_run_loop(self):
        """Test the main autonomous loop."""
        self.mock_tool_executor.return_value = {
            "status": "completed",
            "message": "Tool executed successfully"
        }
        
        self.agent.start("Create a test box")
        result = await self.agent.run_loop()
        
        self.assertIn("agent_id", result)
        self.assertGreater(self.agent.iterations_completed, 0)
        self.assertGreater(len(self.agent.execution_log), 0)


class TestBasicAgent(unittest.TestCase):
    """Test cases for basic agent."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "name": "Test Basic Agent",
            "description": "Test basic agent",
            "autonomous": False
        }
        
        self.agent = BasicAgent(
            agent_id="basic_agent_123",
            name="Test Basic Agent",
            config=self.config
        )
    
    def test_agent_initialization(self):
        """Test basic agent initialization."""
        self.assertEqual(self.agent.agent_id, "basic_agent_123")
        self.assertEqual(self.agent.name, "Test Basic Agent")
    
    def test_execute_command(self):
        """Test command execution."""
        result = self.agent.execute_command("CreateSketch", {"plane": "xy"})
        
        self.assertIn("status", result)
        self.assertIn("command", result)
        self.assertEqual(result["command"], "CreateSketch")
    
    def test_get_status(self):
        """Test getting basic agent status."""
        status = self.agent.get_status()
        
        self.assertIn("agent_id", status)
        self.assertIn("name", status) 
        self.assertIn("type", status)
        self.assertEqual(status["autonomous"], False)


class TestAgentFactory(unittest.TestCase):
    """Test cases for agent factory."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / ".bmad-core"
        self.config_path.mkdir(exist_ok=True)
        
        # Create test config file
        test_config = {
            "agents": {
                "test_autonomous": {
                    "name": "Test Autonomous Agent",
                    "description": "A test autonomous agent",
                    "autonomous": True,
                    "instructions": "Test instructions",
                    "parameters": {
                        "max_iterations": 2,
                        "timeout_seconds": 10
                    }
                },
                "test_basic": {
                    "name": "Test Basic Agent",
                    "description": "A test basic agent", 
                    "autonomous": False
                }
            }
        }
        
        config_file = self.config_path / "agents.yaml"
        import yaml
        with open(config_file, 'w') as f:
            yaml.dump(test_config, f)
        
        # Patch the config parser to use our test config
        with patch('server.agent_factory.agent_config_parser') as mock_parser:
            mock_parser.get_agent.side_effect = lambda name: test_config["agents"].get(name)
            mock_parser.validate_agent_config.return_value = []
            mock_parser.get_agents.return_value = test_config["agents"]
            mock_parser.get_teams.return_value = {}
            
            self.factory = AgentFactory()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.factory.cleanup()
    
    @patch('server.agent_factory.agent_config_parser')
    def test_create_autonomous_agent(self, mock_parser):
        """Test creating an autonomous agent."""
        # Mock config
        config = {
            "name": "Test Autonomous Agent",
            "description": "A test autonomous agent",
            "autonomous": True,
            "instructions": "Test instructions",
            "parameters": {"max_iterations": 2}
        }
        
        mock_parser.get_agent.return_value = config
        mock_parser.validate_agent_config.return_value = []
        
        agent = self.factory.create_agent("test_autonomous")
        
        self.assertIsInstance(agent, AutonomousAgent)
        self.assertEqual(agent.name, "Test Autonomous Agent")
    
    @patch('server.agent_factory.agent_config_parser')
    def test_create_basic_agent(self, mock_parser):
        """Test creating a basic agent."""
        # Mock config
        config = {
            "name": "Test Basic Agent",
            "description": "A test basic agent",
            "autonomous": False
        }
        
        mock_parser.get_agent.return_value = config
        mock_parser.validate_agent_config.return_value = []
        
        agent = self.factory.create_agent("test_basic")
        
        self.assertIsInstance(agent, BasicAgent)
        self.assertEqual(agent.name, "Test Basic Agent")
    
    @patch('server.agent_factory.agent_config_parser')
    def test_get_available_agents(self, mock_parser):
        """Test getting available agents."""
        agents_config = {
            "test_agent": {
                "name": "Test Agent",
                "description": "Test description", 
                "autonomous": True
            }
        }
        teams_config = {
            "test_team": {
                "name": "Test Team",
                "description": "Test team description",
                "members": ["test_agent"]
            }
        }
        
        mock_parser.get_agents.return_value = agents_config
        mock_parser.get_teams.return_value = teams_config
        
        available = self.factory.get_available_agents()
        
        self.assertIn("agents", available)
        self.assertIn("teams", available)
        self.assertIn("test_agent", available["agents"])
        self.assertIn("test_team", available["teams"])


class TestAgentRegistry(unittest.TestCase):
    """Test cases for agent registry."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = AgentRegistry()
        
        # Create mock agents
        self.mock_agent1 = BasicAgent("agent1", "Agent 1", {"name": "Agent 1"})
        self.mock_agent2 = BasicAgent("agent2", "Agent 2", {"name": "Agent 2"})
    
    def test_register_agent(self):
        """Test registering agents."""
        self.registry.register_agent("agent1", self.mock_agent1)
        
        agent = self.registry.get_agent("agent1")
        self.assertEqual(agent, self.mock_agent1)
    
    def test_unregister_agent(self):
        """Test unregistering agents."""
        self.registry.register_agent("agent1", self.mock_agent1)
        
        removed_agent = self.registry.unregister_agent("agent1")
        self.assertEqual(removed_agent, self.mock_agent1)
        
        # Should not exist anymore
        agent = self.registry.get_agent("agent1")
        self.assertIsNone(agent)
    
    def test_list_agents(self):
        """Test listing agents."""
        self.registry.register_agent("agent1", self.mock_agent1)
        self.registry.register_agent("agent2", self.mock_agent2)
        
        agents = self.registry.list_agents()
        self.assertEqual(len(agents), 2)


if __name__ == "__main__":
    # Run async tests with asyncio
    async def run_async_tests():
        test_cases = [
            TestAutonomousAgent("test_run_loop"),
        ]
        
        for test in test_cases:
            await test.test_run_loop()
    
    # Run regular unit tests
    unittest.main(verbosity=2, exit=False)
    
    # Run async tests
    print("\nRunning async tests...")
    asyncio.run(run_async_tests())
    print("Async tests completed.")