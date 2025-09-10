#!/usr/bin/env python3
"""
Integration test for agent API endpoints.

This module contains tests for the new agent API endpoints added to main.py.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from fastapi.testclient import TestClient


class TestAgentAPI(unittest.TestCase):
    """Test cases for agent API endpoints."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures for the class."""
        # Create temporary directory for test config
        cls.temp_dir = tempfile.mkdtemp()
        cls.config_path = Path(cls.temp_dir) / ".bmad-core"
        cls.config_path.mkdir(exist_ok=True)
        
        # Create test config file
        test_config = {
            "agents": {
                "design_assistant": {
                    "name": "Design Assistant",
                    "description": "An autonomous agent that helps with CAD design tasks",
                    "autonomous": True,
                    "instructions": "Test instructions for design assistant",
                    "capabilities": ["sketch_creation", "3d_modeling"],
                    "parameters": {
                        "max_iterations": 5,
                        "timeout_seconds": 60
                    }
                },
                "sketch_helper": {
                    "name": "Sketch Helper", 
                    "description": "A basic agent for simple sketching operations",
                    "autonomous": False,
                    "instructions": "Test instructions for sketch helper",
                    "capabilities": ["sketch_creation", "basic_shapes"]
                }
            },
            "teams": {
                "cad_team": {
                    "name": "CAD Design Team",
                    "description": "A collaborative team for CAD projects",
                    "members": ["design_assistant", "sketch_helper"],
                    "workflow": []
                }
            }
        }
        
        config_file = cls.config_path / "agents.yaml"
        import yaml
        with open(config_file, 'w') as f:
            yaml.dump(test_config, f)
    
    @classmethod  
    def tearDownClass(cls):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
    
    def setUp(self):
        """Set up test fixtures for each test."""
        # Mock the agent config parser to use our test config
        self.mock_parser_patcher = patch('server.agent_factory.agent_config_parser')
        self.mock_parser = self.mock_parser_patcher.start()
        
        # Set up mock responses
        test_agents = {
            "design_assistant": {
                "name": "Design Assistant",
                "description": "An autonomous agent that helps with CAD design tasks",
                "autonomous": True,
                "instructions": "Test instructions",
                "capabilities": ["sketch_creation", "3d_modeling"],
                "parameters": {"max_iterations": 5, "timeout_seconds": 60}
            },
            "sketch_helper": {
                "name": "Sketch Helper",
                "description": "A basic agent for simple sketching operations", 
                "autonomous": False,
                "instructions": "Test instructions",
                "capabilities": ["sketch_creation", "basic_shapes"],
                "parameters": {}
            }
        }
        
        test_teams = {
            "cad_team": {
                "name": "CAD Design Team",
                "description": "A collaborative team for CAD projects",
                "members": ["design_assistant", "sketch_helper"],
                "workflow": []
            }
        }
        
        self.mock_parser.get_agents.return_value = test_agents
        self.mock_parser.get_teams.return_value = test_teams
        self.mock_parser.get_agent.side_effect = lambda name: test_agents.get(name)
        self.mock_parser.validate_agent_config.return_value = []
        
        # Import and create test client after mocking
        from main import app
        self.client = TestClient(app)
    
    def tearDown(self):
        """Clean up after each test."""
        self.mock_parser_patcher.stop()
    
    def test_list_agents_endpoint(self):
        """Test GET /api/bmad/agents endpoint."""
        response = self.client.get("/api/bmad/agents")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check response structure
        self.assertIn("agents", data)
        self.assertIn("teams", data)
        
        # Check agents data
        agents = data["agents"]
        self.assertIn("design_assistant", agents)
        self.assertIn("sketch_helper", agents)
        
        # Verify autonomous agent data
        design_agent = agents["design_assistant"]
        self.assertEqual(design_agent["name"], "Design Assistant")
        self.assertTrue(design_agent["autonomous"])
        self.assertIn("sketch_creation", design_agent["capabilities"])
        
        # Verify basic agent data
        sketch_agent = agents["sketch_helper"]
        self.assertEqual(sketch_agent["name"], "Sketch Helper")
        self.assertFalse(sketch_agent["autonomous"])
        
        # Check teams data
        teams = data["teams"]
        self.assertIn("cad_team", teams)
        cad_team = teams["cad_team"]
        self.assertEqual(len(cad_team["members"]), 2)
        self.assertIn("design_assistant", cad_team["members"])
    
    @patch('server.agent_factory.agent_factory.start_autonomous_agent')
    def test_start_agent_endpoint(self, mock_start):
        """Test POST /api/bmad/agents/{agent_name}/start endpoint."""
        # Mock successful start response
        mock_status = {
            "agent_id": "design_assistant_12345678",
            "name": "Design Assistant",
            "state": "planning",
            "current_goal": "Create a simple box",
            "iterations_completed": 0,
            "max_iterations": 5,
            "elapsed_time": 0.0,
            "timeout_seconds": 60,
            "error_message": None,
            "running": True,
            "execution_log_length": 0
        }
        mock_start.return_value = mock_status
        
        # Make request
        request_data = {
            "goal": "Create a simple box",
            "context": {"project": "test"}
        }
        response = self.client.post(
            "/api/bmad/agents/design_assistant/start",
            json=request_data
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check response structure
        self.assertIn("agent_id", data)
        self.assertIn("state", data)
        self.assertIn("current_goal", data)
        self.assertEqual(data["current_goal"], "Create a simple box")
        self.assertTrue(data["running"])
        
        # Verify the factory method was called correctly
        mock_start.assert_called_once_with(
            agent_name="design_assistant",
            goal="Create a simple box",
            context={"project": "test"}
        )
    
    @patch('server.agent_factory.agent_factory.stop_agent')
    def test_stop_agent_endpoint(self, mock_stop):
        """Test POST /api/bmad/agents/{agent_id}/stop endpoint."""
        # Mock stop response
        mock_status = {
            "agent_id": "design_assistant_12345678",
            "name": "Design Assistant",
            "state": "stopped",
            "current_goal": "Create a simple box",
            "iterations_completed": 2,
            "max_iterations": 5,
            "elapsed_time": 15.5,
            "timeout_seconds": 60,
            "error_message": None,
            "running": False,
            "execution_log_length": 6
        }
        mock_stop.return_value = mock_status
        
        # Make request
        response = self.client.post("/api/bmad/agents/design_assistant_12345678/stop")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check response
        self.assertEqual(data["agent_id"], "design_assistant_12345678") 
        self.assertEqual(data["state"], "stopped")
        self.assertFalse(data["running"])
        self.assertEqual(data["iterations_completed"], 2)
        
        # Verify the factory method was called
        mock_stop.assert_called_once_with("design_assistant_12345678")
    
    @patch('server.agent_factory.agent_factory.stop_agent')
    def test_stop_agent_not_found(self, mock_stop):
        """Test stopping non-existent agent."""
        mock_stop.return_value = None
        
        response = self.client.post("/api/bmad/agents/nonexistent_agent/stop")
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("Agent not found", data["detail"])
    
    @patch('server.agent_factory.agent_factory.list_running_agents')
    def test_list_running_agents_endpoint(self, mock_list):
        """Test GET /api/bmad/agents/running endpoint."""
        # Mock running agents
        mock_agents = [
            {
                "agent_id": "design_assistant_12345678",
                "name": "Design Assistant",
                "state": "acting",
                "current_goal": "Create a simple box",
                "iterations_completed": 1,
                "max_iterations": 5,
                "elapsed_time": 10.2,
                "timeout_seconds": 60,
                "error_message": None,
                "running": True,
                "execution_log_length": 3
            },
            {
                "agent_id": "modeling_expert_87654321",
                "name": "3D Modeling Expert",
                "state": "reporting",
                "current_goal": "Create complex geometry",
                "iterations_completed": 3,
                "max_iterations": 10,
                "elapsed_time": 25.7,
                "timeout_seconds": 300,
                "error_message": None,
                "running": True,
                "execution_log_length": 9
            }
        ]
        mock_list.return_value = mock_agents
        
        # Make request
        response = self.client.get("/api/bmad/agents/running")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check response structure
        self.assertIn("agents", data)
        agents = data["agents"]
        self.assertEqual(len(agents), 2)
        
        # Check first agent
        agent1 = agents[0]
        self.assertEqual(agent1["agent_id"], "design_assistant_12345678")
        self.assertEqual(agent1["state"], "acting")
        self.assertTrue(agent1["running"])
        
        # Check second agent
        agent2 = agents[1]
        self.assertEqual(agent2["agent_id"], "modeling_expert_87654321")
        self.assertEqual(agent2["iterations_completed"], 3)
    
    @patch('server.agent_factory.agent_factory.get_agent_status')
    def test_get_agent_status_endpoint(self, mock_get_status):
        """Test GET /api/bmad/agents/{agent_id}/status endpoint."""
        # Mock agent status
        mock_status = {
            "agent_id": "design_assistant_12345678",
            "name": "Design Assistant",
            "state": "completed",
            "current_goal": "Create a simple box",
            "iterations_completed": 3,
            "max_iterations": 5,
            "elapsed_time": 45.8,
            "timeout_seconds": 60,
            "error_message": None,
            "running": False,
            "execution_log_length": 9
        }
        mock_get_status.return_value = mock_status
        
        # Make request
        response = self.client.get("/api/bmad/agents/design_assistant_12345678/status")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check response
        self.assertEqual(data["agent_id"], "design_assistant_12345678")
        self.assertEqual(data["state"], "completed")
        self.assertFalse(data["running"])
        self.assertEqual(data["iterations_completed"], 3)
        
        # Verify the factory method was called
        mock_get_status.assert_called_once_with("design_assistant_12345678")
    
    @patch('server.agent_factory.agent_factory.get_agent_status')
    def test_get_agent_status_not_found(self, mock_get_status):
        """Test getting status of non-existent agent."""
        mock_get_status.return_value = None
        
        response = self.client.get("/api/bmad/agents/nonexistent_agent/status")
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("Agent not found", data["detail"])
    
    def test_invalid_agent_name_start(self):
        """Test starting agent with invalid name."""
        request_data = {"goal": "Create something"}
        response = self.client.post(
            "/api/bmad/agents/nonexistent_agent/start",
            json=request_data
        )
        
        # Should get 400 or 500 error due to invalid agent name
        self.assertIn(response.status_code, [400, 500])


if __name__ == "__main__":
    # Install fastapi test client if needed
    try:
        from fastapi.testclient import TestClient
    except ImportError:
        print("Installing httpx for FastAPI testing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
        from fastapi.testclient import TestClient
    
    unittest.main(verbosity=2)