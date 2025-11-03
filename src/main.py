"""
Ambient AI System - Main Entry Point
A voice-first, screenless AI interface that processes natural language commands.
"""

import asyncio
import signal
import sys
from typing import Optional

from dotenv import load_dotenv

from src.voice_input import VoiceInput
from src.voice_output import VoiceOutput
from src.nlu_core import NLUCore
from src.context_manager import ContextManager
from src.state_machine import StateMachine
from src.action_executor import ActionExecutor
from src.utils.logging import setup_logging, get_logger
from src.utils.config import Config

# Load environment variables
load_dotenv()

# Set up logging
setup_logging()
logger = get_logger(__name__)


class AmbientAI:
    """
    Main Ambient AI System
    
    Orchestrates all components to provide a seamless voice-first experience:
    - Voice input (speech-to-text)
    - Natural language understanding
    - Context management
    - Action execution
    - Voice output (text-to-speech)
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the Ambient AI system
        
        Args:
            config: Optional configuration object. If None, loads from environment.
        """
        self.config = config or Config()
        self.running = False
        
        # Initialize components
        logger.info("Initializing Ambient AI components...")
        
        self.voice_input = VoiceInput(self.config)
        self.voice_output = VoiceOutput(self.config)
        self.nlu = NLUCore(self.config)
        self.context = ContextManager(self.config)
        self.state_machine = StateMachine(self.config)
        self.action_executor = ActionExecutor(self.config)
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("Ambient AI system initialized successfully")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.stop()
        sys.exit(0)
    
    async def start(self):
        """Start the Ambient AI system in continuous listening mode"""
        self.running = True
        logger.info("Starting Ambient AI system...")
        
        # Welcome message
        await self.voice_output.speak_async(
            "Hello! Ambient AI is now active. How can I help you today?"
        )
        
        # Main processing loop
        while self.running:
            try:
                # Listen for wake word or continuous input
                if self.config.enable_wake_word:
                    wake_detected = await self.voice_input.wait_for_wake_word_async()
                    if not wake_detected:
                        continue
                    
                    # Acknowledge wake word
                    await self.voice_output.play_chime_async()
                
                # Capture voice input
                logger.info("Listening for command...")
                audio_data = await self.voice_input.capture_audio_async()
                
                if not audio_data:
                    continue
                
                # Convert speech to text
                text = await self.voice_input.transcribe_async(audio_data)
                if not text or text.strip() == "":
                    continue
                
                logger.info(f"User said: {text}")
                
                # Add to context
                self.context.add_message("user", text)
                
                # Update state machine
                self.state_machine.process_input(text)
                
                # Process with NLU
                conversation_history = self.context.get_recent_context()
                response = await self.nlu.process_async(
                    text,
                    context=conversation_history,
                    state=self.state_machine.get_current_state()
                )
                
                logger.info(f"Assistant response: {response}")
                
                # Execute any actions
                actions = self.nlu.extract_actions(response)
                if actions:
                    action_results = await self.action_executor.execute_batch_async(actions)
                    
                    # Incorporate action results into response
                    if action_results:
                        response = self._enhance_response_with_actions(response, action_results)
                
                # Add response to context
                self.context.add_message("assistant", response)
                
                # Speak response
                await self.voice_output.speak_async(response)
                
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                await self.voice_output.speak_async(
                    "I'm sorry, I encountered an error. Please try again."
                )
                continue
    
    def start_sync(self):
        """Synchronous wrapper for start() method"""
        asyncio.run(self.start())
    
    def stop(self):
        """Stop the Ambient AI system"""
        logger.info("Stopping Ambient AI system...")
        self.running = False
        
        # Clean up resources
        self.voice_input.cleanup()
        self.voice_output.cleanup()
        self.context.save()
        
        logger.info("Ambient AI system stopped")
    
    def process_single_command(self, text: str) -> str:
        """
        Process a single text command (useful for testing)
        
        Args:
            text: The command text
            
        Returns:
            The response text
        """
        # Add to context
        self.context.add_message("user", text)
        
        # Process with NLU
        conversation_history = self.context.get_recent_context()
        response = self.nlu.process(
            text,
            context=conversation_history,
            state=self.state_machine.get_current_state()
        )
        
        # Execute actions
        actions = self.nlu.extract_actions(response)
        if actions:
            action_results = self.action_executor.execute_batch(actions)
            if action_results:
                response = self._enhance_response_with_actions(response, action_results)
        
        # Add response to context
        self.context.add_message("assistant", response)
        
        return response
    
    def _enhance_response_with_actions(self, response: str, action_results: list) -> str:
        """Enhance response text with action execution results"""
        # If actions were successful, keep original response
        # If actions failed, append error information
        
        failed_actions = [r for r in action_results if not r.get('success')]
        if failed_actions:
            errors = ", ".join([r.get('error', 'unknown error') for r in failed_actions])
            response += f" However, I encountered some issues: {errors}"
        
        return response
    
    def register_action_handler(self, action_type: str, handler):
        """Register a custom action handler"""
        self.action_executor.register_handler(action_type, handler)
    
    def get_system_status(self) -> dict:
        """Get current system status"""
        return {
            "running": self.running,
            "state": self.state_machine.get_current_state(),
            "context_size": len(self.context.get_recent_context()),
            "voice_input_ready": self.voice_input.is_ready(),
            "voice_output_ready": self.voice_output.is_ready(),
        }


def main():
    """Main entry point"""
    try:
        # Initialize system
        ai = AmbientAI()
        
        # Start in continuous mode
        logger.info("=" * 60)
        logger.info("Ambient AI Voice-First Interface")
        logger.info("=" * 60)
        logger.info("Press Ctrl+C to stop")
        logger.info("")
        
        ai.start_sync()
        
    except KeyboardInterrupt:
        logger.info("\nShutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Goodbye!")


if __name__ == "__main__":
    main()
