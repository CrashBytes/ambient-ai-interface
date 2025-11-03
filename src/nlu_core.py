"""
Natural Language Understanding Core
Uses GPT-4 for intent recognition and response generation
"""

import json
import re
from typing import Optional, List, Dict, Any

from openai import OpenAI, AsyncOpenAI

from src.utils.logging import get_logger
from src.utils.config import Config

logger = get_logger(__name__)


class NLUCore:
    """
    Natural Language Understanding Engine
    
    Processes user input through GPT-4 to:
    - Understand user intent
    - Generate natural responses
    - Extract actionable commands
    - Maintain conversational flow
    """
    
    def __init__(self, config: Config):
        """
        Initialize NLU core
        
        Args:
            config: Configuration object
        """
        self.config = config
        
        # Initialize OpenAI clients
        self.client = OpenAI(api_key=config.openai_api_key)
        self.async_client = AsyncOpenAI(api_key=config.openai_api_key)
        
        # Model configuration
        self.model = config.openai_model
        self.temperature = config.nlu_temperature
        self.max_tokens = config.nlu_max_tokens
        
        # System prompt
        self.system_prompt = config.nlu_system_prompt or self._get_default_system_prompt()
        
        logger.info(f"NLU core initialized (model: {self.model})")
    
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt"""
        return """You are a helpful ambient AI assistant that responds naturally to voice commands.

Key behaviors:
- Be conversational and natural
- Keep responses concise (1-3 sentences usually)
- Acknowledge commands with confirmation
- Ask for clarification when needed
- Remember context from previous exchanges
- When executing actions, describe what you're doing
- Be proactive in offering help

For actionable commands, include structured data in your response using this format:
ACTION: {action_type: "action_name", parameters: {...}}

Available actions:
- smart_home: Control lights, temperature, security
- information: Get weather, news, time, etc.
- reminder: Set reminders and alarms
- communication: Send messages, make calls
- media: Play music, videos, podcasts
- search: Search for information
- custom: Custom user-defined actions

Example responses:
User: "Turn on the living room lights"
Assistant: "I'll turn on the living room lights for you. ACTION: {action_type: "smart_home", parameters: {device: "lights", location: "living room", action: "on"}}"

User: "What's the weather like?"
Assistant: "Let me check the weather for you. ACTION: {action_type: "information", parameters: {type: "weather", location: "current"}}"

Be helpful, friendly, and efficient!"""
    
    def process(
        self,
        user_input: str,
        context: Optional[List[Dict[str, str]]] = None,
        state: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process user input and generate response
        
        Args:
            user_input: User's text input
            context: Conversation history (list of {role, content} dicts)
            state: Current system state
            
        Returns:
            Generated response text
        """
        try:
            # Build messages
            messages = self._build_messages(user_input, context, state)
            
            # Call GPT-4
            logger.info(f"Processing input: {user_input[:50]}...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Extract response text
            response_text = response.choices[0].message.content.strip()
            
            logger.info(f"Generated response: {response_text[:50]}...")
            
            return response_text
            
        except Exception as e:
            logger.error(f"NLU processing error: {e}", exc_info=True)
            return "I'm sorry, I had trouble understanding that. Could you please rephrase?"
    
    async def process_async(
        self,
        user_input: str,
        context: Optional[List[Dict[str, str]]] = None,
        state: Optional[Dict[str, Any]] = None
    ) -> str:
        """Async version of process"""
        try:
            # Build messages
            messages = self._build_messages(user_input, context, state)
            
            # Call GPT-4
            logger.info(f"Processing input: {user_input[:50]}...")
            
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Extract response text
            response_text = response.choices[0].message.content.strip()
            
            logger.info(f"Generated response: {response_text[:50]}...")
            
            return response_text
            
        except Exception as e:
            logger.error(f"NLU processing error: {e}", exc_info=True)
            return "I'm sorry, I had trouble understanding that. Could you please rephrase?"
    
    def _build_messages(
        self,
        user_input: str,
        context: Optional[List[Dict[str, str]]],
        state: Optional[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Build messages array for GPT-4"""
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Add state information if available
        if state:
            state_info = self._format_state_info(state)
            if state_info:
                messages.append({
                    "role": "system",
                    "content": f"Current system state: {state_info}"
                })
        
        # Add context (conversation history)
        if context:
            for msg in context[-self.config.max_context_length:]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # Add current user input
        messages.append({
            "role": "user",
            "content": user_input
        })
        
        return messages
    
    def _format_state_info(self, state: Dict[str, Any]) -> str:
        """Format state information for system prompt"""
        if not state:
            return ""
        
        # Format state dict as readable text
        state_parts = []
        for key, value in state.items():
            state_parts.append(f"{key}: {value}")
        
        return ", ".join(state_parts)
    
    def extract_actions(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Extract action commands from response text
        
        Args:
            response_text: The generated response text
            
        Returns:
            List of action dictionaries
        """
        actions = []
        
        # Look for ACTION: markers in response
        action_pattern = r'ACTION:\s*(\{[^}]+\})'
        matches = re.findall(action_pattern, response_text)
        
        for match in matches:
            try:
                # Parse JSON action
                action = json.loads(match)
                actions.append(action)
                logger.info(f"Extracted action: {action}")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse action: {match} ({e})")
        
        return actions
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract named entities from text
        
        Args:
            text: Input text
            
        Returns:
            Dictionary of entity types and values
        """
        # Simple entity extraction
        # In production, use spaCy or similar NLP library
        
        entities = {
            "devices": [],
            "locations": [],
            "times": [],
            "numbers": []
        }
        
        # Extract device mentions
        device_keywords = ["light", "lights", "thermostat", "temperature", "door", "lock", "camera"]
        for keyword in device_keywords:
            if keyword in text.lower():
                entities["devices"].append(keyword)
        
        # Extract location mentions
        location_keywords = ["living room", "bedroom", "kitchen", "bathroom", "garage"]
        for location in location_keywords:
            if location in text.lower():
                entities["locations"].append(location)
        
        # Extract time references
        time_keywords = ["morning", "afternoon", "evening", "tonight", "today", "tomorrow"]
        for time_ref in time_keywords:
            if time_ref in text.lower():
                entities["times"].append(time_ref)
        
        # Extract numbers
        numbers = re.findall(r'\b\d+\b', text)
        entities["numbers"] = numbers
        
        return entities
    
    def classify_intent(self, text: str) -> str:
        """
        Classify user intent
        
        Args:
            text: User input text
            
        Returns:
            Intent classification
        """
        # Simple keyword-based intent classification
        # In production, train an intent classifier
        
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["turn on", "turn off", "set", "adjust"]):
            return "control"
        elif any(word in text_lower for word in ["what", "when", "where", "how", "who"]):
            return "query"
        elif any(word in text_lower for word in ["remind me", "set alarm", "schedule"]):
            return "reminder"
        elif any(word in text_lower for word in ["play", "stop", "pause", "next", "previous"]):
            return "media"
        elif any(word in text_lower for word in ["send", "message", "call", "text"]):
            return "communication"
        else:
            return "general"
    
    def get_confidence_score(self, response: str) -> float:
        """
        Estimate confidence score for response
        
        Args:
            response: Generated response
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Simple heuristic-based confidence
        # In production, use model's confidence scores
        
        confidence = 0.8  # Default high confidence
        
        # Lower confidence for uncertain phrases
        uncertain_phrases = [
            "i'm not sure",
            "i don't know",
            "maybe",
            "perhaps",
            "i think"
        ]
        
        response_lower = response.lower()
        for phrase in uncertain_phrases:
            if phrase in response_lower:
                confidence = 0.5
                break
        
        return confidence
