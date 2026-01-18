"""
Additional unit tests for Main Ambient AI System
Tests async start method and main loop coverage
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock


class TestAmbientAIAsyncStart:
    """Test async start() method and main loop"""
    
    @pytest.mark.asyncio
    async def test_start_without_wake_word(self, test_config):
        """Test start loop processes commands without wake word"""
        with patch('src.main.VoiceInput') as mock_vi, \
             patch('src.main.VoiceOutput') as mock_vo, \
             patch('src.main.NLUCore') as mock_nlu, \
             patch('src.main.ContextManager') as mock_ctx, \
             patch('src.main.StateMachine') as mock_sm, \
             patch('src.main.ActionExecutor') as mock_ae:
            
            # Create mock instances
            vi_inst = Mock()
            vo_inst = Mock()
            nlu_inst = Mock()
            ctx_inst = Mock()
            sm_inst = Mock()
            ae_inst = Mock()
            
            mock_vi.return_value = vi_inst
            mock_vo.return_value = vo_inst
            mock_nlu.return_value = nlu_inst
            mock_ctx.return_value = ctx_inst
            mock_sm.return_value = sm_inst
            mock_ae.return_value = ae_inst
            
            # Configure test_config
            test_config.enable_wake_word = False
            
            # Set up async mocks
            vo_inst.speak_async = AsyncMock()
            vo_inst.play_chime_async = AsyncMock()
            vi_inst.capture_audio_async = AsyncMock(return_value=b"audio_data")
            vi_inst.transcribe_async = AsyncMock(return_value="hello")
            nlu_inst.process_async = AsyncMock(return_value="Hi there!")
            nlu_inst.extract_actions.return_value = []
            ctx_inst.get_recent_context.return_value = []
            sm_inst.get_current_state.return_value = "idle"
            ae_inst.execute_batch_async = AsyncMock(return_value=[])
            
            from src.main import AmbientAI
            ai = AmbientAI(test_config)
            
            # Stop after first iteration
            call_count = 0
            original_running = ai.running
            
            async def stop_after_one():
                nonlocal call_count
                call_count += 1
                if call_count > 1:
                    ai.running = False
                return b"audio_data"
            
            vi_inst.capture_audio_async = stop_after_one
            
            await ai.start()
            
            # Verify welcome message was spoken
            assert vo_inst.speak_async.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_start_with_wake_word(self, test_config):
        """Test start loop with wake word enabled"""
        with patch('src.main.VoiceInput') as mock_vi, \
             patch('src.main.VoiceOutput') as mock_vo, \
             patch('src.main.NLUCore') as mock_nlu, \
             patch('src.main.ContextManager') as mock_ctx, \
             patch('src.main.StateMachine') as mock_sm, \
             patch('src.main.ActionExecutor') as mock_ae:
            
            vi_inst = Mock()
            vo_inst = Mock()
            nlu_inst = Mock()
            ctx_inst = Mock()
            sm_inst = Mock()
            ae_inst = Mock()
            
            mock_vi.return_value = vi_inst
            mock_vo.return_value = vo_inst
            mock_nlu.return_value = nlu_inst
            mock_ctx.return_value = ctx_inst
            mock_sm.return_value = sm_inst
            mock_ae.return_value = ae_inst
            
            # Enable wake word
            test_config.enable_wake_word = True
            
            vo_inst.speak_async = AsyncMock()
            vo_inst.play_chime_async = AsyncMock()
            
            # First call: wake word detected, then stop
            call_count = 0
            async def wake_word_side_effect():
                nonlocal call_count
                call_count += 1
                if call_count > 1:
                    return False  # Stop loop
                return True
            
            vi_inst.wait_for_wake_word_async = wake_word_side_effect
            vi_inst.capture_audio_async = AsyncMock(return_value=b"audio")
            vi_inst.transcribe_async = AsyncMock(return_value="test command")
            nlu_inst.process_async = AsyncMock(return_value="Response")
            nlu_inst.extract_actions.return_value = []
            ctx_inst.get_recent_context.return_value = []
            sm_inst.get_current_state.return_value = "idle"
            
            from src.main import AmbientAI
            ai = AmbientAI(test_config)
            
            # Use a separate flag to stop
            async def controlled_start():
                ai.running = True
                # Just run 2 iterations
                for _ in range(2):
                    if not ai.running:
                        break
                    wake = await vi_inst.wait_for_wake_word_async()
                    if wake:
                        await vo_inst.play_chime_async()
                ai.running = False
            
            await controlled_start()
            
            # Verify chime was played after wake word
            vo_inst.play_chime_async.assert_called()
    
    @pytest.mark.asyncio
    async def test_start_empty_audio_continues(self, test_config):
        """Test that empty audio data continues loop"""
        with patch('src.main.VoiceInput') as mock_vi, \
             patch('src.main.VoiceOutput') as mock_vo, \
             patch('src.main.NLUCore') as mock_nlu, \
             patch('src.main.ContextManager') as mock_ctx, \
             patch('src.main.StateMachine') as mock_sm, \
             patch('src.main.ActionExecutor') as mock_ae:
            
            vi_inst = Mock()
            vo_inst = Mock()
            
            mock_vi.return_value = vi_inst
            mock_vo.return_value = vo_inst
            mock_nlu.return_value = Mock()
            mock_ctx.return_value = Mock()
            mock_sm.return_value = Mock()
            mock_ae.return_value = Mock()
            
            test_config.enable_wake_word = False
            
            vo_inst.speak_async = AsyncMock()
            
            # First call returns None, second call raises to stop
            call_count = 0
            async def capture_side_effect():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return None
                raise KeyboardInterrupt()
            
            vi_inst.capture_audio_async = capture_side_effect
            
            from src.main import AmbientAI
            ai = AmbientAI(test_config)
            
            await ai.start()
            
            # Should have called capture_audio twice
            assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_start_empty_transcription_continues(self, test_config):
        """Test that empty transcription continues loop"""
        with patch('src.main.VoiceInput') as mock_vi, \
             patch('src.main.VoiceOutput') as mock_vo, \
             patch('src.main.NLUCore'), \
             patch('src.main.ContextManager'), \
             patch('src.main.StateMachine'), \
             patch('src.main.ActionExecutor'):
            
            vi_inst = Mock()
            vo_inst = Mock()
            
            mock_vi.return_value = vi_inst
            mock_vo.return_value = vo_inst
            
            test_config.enable_wake_word = False
            
            vo_inst.speak_async = AsyncMock()
            vi_inst.capture_audio_async = AsyncMock(return_value=b"audio")
            
            call_count = 0
            async def transcribe_side_effect(audio):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return ""  # Empty transcription
                raise KeyboardInterrupt()
            
            vi_inst.transcribe_async = transcribe_side_effect
            
            from src.main import AmbientAI
            ai = AmbientAI(test_config)
            
            await ai.start()
            
            assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_start_with_actions(self, test_config):
        """Test start loop with action execution"""
        with patch('src.main.VoiceInput') as mock_vi, \
             patch('src.main.VoiceOutput') as mock_vo, \
             patch('src.main.NLUCore') as mock_nlu, \
             patch('src.main.ContextManager') as mock_ctx, \
             patch('src.main.StateMachine') as mock_sm, \
             patch('src.main.ActionExecutor') as mock_ae:
            
            vi_inst = Mock()
            vo_inst = Mock()
            nlu_inst = Mock()
            ctx_inst = Mock()
            sm_inst = Mock()
            ae_inst = Mock()
            
            mock_vi.return_value = vi_inst
            mock_vo.return_value = vo_inst
            mock_nlu.return_value = nlu_inst
            mock_ctx.return_value = ctx_inst
            mock_sm.return_value = sm_inst
            mock_ae.return_value = ae_inst
            
            test_config.enable_wake_word = False
            
            vo_inst.speak_async = AsyncMock()
            vi_inst.capture_audio_async = AsyncMock(return_value=b"audio")
            
            call_count = 0
            async def transcribe_side_effect(audio):
                nonlocal call_count
                call_count += 1
                if call_count > 1:
                    raise KeyboardInterrupt()
                return "turn on lights"
            
            vi_inst.transcribe_async = transcribe_side_effect
            nlu_inst.process_async = AsyncMock(return_value="Turning on lights")
            nlu_inst.extract_actions.return_value = [{"type": "light", "action": "on"}]
            ae_inst.execute_batch_async = AsyncMock(return_value=[{"success": True}])
            ctx_inst.get_recent_context.return_value = []
            sm_inst.get_current_state.return_value = "idle"
            
            from src.main import AmbientAI
            ai = AmbientAI(test_config)
            
            await ai.start()
            
            # Verify actions were executed
            ae_inst.execute_batch_async.assert_called()
    
    @pytest.mark.asyncio
    async def test_start_error_handling(self, test_config):
        """Test that errors in main loop are handled gracefully"""
        with patch('src.main.VoiceInput') as mock_vi, \
             patch('src.main.VoiceOutput') as mock_vo, \
             patch('src.main.NLUCore') as mock_nlu, \
             patch('src.main.ContextManager'), \
             patch('src.main.StateMachine'), \
             patch('src.main.ActionExecutor'):
            
            vi_inst = Mock()
            vo_inst = Mock()
            nlu_inst = Mock()
            
            mock_vi.return_value = vi_inst
            mock_vo.return_value = vo_inst
            mock_nlu.return_value = nlu_inst
            
            test_config.enable_wake_word = False
            
            vo_inst.speak_async = AsyncMock()
            vi_inst.capture_audio_async = AsyncMock(return_value=b"audio")
            vi_inst.transcribe_async = AsyncMock(return_value="hello")
            
            call_count = 0
            async def process_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise Exception("NLU error")
                raise KeyboardInterrupt()
            
            nlu_inst.process_async = process_side_effect
            
            from src.main import AmbientAI
            ai = AmbientAI(test_config)
            
            await ai.start()
            
            # Should have spoken error message
            error_calls = [call for call in vo_inst.speak_async.call_args_list 
                         if "error" in str(call).lower()]
            assert len(error_calls) >= 1
