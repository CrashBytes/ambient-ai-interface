"""
Basic Conversation Example
Demonstrates simple text-based interaction with the Ambient AI system
"""

import sys
sys.path.insert(0, '../')

from src.main import AmbientAI


def main():
    """Run a basic conversation loop"""
    
    print("=" * 60)
    print("Ambient AI - Basic Conversation Example")
    print("=" * 60)
    print("This example demonstrates text-based interaction")
    print("Type 'quit' or 'exit' to stop")
    print("")
    
    # Initialize the system
    print("Initializing Ambient AI...")
    ai = AmbientAI()
    print("System ready!\n")
    
    # Conversation loop
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\nAssistant: Goodbye!")
                break
            
            # Process command
            response = ai.process_single_command(user_input)
            
            # Display response
            print(f"Assistant: {response}\n")
            
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
            break
        except Exception as e:
            print(f"Error: {e}")
            continue
    
    # Cleanup
    ai.stop()
    print("\nThank you for using Ambient AI!")


if __name__ == "__main__":
    main()
