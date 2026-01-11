"""
Unit tests for State Machine
Tests system state management and transitions
"""

import pytest
from src.state_machine import StateMachine, SystemState


class TestStateMachine:
    """Test state machine functionality"""
    
    def test_initialization(self, test_config):
        """Test state machine initialization"""
        sm = StateMachine(test_config)
        
        assert sm.current_state == SystemState.IDLE
        assert sm.previous_state is None
        assert len(sm.state_data) == 0
    
    def test_get_current_state_initial(self, test_config):
        """Test getting initial state"""
        sm = StateMachine(test_config)
        state = sm.get_current_state()
        
        assert state["state"] == "idle"
        assert state["previous_state"] is None
        assert state["data"] == {}
    
    def test_transition_to_new_state(self, test_config):
        """Test transitioning to a new state"""
        sm = StateMachine(test_config)
        sm.transition_to(SystemState.LISTENING)
        
        assert sm.current_state == SystemState.LISTENING
        assert sm.previous_state == SystemState.IDLE
    
    def test_transition_with_data(self, test_config):
        """Test state transition with data"""
        sm = StateMachine(test_config)
        data = {"user_id": "12345", "intent": "greeting"}
        
        sm.transition_to(SystemState.PROCESSING, data=data)
        
        assert sm.current_state == SystemState.PROCESSING
        assert sm.state_data["user_id"] == "12345"
        assert sm.state_data["intent"] == "greeting"
    
    def test_transition_to_same_state(self, test_config):
        """Test transitioning to same state does nothing"""
        sm = StateMachine(test_config)
        sm.transition_to(SystemState.IDLE)
        
        # Should still be idle, previous should still be None
        assert sm.current_state == SystemState.IDLE
        assert sm.previous_state is None
    
    def test_multiple_transitions(self, test_config):
        """Test chain of state transitions"""
        sm = StateMachine(test_config)
        
        sm.transition_to(SystemState.LISTENING)
        assert sm.current_state == SystemState.LISTENING
        assert sm.previous_state == SystemState.IDLE
        
        sm.transition_to(SystemState.PROCESSING)
        assert sm.current_state == SystemState.PROCESSING
        assert sm.previous_state == SystemState.LISTENING
        
        sm.transition_to(SystemState.RESPONDING)
        assert sm.current_state == SystemState.RESPONDING
        assert sm.previous_state == SystemState.PROCESSING
    
    def test_set_state_data(self, test_config):
        """Test setting state data"""
        sm = StateMachine(test_config)
        
        sm.set_state_data("key1", "value1")
        sm.set_state_data("key2", 42)
        
        assert sm.state_data["key1"] == "value1"
        assert sm.state_data["key2"] == 42
    
    def test_get_state_data(self, test_config):
        """Test getting state data"""
        sm = StateMachine(test_config)
        
        sm.set_state_data("test_key", "test_value")
        
        assert sm.get_state_data("test_key") == "test_value"
        assert sm.get_state_data("nonexistent", "default") == "default"
    
    def test_clear_state_data(self, test_config):
        """Test clearing state data"""
        sm = StateMachine(test_config)
        
        sm.set_state_data("key1", "value1")
        sm.set_state_data("key2", "value2")
        
        assert len(sm.state_data) == 2
        
        sm.clear_state_data()
        
        assert len(sm.state_data) == 0
    
    def test_register_callback(self, test_config):
        """Test registering state callback"""
        sm = StateMachine(test_config)
        callback_called = []
        
        def my_callback(state_data):
            callback_called.append(True)
        
        sm.register_callback(SystemState.PROCESSING, my_callback)
        sm.transition_to(SystemState.PROCESSING)
        
        assert len(callback_called) == 1
    
    def test_callback_receives_state_data(self, test_config):
        """Test callback receives state data"""
        sm = StateMachine(test_config)
        received_data = []
        
        def my_callback(state_data):
            received_data.append(state_data.copy())
        
        sm.register_callback(SystemState.PROCESSING, my_callback)
        sm.transition_to(SystemState.PROCESSING, {"test": "data"})
        
        assert len(received_data) == 1
        assert received_data[0]["test"] == "data"
    
    def test_multiple_callbacks(self, test_config):
        """Test multiple callbacks for same state"""
        sm = StateMachine(test_config)
        call_count = []
        
        def callback1(data):
            call_count.append(1)
        
        def callback2(data):
            call_count.append(2)
        
        sm.register_callback(SystemState.PROCESSING, callback1)
        sm.register_callback(SystemState.PROCESSING, callback2)
        sm.transition_to(SystemState.PROCESSING)
        
        assert len(call_count) == 2
    
    def test_callback_error_handling(self, test_config):
        """Test callback errors don't crash system"""
        sm = StateMachine(test_config)
        
        def bad_callback(data):
            raise ValueError("Callback error")
        
        sm.register_callback(SystemState.PROCESSING, bad_callback)
        
        # Should not raise exception
        sm.transition_to(SystemState.PROCESSING)
    
    def test_process_input_stop_command(self, test_config):
        """Test processing stop command"""
        sm = StateMachine(test_config)
        sm.transition_to(SystemState.PROCESSING)
        
        sm.process_input("stop")
        
        assert sm.current_state == SystemState.IDLE
    
    def test_process_input_cancel_command(self, test_config):
        """Test processing cancel command"""
        sm = StateMachine(test_config)
        sm.transition_to(SystemState.PROCESSING)
        
        sm.process_input("cancel that")
        
        assert sm.current_state == SystemState.IDLE
    
    def test_process_input_help_command(self, test_config):
        """Test processing help command"""
        sm = StateMachine(test_config)
        sm.process_input("help me")
        
        assert sm.get_state_data("help_requested") is True
    
    def test_process_input_stores_input(self, test_config):
        """Test input is stored in state data"""
        sm = StateMachine(test_config)
        test_input = "turn on the lights"
        
        sm.process_input(test_input)
        
        assert sm.get_state_data("last_input") == test_input
    
    def test_is_idle(self, test_config):
        """Test is_idle check"""
        sm = StateMachine(test_config)
        
        assert sm.is_idle() is True
        
        sm.transition_to(SystemState.PROCESSING)
        assert sm.is_idle() is False
    
    def test_is_busy_processing(self, test_config):
        """Test is_busy when processing"""
        sm = StateMachine(test_config)
        
        assert sm.is_busy() is False
        
        sm.transition_to(SystemState.PROCESSING)
        assert sm.is_busy() is True
    
    def test_is_busy_executing_action(self, test_config):
        """Test is_busy when executing action"""
        sm = StateMachine(test_config)
        
        sm.transition_to(SystemState.EXECUTING_ACTION)
        assert sm.is_busy() is True
    
    def test_is_busy_other_states(self, test_config):
        """Test is_busy returns False for non-busy states"""
        sm = StateMachine(test_config)
        
        sm.transition_to(SystemState.LISTENING)
        assert sm.is_busy() is False
        
        sm.transition_to(SystemState.RESPONDING)
        assert sm.is_busy() is False
    
    def test_set_error(self, test_config):
        """Test setting error state"""
        sm = StateMachine(test_config)
        error_msg = "Something went wrong"
        
        sm.set_error(error_msg)
        
        assert sm.current_state == SystemState.ERROR
        assert sm.get_state_data("error_message") == error_msg
    
    def test_clear_error(self, test_config):
        """Test clearing error state"""
        sm = StateMachine(test_config)
        
        sm.set_error("Error occurred")
        assert sm.current_state == SystemState.ERROR
        
        sm.clear_error()
        assert sm.current_state == SystemState.IDLE
        assert sm.get_state_data("error_message") is None
    
    def test_clear_error_when_not_in_error(self, test_config):
        """Test clearing error when not in error state does nothing"""
        sm = StateMachine(test_config)
        sm.transition_to(SystemState.PROCESSING)
        
        sm.clear_error()
        
        # Should still be in PROCESSING state
        assert sm.current_state == SystemState.PROCESSING
    
    def test_all_system_states_exist(self, test_config):
        """Test all expected system states exist"""
        expected_states = [
            "IDLE", "LISTENING", "PROCESSING",
            "RESPONDING", "EXECUTING_ACTION", "ERROR"
        ]
        
        for state_name in expected_states:
            assert hasattr(SystemState, state_name)
    
    def test_state_enum_values(self, test_config):
        """Test state enum values are lowercase strings"""
        assert SystemState.IDLE.value == "idle"
        assert SystemState.LISTENING.value == "listening"
        assert SystemState.PROCESSING.value == "processing"
        assert SystemState.RESPONDING.value == "responding"
        assert SystemState.EXECUTING_ACTION.value == "executing_action"
        assert SystemState.ERROR.value == "error"
    
    def test_get_current_state_with_data(self, test_config):
        """Test getting current state returns copy of data"""
        sm = StateMachine(test_config)
        sm.set_state_data("key", "value")
        
        state1 = sm.get_current_state()
        state1["data"]["key"] = "modified"
        
        state2 = sm.get_current_state()
        assert state2["data"]["key"] == "value"  # Should not be modified
    
    def test_state_data_persists_across_transitions(self, test_config):
        """Test state data persists when transitioning"""
        sm = StateMachine(test_config)
        
        sm.set_state_data("persistent_key", "persistent_value")
        sm.transition_to(SystemState.PROCESSING)
        sm.transition_to(SystemState.RESPONDING)
        
        assert sm.get_state_data("persistent_key") == "persistent_value"
    
    def test_transition_data_updates_existing(self, test_config):
        """Test transition data updates existing state data"""
        sm = StateMachine(test_config)
        
        sm.set_state_data("key1", "value1")
        sm.set_state_data("key2", "value2")
        
        sm.transition_to(SystemState.PROCESSING, {"key1": "updated", "key3": "new"})
        
        assert sm.get_state_data("key1") == "updated"  # Updated
        assert sm.get_state_data("key2") == "value2"   # Unchanged
        assert sm.get_state_data("key3") == "new"      # Added
