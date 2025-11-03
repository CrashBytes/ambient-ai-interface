"""
State Machine - System State Management
Tracks system state and handles state transitions
"""

from enum import Enum
from typing import Dict, Any, Optional, Callable

from src.utils.logging import get_logger
from src.utils.config import Config

logger = get_logger(__name__)


class SystemState(Enum):
    """System states"""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    RESPONDING = "responding"
    EXECUTING_ACTION = "executing_action"
    ERROR = "error"


class StateMachine:
    """
    State Machine for Ambient AI System
    
    Manages system state transitions and triggers appropriate callbacks
    """
    
    def __init__(self, config: Config):
        """
        Initialize state machine
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.current_state = SystemState.IDLE
        self.previous_state = None
        self.state_data: Dict[str, Any] = {}
        
        # State transition callbacks
        self.state_callbacks: Dict[SystemState, list] = {
            state: [] for state in SystemState
        }
        
        logger.info("State machine initialized")
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current state information"""
        return {
            "state": self.current_state.value,
            "previous_state": self.previous_state.value if self.previous_state else None,
            "data": self.state_data.copy()
        }
    
    def transition_to(self, new_state: SystemState, data: Optional[Dict[str, Any]] = None):
        """
        Transition to a new state
        
        Args:
            new_state: Target state
            data: Optional state data
        """
        if new_state == self.current_state:
            return
        
        logger.info(f"State transition: {self.current_state.value} -> {new_state.value}")
        
        # Store previous state
        self.previous_state = self.current_state
        
        # Update state
        self.current_state = new_state
        
        # Update state data
        if data:
            self.state_data.update(data)
        
        # Execute callbacks
        self._execute_callbacks(new_state)
    
    def set_state_data(self, key: str, value: Any):
        """Set state data"""
        self.state_data[key] = value
    
    def get_state_data(self, key: str, default: Any = None) -> Any:
        """Get state data"""
        return self.state_data.get(key, default)
    
    def clear_state_data(self):
        """Clear all state data"""
        self.state_data.clear()
    
    def register_callback(self, state: SystemState, callback: Callable):
        """
        Register callback for state entry
        
        Args:
            state: State to monitor
            callback: Callback function (receives state_data dict)
        """
        self.state_callbacks[state].append(callback)
        logger.debug(f"Registered callback for state: {state.value}")
    
    def _execute_callbacks(self, state: SystemState):
        """Execute registered callbacks for a state"""
        callbacks = self.state_callbacks.get(state, [])
        for callback in callbacks:
            try:
                callback(self.state_data)
            except Exception as e:
                logger.error(f"Callback error for state {state.value}: {e}", exc_info=True)
    
    def process_input(self, user_input: str):
        """
        Process user input and update state accordingly
        
        Args:
            user_input: User's text input
        """
        # Simple state transitions based on input
        input_lower = user_input.lower()
        
        # Check for system commands
        if "stop" in input_lower or "cancel" in input_lower:
            self.transition_to(SystemState.IDLE)
        elif "help" in input_lower:
            self.set_state_data("help_requested", True)
        
        # Store input in state data
        self.set_state_data("last_input", user_input)
    
    def is_idle(self) -> bool:
        """Check if system is idle"""
        return self.current_state == SystemState.IDLE
    
    def is_busy(self) -> bool:
        """Check if system is busy processing"""
        return self.current_state in [
            SystemState.PROCESSING,
            SystemState.EXECUTING_ACTION
        ]
    
    def set_error(self, error_message: str):
        """Set error state"""
        self.transition_to(
            SystemState.ERROR,
            {"error_message": error_message}
        )
    
    def clear_error(self):
        """Clear error state"""
        if self.current_state == SystemState.ERROR:
            self.transition_to(SystemState.IDLE)
            self.state_data.pop("error_message", None)
