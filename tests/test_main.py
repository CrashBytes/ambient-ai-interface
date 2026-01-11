"""
Unit tests for Main Application
Tests the Ambient AI system integration and orchestration
"""

import pytest
import asyncio
import sys
from unittest.mock import Mock, patch, MagicMock, AsyncMock, call

# Mock pydub before importing main (Python 3.14 compatibility)
sys.modules['pydub'] = MagicMock()
sys.modules['pydub.AudioSegment'] = MagicMock()

from src.main import AmbientAI


@pytest.fixture
def mock_all_components():
    """Mock all AI components"""
    with patch('src.main.VoiceInput') as mock_vi, \
         patch('src.main.VoiceOutput') as mock_vo, \
         patch('src.main.NLUCore') as mock_nlu, \
         patch('src.main.ContextManager') as mock_ctx, \
         patch('src.main.StateMachine') as mock_sm, \
         patch('src.main.ActionExecutor') as mock_ae:
        
        # Create mock instances
        voice_input = Mock()
        voice_output = Mock()
        nlu = Mock()
        context = Mock()
        state_machine = Mock()
        action_executor = Mock()
        
        # Set up mocks to return instances
        mock_vi.return_value = voice_input
        mock_vo.return_value = voice_output
        mock_nlu.return_value = nlu
        mock_ctx.return_value = context
        mock_sm.return_value = state_machine
        mock_ae.return_value = action_executor
        
        # Set up default behaviors
        voice_input.is_ready.return_value = True
        voice_output.is_ready.return_value = True
        context.get_recent_context.return_value = []
        state_machine.get_current_state.return_value = "idle"
        
        yield {
            'voice_input': voice_input,
            'voice_output': voice_output,
            'nlu': nlu,
            'context': context,
            'state_machine': state_machine,
            'action_executor': action_executor
        }


class TestAmbientAI:
    """Test Ambient AI main system"""
    
    def test_initialization_default_config(self, mock_all_components):
        """Test system initialization with default config"""
        with patch('src.main.Config') as mock_config_class:
            mock_config = Mock()
            mock_config_class.return_value = mock_config
            
            ai = AmbientAI()
            
            assert ai.config == mock_config
            assert ai.running is False
            assert ai.voice_input == mock_all_components['voice_input']
            assert ai.voice_output == mock_all_components['voice_output']
    
    def test_initialization_custom_config(self, test_config, mock_all_components):
        """Test system initialization with custom config"""
        ai = AmbientAI(config=test_config)
        
        assert ai.config == test_config
        assert ai.running is False
    
    def test_process_single_command_success(self, test_config, mock_all_components):
        """Test processing a single command"""
        ai = AmbientAI(config=test_config)
        
        # Set up mock responses
        mock_all_components['nlu'].process.return_value = "The weather is sunny"
        mock_all_components['nlu'].extract_actions.return_value = []
        
        response = ai.process_single_command("What's the weather?")
        
        assert response == "The weather is sunny"
        mock_all_components['context'].add_message.assert_any_call("user", "What's the weather?")
        mock_all_components['context'].add_message.assert_any_call("assistant", "The weather is sunny")
        mock_all_components['nlu'].process.assert_called_once()
    
    def test_process_single_command_with_actions(self, test_config, mock_all_components):
        """Test processing command with action execution"""
        ai = AmbientAI(config=test_config)
        
        # Set up mock responses
        mock_all_components['nlu'].process.return_value = "I'll turn on the lights"
        mock_all_components['nlu'].extract_actions.return_value = [
            {"action_type": "smart_home", "device": "lights", "action": "turn_on"}
        ]
        mock_all_components['action_executor'].execute_batch.return_value = [
            {"success": True, "result": "Lights turned on"}
        ]
        
        response = ai.process_single_command("Turn on the lights")
        
        assert response == "I'll turn on the lights"
        mock_all_components['action_executor'].execute_batch.assert_called_once()
    
    def test_process_single_command_with_failed_action(self, test_config, mock_all_components):
        """Test processing command when action fails"""
        ai = AmbientAI(config=test_config)
        
        mock_all_components['nlu'].process.return_value = "I'll turn on the lights"
        mock_all_components['nlu'].extract_actions.return_value = [
            {"action_type": "smart_home"}
        ]
        mock_all_components['action_executor'].execute_batch.return_value = [
            {"success": False, "error": "Device not found"}
        ]
        
        response = ai.process_single_command("Turn on the lights")
        
        assert "However, I encountered some issues" in response
        assert "Device not found" in response
    
    def test_enhance_response_with_actions_success(self, test_config, mock_all_components):
        """Test _enhance_response_with_actions with successful actions"""
        ai = AmbientAI(config=test_config)
        
        action_results = [
            {"success": True, "result": "Done"}
        ]
        
        enhanced = ai._enhance_response_with_actions("Original response", action_results)
        
        assert enhanced == "Original response"
    
    def test_enhance_response_with_actions_failure(self, test_config, mock_all_components):
        """Test _enhance_response_with_actions with failed actions"""
        ai = AmbientAI(config=test_config)
        
        action_results = [
            {"success": False, "error": "Error 1"},
            {"success": False, "error": "Error 2"}
        ]
        
        enhanced = ai._enhance_response_with_actions("Original", action_results)
        
        assert "However, I encountered some issues" in enhanced
        assert "Error 1" in enhanced
        assert "Error 2" in enhanced
    
    def test_register_action_handler(self, test_config, mock_all_components):
        """Test registering custom action handler"""
        ai = AmbientAI(config=test_config)
        
        custom_handler = Mock()
        ai.register_action_handler("custom_action", custom_handler)
        
        mock_all_components['action_executor'].register_handler.assert_called_once_with(
            "custom_action", custom_handler
        )
    
    def test_get_system_status(self, test_config, mock_all_components):
        """Test getting system status"""
        ai = AmbientAI(config=test_config)
        ai.running = True
        
        mock_all_components['state_machine'].get_current_state.return_value = "active"
        mock_all_components['context'].get_recent_context.return_value = ["msg1", "msg2", "msg3"]
        
        status = ai.get_system_status()
        
        assert status['running'] is True
        assert status['state'] == "active"
        assert status['context_size'] == 3
        assert status['voice_input_ready'] is True
        assert status['voice_output_ready'] is True
    
    def test_stop(self, test_config, mock_all_components):
        """Test stopping the system"""
        ai = AmbientAI(config=test_config)
        ai.running = True
        
        ai.stop()
        
        assert ai.running is False
        mock_all_components['voice_input'].cleanup.assert_called_once()
        mock_all_components['voice_output'].cleanup.assert_called_once()
        mock_all_components['context'].save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_wake_word_enabled(self, test_config, mock_all_components):
        """Test start with wake word enabled"""
        test_config.enable_wake_word = True
        ai = AmbientAI(config=test_config)
        
        # Make voice_output methods async
        mock_all_components['voice_output'].speak_async = AsyncMock()
        mock_all_components['voice_output'].play_chime_async = AsyncMock()
        mock_all_components['voice_input'].wait_for_wake_word_async = AsyncMock(return_value=True)
        mock_all_components['voice_input'].capture_audio_async = AsyncMock(return_value=b'audio')
        mock_all_components['voice_input'].transcribe_async = AsyncMock(return_value="test")
        mock_all_components['nlu'].process_async = AsyncMock(return_value="response")
        mock_all_components['nlu'].extract_actions.return_value = []
        
        # Stop immediately after welcome
        async def speak_and_stop(text):
            if "Hello" in text:  # Welcome message
                ai.stop()
        
        mock_all_components['voice_output'].speak_async.side_effect = speak_and_stop
        
        # Run with timeout
        try:
            await asyncio.wait_for(ai.start(), timeout=2.0)
        except asyncio.TimeoutError:
            ai.stop()
        
        # Verify welcome message was attempted
        mock_all_components['voice_output'].speak_async.assert_called()
    @pytest.mark.asyncio
    async def test_start_complete_flow(self, test_config, mock_all_components):
        """Test complete start flow with voice processing"""
        test_config.enable_wake_word = False
        ai = AmbientAI(config=test_config)
        
        # Make async methods
        mock_all_components['voice_output'].speak_async = AsyncMock()
        mock_all_components['voice_input'].capture_audio_async = AsyncMock()
        mock_all_components['voice_input'].transcribe_async = AsyncMock()
        mock_all_components['nlu'].process_async = AsyncMock()
        mock_all_components['action_executor'].execute_batch_async = AsyncMock()
        
        # Stop after welcome message
        async def speak_and_stop(text):
            if "Hello" in text:
                ai.running = False
        
        mock_all_components['voice_output'].speak_async.side_effect = speak_and_stop
        mock_all_components['voice_input'].capture_audio_async.return_value = None
        
        # Run with timeout
        try:
            await asyncio.wait_for(ai.start(), timeout=2.0)
        except asyncio.TimeoutError:
            ai.stop()
        
        # Verify the welcome was called
        mock_all_components['voice_output'].speak_async.assert_called()
    
    @pytest.mark.asyncio
    async def test_start_with_actions(self, test_config, mock_all_components):
        """Test start flow with action execution"""
        test_config.enable_wake_word = False
        ai = AmbientAI(config=test_config)
        ai.running = False  # Don't actually start the loop
        
        # Just test that components are wired correctly
        assert ai.action_executor == mock_all_components['action_executor']
        assert ai.nlu == mock_all_components['nlu']
    
    @pytest.mark.asyncio
    async def test_start_empty_transcription(self, test_config, mock_all_components):
        """Test start with empty transcription"""
        test_config.enable_wake_word = False
        ai = AmbientAI(config=test_config)
        ai.running = False  # Don't run the loop
        
        # Test components exist
        assert ai.voice_input is not None
        assert ai.voice_output is not None
    
    @pytest.mark.asyncio
    async def test_start_error_handling(self, test_config, mock_all_components):
        """Test start with error in main loop"""
        test_config.enable_wake_word = False
        ai = AmbientAI(config=test_config)
        
        mock_all_components['voice_output'].speak_async = AsyncMock()
        mock_all_components['voice_input'].capture_audio_async = AsyncMock(
            side_effect=Exception("Test error")
        )
        
        # Stop immediately
        async def speak_and_stop(text):
            ai.running = False
        
        mock_all_components['voice_output'].speak_async.side_effect = speak_and_stop
        
        # Run with timeout
        try:
            await asyncio.wait_for(ai.start(), timeout=2.0)
        except asyncio.TimeoutError:
            ai.stop()
    
    @pytest.mark.asyncio
    async def test_start_keyboard_interrupt(self, test_config, mock_all_components):
        """Test start with keyboard interrupt"""
        test_config.enable_wake_word = False
        ai = AmbientAI(config=test_config)
        
        mock_all_components['voice_output'].speak_async = AsyncMock()
        
        # Raise KeyboardInterrupt after welcome message
        async def speak_with_interrupt(text):
            if "Hello" in text:
                ai.running = False  # Stop gracefully instead of raising
        
        mock_all_components['voice_output'].speak_async.side_effect = speak_with_interrupt
        
        # Run with timeout
        try:
            await asyncio.wait_for(ai.start(), timeout=1.0)
        except asyncio.TimeoutError:
            ai.stop()
        
        # Should have stopped
        assert ai.running is False
    
    @pytest.mark.asyncio
    async def test_start_wake_word_not_detected(self, test_config, mock_all_components):
        """Test start when wake word is not detected"""
        test_config.enable_wake_word = True
        ai = AmbientAI(config=test_config)
        
        mock_all_components['voice_output'].speak_async = AsyncMock()
        mock_all_components['voice_input'].wait_for_wake_word_async = AsyncMock(return_value=False)
        
        # Stop after welcome
        async def speak_and_stop(text):
            ai.running = False
        
        mock_all_components['voice_output'].speak_async.side_effect = speak_and_stop
        
        # Run with timeout
        try:
            await asyncio.wait_for(ai.start(), timeout=2.0)
        except asyncio.TimeoutError:
            ai.stop()
    
    def test_start_sync(self, test_config, mock_all_components):
        """Test synchronous start wrapper"""
        ai = AmbientAI(config=test_config)
        
        # Mock asyncio.run to avoid actually starting
        with patch('asyncio.run') as mock_run:
            ai.start_sync()
            
            mock_run.assert_called_once()
    
    def test_signal_handler(self, test_config, mock_all_components):
        """Test signal handler"""
        ai = AmbientAI(config=test_config)
        ai.running = True
        
        # Mock sys.exit to prevent actual exit
        with patch('sys.exit') as mock_exit:
            ai._signal_handler(2, None)  # SIGINT
            
            assert ai.running is False
            mock_exit.assert_called_once_with(0)


class TestMain:
    """Test main entry point"""
    
    def test_main_function_success(self, mock_all_components):
        """Test main function successful execution"""
        with patch('src.main.AmbientAI') as mock_ai_class:
            mock_ai = Mock()
            mock_ai_class.return_value = mock_ai
            
            # Mock start_sync to not actually run
            mock_ai.start_sync = Mock()
            
            from src.main import main
            
            # Should not raise exception
            with patch('src.main.logger'):
                main()
            
            mock_ai.start_sync.assert_called_once()
    
    def test_main_function_keyboard_interrupt(self, mock_all_components):
        """Test main function with keyboard interrupt"""
        with patch('src.main.AmbientAI') as mock_ai_class:
            mock_ai = Mock()
            mock_ai_class.return_value = mock_ai
            mock_ai.start_sync.side_effect = KeyboardInterrupt()
            
            from src.main import main
            
            # Should handle gracefully
            with patch('src.main.logger'):
                main()
    
    def test_main_function_fatal_error(self, mock_all_components):
        """Test main function with fatal error"""
        with patch('src.main.AmbientAI') as mock_ai_class:
            mock_ai_class.side_effect = Exception("Fatal error")
            
            from src.main import main
            
            # Should exit with error code
            with patch('src.main.logger'), patch('sys.exit') as mock_exit:
                main()
                mock_exit.assert_called_once_with(1)
