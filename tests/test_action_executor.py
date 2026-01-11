"""
Unit tests for Action Executor
Tests action execution, handler registration, and default handlers
"""

import pytest
from unittest.mock import Mock, patch
from src.action_executor import ActionExecutor


class TestActionExecutor:
    """Test action executor functionality"""
    
    def test_initialization(self, test_config):
        """Test action executor initialization"""
        executor = ActionExecutor(test_config)
        
        assert executor.config == test_config
        assert isinstance(executor.handlers, dict)
        # Check default handlers registered
        assert "smart_home" in executor.handlers
        assert "information" in executor.handlers
        assert "reminder" in executor.handlers
        assert "media" in executor.handlers
        assert "communication" in executor.handlers
        assert "search" in executor.handlers
    
    def test_register_handler(self, test_config):
        """Test custom handler registration"""
        executor = ActionExecutor(test_config)
        
        def custom_handler(params):
            return "custom result"
        
        executor.register_handler("custom", custom_handler)
        
        assert "custom" in executor.handlers
        assert executor.handlers["custom"] == custom_handler
    
    def test_execute_success(self, test_config):
        """Test successful action execution"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "smart_home",
            "parameters": {
                "device": "lights",
                "location": "bedroom",
                "action": "on"
            }
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert result["action_type"] == "smart_home"
        assert "result" in result
    
    def test_execute_no_action_type(self, test_config):
        """Test execution with missing action_type"""
        executor = ActionExecutor(test_config)
        
        action = {"parameters": {}}
        result = executor.execute(action)
        
        assert result["success"] is False
        assert "error" in result
        assert "No action_type" in result["error"]
    
    def test_execute_unknown_action_type(self, test_config):
        """Test execution with unknown action type"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "nonexistent",
            "parameters": {}
        }
        
        result = executor.execute(action)
        
        assert result["success"] is False
        assert "Unknown action type" in result["error"]
    
    def test_execute_handler_exception(self, test_config):
        """Test execution when handler raises exception"""
        executor = ActionExecutor(test_config)
        
        def failing_handler(params):
            raise ValueError("Test error")
        
        executor.register_handler("failing", failing_handler)
        
        action = {"action_type": "failing", "parameters": {}}
        result = executor.execute(action)
        
        assert result["success"] is False
        assert "error" in result
        assert "Test error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_async_success(self, test_config):
        """Test async action execution"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "information",
            "parameters": {"type": "weather"}
        }
        
        result = await executor.execute_async(action)
        
        assert result["success"] is True
        assert result["action_type"] == "information"
    
    @pytest.mark.asyncio
    async def test_execute_async_with_async_handler(self, test_config):
        """Test async execution with async handler"""
        executor = ActionExecutor(test_config)
        
        async def async_handler(params):
            return "async result"
        
        executor.register_handler("async_test", async_handler)
        
        action = {"action_type": "async_test", "parameters": {}}
        result = await executor.execute_async(action)
        
        assert result["success"] is True
        assert result["result"] == "async result"
    
    @pytest.mark.asyncio
    async def test_execute_async_no_action_type(self, test_config):
        """Test async execution with missing action_type"""
        executor = ActionExecutor(test_config)
        
        action = {"parameters": {}}
        result = await executor.execute_async(action)
        
        assert result["success"] is False
        assert "No action_type" in result["error"]
    
    def test_execute_batch(self, test_config):
        """Test batch action execution"""
        executor = ActionExecutor(test_config)
        
        actions = [
            {"action_type": "smart_home", "parameters": {"device": "lights", "action": "on"}},
            {"action_type": "information", "parameters": {"type": "weather"}},
            {"action_type": "media", "parameters": {"action": "play"}}
        ]
        
        results = executor.execute_batch(actions)
        
        assert len(results) == 3
        assert all(r["success"] for r in results)
    
    @pytest.mark.asyncio
    async def test_execute_batch_async(self, test_config):
        """Test async batch execution"""
        executor = ActionExecutor(test_config)
        
        actions = [
            {"action_type": "smart_home", "parameters": {"device": "lights", "action": "on"}},
            {"action_type": "information", "parameters": {"type": "time"}}
        ]
        
        results = await executor.execute_batch_async(actions)
        
        assert len(results) == 2
        assert all(r["success"] for r in results)
    
    # Test default handlers
    
    def test_handle_smart_home_turn_on(self, test_config):
        """Test smart home turn on"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "smart_home",
            "parameters": {
                "device": "lights",
                "location": "kitchen",
                "action": "on"
            }
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "Turned on" in result["result"]
        assert "lights" in result["result"]
    
    def test_handle_smart_home_turn_off(self, test_config):
        """Test smart home turn off"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "smart_home",
            "parameters": {
                "device": "thermostat",
                "location": "bedroom",
                "action": "off"
            }
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "Turned off" in result["result"]
    
    def test_handle_smart_home_set_value(self, test_config):
        """Test smart home set value"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "smart_home",
            "parameters": {
                "device": "thermostat",
                "location": "living room",
                "action": "set",
                "value": "72"
            }
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "Set" in result["result"]
        assert "72" in result["result"]
    
    def test_handle_information_weather(self, test_config):
        """Test information retrieval - weather"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "information",
            "parameters": {"type": "weather"}
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "weather" in result["result"].lower()
    
    def test_handle_information_news(self, test_config):
        """Test information retrieval - news"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "information",
            "parameters": {"type": "news"}
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "news" in result["result"].lower()
    
    def test_handle_information_time(self, test_config):
        """Test information retrieval - time"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "information",
            "parameters": {"type": "time"}
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "time" in result["result"].lower()
    
    def test_handle_reminder_set(self, test_config):
        """Test reminder set"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "reminder",
            "parameters": {
                "action": "set",
                "time": "tomorrow",
                "message": "to call mom"
            }
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "remind" in result["result"].lower()
    
    def test_handle_reminder_list(self, test_config):
        """Test reminder list"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "reminder",
            "parameters": {"action": "list"}
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "reminders" in result["result"].lower()
    
    def test_handle_media_play(self, test_config):
        """Test media play"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "media",
            "parameters": {
                "action": "play",
                "title": "Favorite Song"
            }
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "Playing" in result["result"]
    
    def test_handle_media_pause(self, test_config):
        """Test media pause"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "media",
            "parameters": {"action": "pause"}
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "paused" in result["result"].lower()
    
    def test_handle_media_next(self, test_config):
        """Test media next"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "media",
            "parameters": {"action": "next"}
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "next" in result["result"].lower()
    
    def test_handle_communication_message(self, test_config):
        """Test communication - send message"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "communication",
            "parameters": {
                "action": "send_message",
                "recipient": "John",
                "message": "Hello"
            }
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "Message sent" in result["result"]
    
    def test_handle_communication_call(self, test_config):
        """Test communication - call"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "communication",
            "parameters": {
                "action": "call",
                "recipient": "Jane"
            }
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "Calling" in result["result"]
    
    def test_handle_search(self, test_config):
        """Test search action"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "search",
            "parameters": {"query": "python tutorials"}
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "found" in result["result"].lower()
