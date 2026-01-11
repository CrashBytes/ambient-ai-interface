"""
Unit tests for Main Ambient AI System  
Tests system initialization, orchestration, and integration
"""

import pytest
import signal
import sys
from unittest.mock import Mock, patch, MagicMock, call
import numpy as np


class TestAmbientAIInitialization:
    """Test Ambient AI system initialization"""
    
    def test_initialization(self, test_config):
        """Test basic initialization"""
        with patch('src.main.VoiceInput'), \
             patch('src.main.VoiceOutput'), \
             patch('src.main.NLUCore'), \
             patch('src.main.ContextManager'), \
             patch('src.main.StateMachine'), \
             patch('src.main.ActionExecutor'):
            
            from src.main import AmbientAI
            ai = AmbientAI(test_config)
            
            assert ai.config == test_config
            assert ai.running is False
    
    def test_initialization_with_default_config(self):
        """Test initialization with default config"""
        with patch('src.main.VoiceInput'), \
             patch('src.main.VoiceOutput'), \
             patch('src.main.NLUCore'), \
             patch('src.main.ContextManager'), \
             patch('src.main.StateMachine'), \
             patch('src.main.ActionExecutor'), \
             patch('src.main.Config') as mock_config:
            
            mock_config.return_value = Mock()
            from src.main import AmbientAI
            ai = AmbientAI()
            
            mock_config.assert_called_once()


class TestAmbientAISignalHandling:
    """Test signal handling and shutdown"""
    
    def test_signal_handler(self, test_config):
        """Test signal handler triggers shutdown"""
        with patch('src.main.VoiceInput'), \
             patch('src.main.VoiceOutput'), \
             patch('src.main.NLUCore'), \
             patch('src.main.ContextManager'), \
             patch('src.main.StateMachine'), \
             patch('src.main.ActionExecutor'):
            
            from src.main import AmbientAI
            ai = AmbientAI(test_config)
            
            with patch.object(ai, 'stop') as mock_stop:
                with pytest.raises(SystemExit):
                    ai._signal_handler(signal.SIGINT, None)
                
                mock_stop.assert_called_once()
    
    def test_stop_method(self, test_config):
        """Test stop method cleans up resources"""
        with patch('src.main.VoiceInput') as mock_vi, \
             patch('src.main.VoiceOutput') as mock_vo, \
             patch('src.main.NLUCore'), \
             patch('src.main.ContextManager') as mock_ctx, \
             patch('src.main.StateMachine'), \
             patch('src.main.ActionExecutor'):
            
            # Create mock instances
            vi_inst = Mock()
            vo_inst = Mock()
            ctx_inst = Mock()
            mock_vi.return_value = vi_inst
            mock_vo.return_value = vo_inst
            mock_ctx.return_value = ctx_inst
            
            from src.main import AmbientAI
            ai = AmbientAI(test_config)
            ai.running = True
            
            ai.stop()
            
            assert ai.running is False
            vi_inst.cleanup.assert_called_once()
            vo_inst.cleanup.assert_called_once()
            ctx_inst.save.assert_called_once()


class TestAmbientAISyncMethods:
    """Test synchronous methods"""
    
    def test_start_sync(self, test_config):
        """Test synchronous start wrapper"""
        with patch('src.main.VoiceInput'), \
             patch('src.main.VoiceOutput'), \
             patch('src.main.NLUCore'), \
             patch('src.main.ContextManager'), \
             patch('src.main.StateMachine'), \
             patch('src.main.ActionExecutor'):
            
            from src.main import AmbientAI
            ai = AmbientAI(test_config)
            
            # Mock asyncio.run to avoid actually running
            with patch('asyncio.run') as mock_run:
                ai.start_sync()
                mock_run.assert_called_once()
    
    def test_process_single_command(self, test_config):
        """Test process_single_command method"""
        with patch('src.main.VoiceInput'), \
             patch('src.main.VoiceOutput'), \
             patch('src.main.NLUCore') as mock_nlu, \
             patch('src.main.ContextManager') as mock_ctx, \
             patch('src.main.StateMachine') as mock_sm, \
             patch('src.main.ActionExecutor') as mock_ae:
            
            nlu_inst = Mock()
            ctx_inst = Mock()
            sm_inst = Mock()
            ae_inst = Mock()
            
            mock_nlu.return_value = nlu_inst
            mock_ctx.return_value = ctx_inst
            mock_sm.return_value = sm_inst
            mock_ae.return_value = ae_inst
            
            nlu_inst.process.return_value = "Hello there"
            nlu_inst.extract_actions.return_value = []
            ctx_inst.get_recent_context.return_value = []
            sm_inst.get_current_state.return_value = "idle"
            
            from src.main import AmbientAI
            ai = AmbientAI(test_config)
            
            response = ai.process_single_command("hello")
            
            assert response == "Hello there"
            ctx_inst.add_message.assert_any_call("user", "hello")
            ctx_inst.add_message.assert_any_call("assistant", "Hello there")
    
    def test_process_single_command_with_actions(self, test_config):
        """Test process_single_command with action execution"""
        with patch('src.main.VoiceInput'), \
             patch('src.main.VoiceOutput'), \
             patch('src.main.NLUCore') as mock_nlu, \
             patch('src.main.ContextManager') as mock_ctx, \
             patch('src.main.StateMachine') as mock_sm, \
             patch('src.main.ActionExecutor') as mock_ae:
            
            nlu_inst = Mock()
            ctx_inst = Mock()
            sm_inst = Mock()
            ae_inst = Mock()
            
            mock_nlu.return_value = nlu_inst
            mock_ctx.return_value = ctx_inst
            mock_sm.return_value = sm_inst
            mock_ae.return_value = ae_inst
            
            nlu_inst.process.return_value = "Turning on lights"
            nlu_inst.extract_actions.return_value = [{"type": "light", "action": "on"}]
            ae_inst.execute_batch.return_value = [{"success": True}]
            ctx_inst.get_recent_context.return_value = []
            sm_inst.get_current_state.return_value = "idle"
            
            from src.main import AmbientAI
            ai = AmbientAI(test_config)
            
            response = ai.process_single_command("turn on lights")
            
            assert "Turning on lights" in response
            ae_inst.execute_batch.assert_called_once()
    
    def test_enhance_response_with_actions_success(self, test_config):
        """Test _enhance_response_with_actions with successful actions"""
        with patch('src.main.VoiceInput'), \
             patch('src.main.VoiceOutput'), \
             patch('src.main.NLUCore'), \
             patch('src.main.ContextManager'), \
             patch('src.main.StateMachine'), \
             patch('src.main.ActionExecutor'):
            
            from src.main import AmbientAI
            ai = AmbientAI(test_config)
            
            response = "Task completed"
            action_results = [{"success": True}]
            
            enhanced = ai._enhance_response_with_actions(response, action_results)
            
            assert enhanced == "Task completed"
    
    def test_enhance_response_with_actions_failure(self, test_config):
        """Test _enhance_response_with_actions with failed actions"""
        with patch('src.main.VoiceInput'), \
             patch('src.main.VoiceOutput'), \
             patch('src.main.NLUCore'), \
             patch('src.main.ContextManager'), \
             patch('src.main.StateMachine'), \
             patch('src.main.ActionExecutor'):
            
            from src.main import AmbientAI
            ai = AmbientAI(test_config)
            
            response = "Attempting task"
            action_results = [
                {"success": False, "error": "Device not found"},
                {"success": False, "error": "Timeout"}
            ]
            
            enhanced = ai._enhance_response_with_actions(response, action_results)
            
            assert "Attempting task" in enhanced
            assert "Device not found" in enhanced
            assert "Timeout" in enhanced
    
    def test_register_action_handler(self, test_config):
        """Test register_action_handler method"""
        with patch('src.main.VoiceInput'), \
             patch('src.main.VoiceOutput'), \
             patch('src.main.NLUCore'), \
             patch('src.main.ContextManager'), \
             patch('src.main.StateMachine'), \
             patch('src.main.ActionExecutor') as mock_ae:
            
            ae_inst = Mock()
            mock_ae.return_value = ae_inst
            
            from src.main import AmbientAI
            ai = AmbientAI(test_config)
            
            def custom_handler(action):
                return {"success": True}
            
            ai.register_action_handler("custom_action", custom_handler)
            
            ae_inst.register_handler.assert_called_once_with("custom_action", custom_handler)
    
    def test_get_system_status(self, test_config):
        """Test get_system_status method"""
        with patch('src.main.VoiceInput') as mock_vi, \
             patch('src.main.VoiceOutput') as mock_vo, \
             patch('src.main.NLUCore'), \
             patch('src.main.ContextManager') as mock_ctx, \
             patch('src.main.StateMachine') as mock_sm, \
             patch('src.main.ActionExecutor'):
            
            vi_inst = Mock()
            vo_inst = Mock()
            ctx_inst = Mock()
            sm_inst = Mock()
            
            mock_vi.return_value = vi_inst
            mock_vo.return_value = vo_inst
            mock_ctx.return_value = ctx_inst
            mock_sm.return_value = sm_inst
            
            vi_inst.is_ready.return_value = True
            vo_inst.is_ready.return_value = True
            ctx_inst.get_recent_context.return_value = [1, 2, 3]
            sm_inst.get_current_state.return_value = "active"
            
            from src.main import AmbientAI
            ai = AmbientAI(test_config)
            ai.running = True
            
            status = ai.get_system_status()
            
            assert status["running"] is True
            assert status["state"] == "active"
            assert status["context_size"] == 3
            assert status["voice_input_ready"] is True
            assert status["voice_output_ready"] is True


class TestMainFunction:
    """Test main() entry point"""
    
    def test_main_function_success(self):
        """Test main function runs successfully"""
        with patch('src.main.AmbientAI') as mock_ai_class:
            mock_ai = Mock()
            mock_ai_class.return_value = mock_ai
            
            # Mock to exit quickly
            mock_ai.start_sync.side_effect = KeyboardInterrupt()
            
            from src.main import main
            
            # Should handle KeyboardInterrupt gracefully
            main()
            
            mock_ai_class.assert_called_once()
            mock_ai.start_sync.assert_called_once()
    
    def test_main_function_fatal_error(self):
        """Test main function handles fatal errors"""
        with patch('src.main.AmbientAI') as mock_ai_class:
            mock_ai_class.side_effect = Exception("Fatal error")
            
            from src.main import main
            
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 1
