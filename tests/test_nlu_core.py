"""
Unit tests for NLU Core
Tests natural language understanding, action extraction, and intent classification
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.nlu_core import NLUCore


class TestNLUCore:
    """Test NLU core functionality"""
    
    def test_initialization(self, test_config):
        """Test NLU core initialization"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            
            assert nlu.model == test_config.openai_model
            assert nlu.temperature == test_config.nlu_temperature
            assert nlu.max_tokens == test_config.nlu_max_tokens
            assert nlu.system_prompt is not None
    
    def test_default_system_prompt(self, test_config):
        """Test default system prompt generation"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            prompt = nlu._get_default_system_prompt()
            
            assert "ambient AI assistant" in prompt
            assert "ACTION:" in prompt
            assert "smart_home" in prompt
    
    def test_custom_system_prompt(self, test_config):
        """Test custom system prompt"""
        custom_prompt = "You are a custom AI assistant"
        test_config.nlu_system_prompt = custom_prompt
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            assert nlu.system_prompt == custom_prompt
    
    def test_process_simple_input(self, test_config, mock_openai_client):
        """Test processing simple user input"""
        with patch('openai.OpenAI', return_value=mock_openai_client):
            with patch('openai.AsyncOpenAI'):
                nlu = NLUCore(test_config)
                response = nlu.process("Hello")
                
                assert response is not None
                assert isinstance(response, str)
    
    def test_process_with_context(self, test_config, mock_openai_client, sample_context_messages):
        """Test processing with conversation context"""
        with patch('openai.OpenAI', return_value=mock_openai_client):
            with patch('openai.AsyncOpenAI'):
                nlu = NLUCore(test_config)
                response = nlu.process(
                    "How about tomorrow?",
                    context=sample_context_messages
                )
                
                assert response is not None
    
    def test_process_with_state(self, test_config, mock_openai_client):
        """Test processing with system state"""
        state = {
            "current_location": "living room",
            "devices_on": ["lights", "tv"]
        }
        
        with patch('openai.OpenAI', return_value=mock_openai_client):
            with patch('openai.AsyncOpenAI'):
                nlu = NLUCore(test_config)
                response = nlu.process("Turn off the TV", state=state)
                
                assert response is not None
    
    @pytest.mark.asyncio
    async def test_process_async(self, test_config, mock_async_openai_client):
        """Test async processing"""
        with patch('openai.OpenAI'):
            with patch('openai.AsyncOpenAI', return_value=mock_async_openai_client):
                nlu = NLUCore(test_config)
                response = await nlu.process_async("Hello")
                
                assert response is not None
                assert isinstance(response, str)
    
    @pytest.mark.asyncio
    async def test_process_async_with_context(self, test_config, mock_async_openai_client, sample_context_messages):
        """Test async processing with context"""
        with patch('openai.OpenAI'):
            with patch('openai.AsyncOpenAI', return_value=mock_async_openai_client):
                nlu = NLUCore(test_config)
                response = await nlu.process_async(
                    "What did we talk about?",
                    context=sample_context_messages
                )
                
                assert response is not None
    
    def test_process_error_handling(self, test_config):
        """Test error handling during processing"""
        with patch('openai.OpenAI') as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.chat.completions.create.side_effect = Exception("API Error")
            
            with patch('openai.AsyncOpenAI'):
                nlu = NLUCore(test_config)
                response = nlu.process("Test input")
                
                # Should return error message
                assert "sorry" in response.lower() or "trouble" in response.lower()
    
    def test_build_messages_simple(self, test_config):
        """Test building messages for API call"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            messages = nlu._build_messages("Hello", None, None)
            
            assert len(messages) == 2  # system + user
            assert messages[0]["role"] == "system"
            assert messages[1]["role"] == "user"
            assert messages[1]["content"] == "Hello"
    
    def test_build_messages_with_context(self, test_config, sample_context_messages):
        """Test building messages with context"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            messages = nlu._build_messages("New message", sample_context_messages, None)
            
            # system + context messages + new message
            assert len(messages) > 3
            assert messages[-1]["content"] == "New message"
    
    def test_build_messages_with_state(self, test_config):
        """Test building messages with state"""
        state = {"location": "bedroom", "time": "night"}
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            messages = nlu._build_messages("Test", None, state)
            
            # Should have system prompt + state + user message
            assert len(messages) == 3
            assert any("state" in msg.get("content", "").lower() for msg in messages)
    
    def test_format_state_info(self, test_config):
        """Test state information formatting"""
        state = {"location": "kitchen", "temperature": 72, "lights": "on"}
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            formatted = nlu._format_state_info(state)
            
            assert "location" in formatted
            assert "kitchen" in formatted
            assert "temperature" in formatted
    
    def test_format_state_info_empty(self, test_config):
        """Test formatting empty state"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            formatted = nlu._format_state_info(None)
            
            assert formatted == ""
    
    def test_extract_actions_single(self, test_config):
        """Test extracting single action from response"""
        response = 'I\'ll turn on the lights. ACTION: {"action_type": "smart_home", "parameters": {"device": "lights", "action": "on"}}'
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            actions = nlu.extract_actions(response)
            
            assert len(actions) == 1
            assert actions[0]["action_type"] == "smart_home"
            assert actions[0]["parameters"]["device"] == "lights"
    
    def test_extract_actions_multiple(self, test_config):
        """Test extracting multiple actions"""
        response = '''I'll do that. 
        ACTION: {"action_type": "smart_home", "parameters": {"device": "lights", "action": "on"}}
        And also ACTION: {"action_type": "information", "parameters": {"type": "weather"}}'''
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            actions = nlu.extract_actions(response)
            
            assert len(actions) == 2
    
    def test_extract_actions_none(self, test_config):
        """Test response with no actions"""
        response = "Hello! How can I help you today?"
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            actions = nlu.extract_actions(response)
            
            assert len(actions) == 0
    
    def test_extract_actions_invalid_json(self, test_config):
        """Test handling invalid JSON in action"""
        response = "ACTION: {invalid json}"
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            actions = nlu.extract_actions(response)
            
            assert len(actions) == 0  # Should skip invalid JSON
    
    def test_extract_entities_devices(self, test_config):
        """Test extracting device entities"""
        text = "Turn on the living room lights and lock the door"
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            entities = nlu.extract_entities(text)
            
            assert "lights" in entities["devices"] or "light" in entities["devices"]
            assert "lock" in entities["devices"] or "door" in entities["devices"]
    
    def test_extract_entities_locations(self, test_config):
        """Test extracting location entities"""
        text = "Set the bedroom temperature to 72 and turn off kitchen lights"
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            entities = nlu.extract_entities(text)
            
            assert len(entities["locations"]) > 0
    
    def test_extract_entities_times(self, test_config):
        """Test extracting time entities"""
        text = "Remind me tomorrow morning to check the weather"
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            entities = nlu.extract_entities(text)
            
            assert len(entities["times"]) > 0
    
    def test_extract_entities_numbers(self, test_config):
        """Test extracting number entities"""
        text = "Set temperature to 72 degrees at 8 AM"
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            entities = nlu.extract_entities(text)
            
            assert len(entities["numbers"]) > 0
            assert "72" in entities["numbers"]
    
    def test_classify_intent_control(self, test_config):
        """Test control intent classification"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            
            assert nlu.classify_intent("Turn on the lights") == "control"
            assert nlu.classify_intent("Set temperature to 70") == "control"
            assert nlu.classify_intent("Adjust the volume") == "control"
    
    def test_classify_intent_query(self, test_config):
        """Test query intent classification"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            
            assert nlu.classify_intent("What's the weather?") == "query"
            assert nlu.classify_intent("When is my next meeting?") == "query"
            assert nlu.classify_intent("How do I make coffee?") == "query"
    
    def test_classify_intent_reminder(self, test_config):
        """Test reminder intent classification"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            
            assert nlu.classify_intent("Remind me to call mom") == "reminder"
            # Set alarm can be classified as either control or reminder - both are valid
            result = nlu.classify_intent("Set alarm for 7 AM")
            assert result in ["reminder", "control"]
    
    def test_classify_intent_media(self, test_config):
        """Test media intent classification"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            
            assert nlu.classify_intent("Play my favorite song") == "media"
            assert nlu.classify_intent("Stop the music") == "media"
            assert nlu.classify_intent("Next track please") == "media"
    
    def test_classify_intent_communication(self, test_config):
        """Test communication intent classification"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            
            assert nlu.classify_intent("Send a message to John") == "communication"
            assert nlu.classify_intent("Call my wife") == "communication"
    
    def test_classify_intent_general(self, test_config):
        """Test general intent classification"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            
            assert nlu.classify_intent("Hello there") == "general"
            assert nlu.classify_intent("Thank you") == "general"
    
    def test_confidence_score_high(self, test_config):
        """Test high confidence score"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            
            score = nlu.get_confidence_score("The temperature is 72 degrees")
            assert score >= 0.7
    
    def test_confidence_score_low(self, test_config):
        """Test low confidence score for uncertain responses"""
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            
            score = nlu.get_confidence_score("I'm not sure about that")
            assert score <= 0.6
            
            score = nlu.get_confidence_score("Maybe it's around 70 degrees")
            assert score <= 0.6
    
    def test_context_length_limiting(self, test_config):
        """Test that context is limited to max_context_length"""
        # Create context longer than max_context_length
        long_context = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(20)
        ]
        
        test_config.max_context_length = 5
        
        with patch('openai.OpenAI'), patch('openai.AsyncOpenAI'):
            nlu = NLUCore(test_config)
            messages = nlu._build_messages("New message", long_context, None)
            
            # Should have system + last 5 context messages + new message
            assert len(messages) <= 7  # system + 5 context + current
