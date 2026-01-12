"""
Additional tests for action_executor.py to improve coverage
Focuses on edge cases and uncovered branches
"""

import pytest
from src.action_executor import ActionExecutor


class TestActionExecutorCoverage:
    """Additional tests to improve action executor coverage"""
    
    # Smart home coverage
    
    def test_handle_smart_home_unknown_action(self, test_config):
        """Test smart home with unknown action type (else branch)"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "smart_home",
            "parameters": {
                "device": "doorbell",
                "location": "front door",
                "action": "ring"  # Not on/off/set
            }
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "Executed" in result["result"]
        assert "ring" in result["result"]
        assert "doorbell" in result["result"]
    
    def test_handle_smart_home_set_without_value(self, test_config):
        """Test smart home set action without value (falls through to else)"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "smart_home",
            "parameters": {
                "device": "blinds",
                "location": "bedroom",
                "action": "set"
                # No value provided
            }
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        # Should fall through to else branch since value is None
        assert "Executed" in result["result"]
    
    # Information coverage
    
    def test_handle_information_unknown_type(self, test_config):
        """Test information with unknown type (else branch)"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "information",
            "parameters": {
                "type": "traffic",  # Not weather/news/time
                "location": "downtown"
            }
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "Retrieved information" in result["result"]
        assert "traffic" in result["result"]
    
    # Reminder coverage
    
    def test_handle_reminder_cancel(self, test_config):
        """Test reminder cancel action"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "reminder",
            "parameters": {
                "action": "cancel",
                "message": "meeting"
            }
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "cancelled" in result["result"].lower()
    
    def test_handle_reminder_unknown_action(self, test_config):
        """Test reminder with unknown action (else branch)"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "reminder",
            "parameters": {
                "action": "snooze",  # Not set/list/cancel
                "time": "10 minutes"
            }
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "Reminder action completed" in result["result"]
    
    # Media coverage
    
    def test_handle_media_play_without_title(self, test_config):
        """Test media play without specific title"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "media",
            "parameters": {
                "action": "play",
                "type": "podcast"
                # No title
            }
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "Playing" in result["result"]
        assert "podcast" in result["result"]
    
    def test_handle_media_stop(self, test_config):
        """Test media stop action"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "media",
            "parameters": {"action": "stop"}
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "stopped" in result["result"].lower()
    
    def test_handle_media_previous(self, test_config):
        """Test media previous action"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "media",
            "parameters": {"action": "previous"}
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "previous" in result["result"].lower()
    
    def test_handle_media_unknown_action(self, test_config):
        """Test media with unknown action (else branch)"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "media",
            "parameters": {
                "action": "shuffle",  # Not play/pause/stop/next/previous
                "type": "playlist"
            }
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "Media action completed" in result["result"]
    
    # Communication coverage
    
    def test_handle_communication_email(self, test_config):
        """Test communication email action"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "communication",
            "parameters": {
                "action": "email",
                "recipient": "boss@company.com",
                "message": "Status update"
            }
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "Email sent" in result["result"]
        assert "boss@company.com" in result["result"]
    
    def test_handle_communication_unknown_action(self, test_config):
        """Test communication with unknown action (else branch)"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "communication",
            "parameters": {
                "action": "video_call",  # Not send_message/call/email
                "recipient": "Team"
            }
        }
        
        result = executor.execute(action)
        
        assert result["success"] is True
        assert "Communication action completed" in result["result"]
    
    # Async handler tests
    
    @pytest.mark.asyncio
    async def test_execute_async_unknown_action_type(self, test_config):
        """Test async execution with unknown action type"""
        executor = ActionExecutor(test_config)
        
        action = {
            "action_type": "nonexistent_async",
            "parameters": {}
        }
        
        result = await executor.execute_async(action)
        
        assert result["success"] is False
        assert "Unknown action type" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_async_handler_exception(self, test_config):
        """Test async execution when handler raises exception"""
        executor = ActionExecutor(test_config)
        
        async def failing_async_handler(params):
            raise RuntimeError("Async test error")
        
        executor.register_handler("failing_async", failing_async_handler)
        
        action = {"action_type": "failing_async", "parameters": {}}
        result = await executor.execute_async(action)
        
        assert result["success"] is False
        assert "Async test error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_async_with_sync_handler(self, test_config):
        """Test async execution with synchronous handler (uses asyncio.to_thread)"""
        executor = ActionExecutor(test_config)
        
        # Use one of the default sync handlers
        action = {
            "action_type": "search",
            "parameters": {"query": "async test"}
        }
        
        result = await executor.execute_async(action)
        
        assert result["success"] is True
        assert "found" in result["result"].lower()
    
    # Edge cases for execute_batch
    
    def test_execute_batch_empty(self, test_config):
        """Test batch execution with empty list"""
        executor = ActionExecutor(test_config)
        
        results = executor.execute_batch([])
        
        assert results == []
    
    def test_execute_batch_with_failures(self, test_config):
        """Test batch execution with some failures"""
        executor = ActionExecutor(test_config)
        
        actions = [
            {"action_type": "smart_home", "parameters": {"action": "on"}},
            {"action_type": "invalid_type", "parameters": {}},
            {"action_type": "media", "parameters": {"action": "play"}}
        ]
        
        results = executor.execute_batch(actions)
        
        assert len(results) == 3
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert results[2]["success"] is True
    
    @pytest.mark.asyncio
    async def test_execute_batch_async_empty(self, test_config):
        """Test async batch execution with empty list"""
        executor = ActionExecutor(test_config)
        
        results = await executor.execute_batch_async([])
        
        assert results == []
    
    @pytest.mark.asyncio
    async def test_execute_batch_async_with_failures(self, test_config):
        """Test async batch execution with some failures"""
        executor = ActionExecutor(test_config)
        
        actions = [
            {"action_type": "information", "parameters": {"type": "weather"}},
            {"action_type": "unknown_action", "parameters": {}},
            {"action_type": "reminder", "parameters": {"action": "list"}}
        ]
        
        results = await executor.execute_batch_async(actions)
        
        assert len(results) == 3
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert results[2]["success"] is True
