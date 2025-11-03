"""
Action Executor - Execute Commands and Actions
Handles execution of commands extracted from NLU responses
"""

import asyncio
from typing import Dict, Any, List, Callable, Optional

from src.utils.logging import get_logger
from src.utils.config import Config

logger = get_logger(__name__)


class ActionExecutor:
    """
    Action Execution Engine
    
    Executes actions extracted from NLU responses:
    - Smart home control
    - Information retrieval
    - Reminders and scheduling
    - Media control
    - Custom actions
    """
    
    def __init__(self, config: Config):
        """
        Initialize action executor
        
        Args:
            config: Configuration object
        """
        self.config = config
        
        # Action handlers registry
        self.handlers: Dict[str, Callable] = {}
        
        # Register default handlers
        self._register_default_handlers()
        
        logger.info("Action executor initialized")
    
    def _register_default_handlers(self):
        """Register default action handlers"""
        self.register_handler("smart_home", self._handle_smart_home)
        self.register_handler("information", self._handle_information)
        self.register_handler("reminder", self._handle_reminder)
        self.register_handler("media", self._handle_media)
        self.register_handler("communication", self._handle_communication)
        self.register_handler("search", self._handle_search)
    
    def register_handler(self, action_type: str, handler: Callable):
        """
        Register an action handler
        
        Args:
            action_type: Type of action
            handler: Handler function (async or sync)
        """
        self.handlers[action_type] = handler
        logger.info(f"Registered handler for action type: {action_type}")
    
    def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single action
        
        Args:
            action: Action dictionary with 'action_type' and 'parameters'
            
        Returns:
            Result dictionary
        """
        action_type = action.get("action_type")
        parameters = action.get("parameters", {})
        
        if not action_type:
            return {"success": False, "error": "No action_type specified"}
        
        handler = self.handlers.get(action_type)
        if not handler:
            logger.warning(f"No handler for action type: {action_type}")
            return {
                "success": False,
                "error": f"Unknown action type: {action_type}"
            }
        
        try:
            logger.info(f"Executing action: {action_type} with params: {parameters}")
            result = handler(parameters)
            return {"success": True, "result": result, "action_type": action_type}
        except Exception as e:
            logger.error(f"Action execution error: {e}", exc_info=True)
            return {"success": False, "error": str(e), "action_type": action_type}
    
    async def execute_async(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Async version of execute"""
        action_type = action.get("action_type")
        parameters = action.get("parameters", {})
        
        if not action_type:
            return {"success": False, "error": "No action_type specified"}
        
        handler = self.handlers.get(action_type)
        if not handler:
            logger.warning(f"No handler for action type: {action_type}")
            return {
                "success": False,
                "error": f"Unknown action type: {action_type}"
            }
        
        try:
            logger.info(f"Executing action: {action_type} with params: {parameters}")
            
            # Check if handler is async
            if asyncio.iscoroutinefunction(handler):
                result = await handler(parameters)
            else:
                result = await asyncio.to_thread(handler, parameters)
            
            return {"success": True, "result": result, "action_type": action_type}
        except Exception as e:
            logger.error(f"Action execution error: {e}", exc_info=True)
            return {"success": False, "error": str(e), "action_type": action_type}
    
    def execute_batch(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute multiple actions
        
        Args:
            actions: List of action dictionaries
            
        Returns:
            List of result dictionaries
        """
        results = []
        for action in actions:
            result = self.execute(action)
            results.append(result)
        return results
    
    async def execute_batch_async(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Async version of execute_batch"""
        tasks = [self.execute_async(action) for action in actions]
        results = await asyncio.gather(*tasks)
        return list(results)
    
    # Default Action Handlers
    
    def _handle_smart_home(self, params: Dict[str, Any]) -> str:
        """Handle smart home control actions"""
        device = params.get("device", "device")
        location = params.get("location", "")
        action = params.get("action", "")
        value = params.get("value")
        
        # In production, integrate with actual smart home API
        # (HomeKit, Google Home, Alexa, Home Assistant, etc.)
        
        logger.info(f"Smart home action: {action} {device} in {location}")
        
        if action == "on":
            return f"Turned on {device} in {location}"
        elif action == "off":
            return f"Turned off {device} in {location}"
        elif action == "set" and value:
            return f"Set {device} in {location} to {value}"
        else:
            return f"Executed {action} on {device}"
    
    def _handle_information(self, params: Dict[str, Any]) -> str:
        """Handle information retrieval actions"""
        info_type = params.get("type", "")
        location = params.get("location", "current")
        
        # In production, integrate with actual APIs
        # (Weather API, News API, etc.)
        
        logger.info(f"Information request: {info_type} for {location}")
        
        if info_type == "weather":
            return "The current weather is 72°F and sunny"
        elif info_type == "news":
            return "Here are the top news headlines..."
        elif info_type == "time":
            from datetime import datetime
            return f"The current time is {datetime.now().strftime('%I:%M %p')}"
        else:
            return f"Retrieved information about {info_type}"
    
    def _handle_reminder(self, params: Dict[str, Any]) -> str:
        """Handle reminder and scheduling actions"""
        action = params.get("action", "")
        time = params.get("time", "")
        message = params.get("message", "")
        
        # In production, integrate with calendar/reminder system
        
        logger.info(f"Reminder action: {action} at {time} - {message}")
        
        if action == "set":
            return f"I'll remind you {message} at {time}"
        elif action == "list":
            return "You have 3 upcoming reminders"
        elif action == "cancel":
            return "Reminder cancelled"
        else:
            return "Reminder action completed"
    
    def _handle_media(self, params: Dict[str, Any]) -> str:
        """Handle media control actions"""
        action = params.get("action", "")
        media_type = params.get("type", "music")
        title = params.get("title", "")
        
        # In production, integrate with media player APIs
        # (Spotify, Apple Music, YouTube, etc.)
        
        logger.info(f"Media action: {action} {media_type} - {title}")
        
        if action == "play":
            return f"Playing {title}" if title else f"Playing {media_type}"
        elif action == "pause":
            return "Media paused"
        elif action == "stop":
            return "Media stopped"
        elif action == "next":
            return "Playing next track"
        elif action == "previous":
            return "Playing previous track"
        else:
            return "Media action completed"
    
    def _handle_communication(self, params: Dict[str, Any]) -> str:
        """Handle communication actions"""
        action = params.get("action", "")
        recipient = params.get("recipient", "")
        message = params.get("message", "")
        
        # In production, integrate with messaging/phone APIs
        
        logger.info(f"Communication action: {action} to {recipient}")
        
        if action == "send_message":
            return f"Message sent to {recipient}"
        elif action == "call":
            return f"Calling {recipient}"
        elif action == "email":
            return f"Email sent to {recipient}"
        else:
            return "Communication action completed"
    
    def _handle_search(self, params: Dict[str, Any]) -> str:
        """Handle search actions"""
        query = params.get("query", "")
        
        # In production, integrate with search APIs
        
        logger.info(f"Search query: {query}")
        
        return f"Here's what I found about {query}..."
