import sys
import threading
from memory_manager import MemoryManager
from chat_manager import ChatManager

def main():
    print("Initializing LLM Graph Memory...")
    memory_manager = MemoryManager()
    chat_manager = ChatManager()
    
    print("Checking database connection...")
    try:
        memory_manager.db.execute_query("RETURN 1")
        print("Database connected successfully!")
    except Exception as e:
        print(f"Warning: Could not connect to database. It might hang or fail. Error: {e}")
    
    # Optional: uncomment to clear the database on start for clean testing
    # memory_manager.db.clear_database()
    # print("Database cleared.")

    print("\nHello! What would you like to know?")
    print("\n")

    try:
        while True:
            try:
                user_input = input("\n> ").strip()
            except EOFError:
                break
                
            if not user_input:
                continue
                
            if user_input.lower() == 'exit':
                break
                
            print("Thinking...")
            
            # 1. Get Context
            context = memory_manager.get_relevant_context(user_input)
            
            # 2. Get Chat Response
            response = chat_manager.chat(user_input, context)
            print(f"\n{response}")
            
            # 3. Asynchronously extract and store memory
            extraction_thread = threading.Thread(
                target=memory_manager.extract_and_store_memory,
                args=(user_input,)
            )
            extraction_thread.start()
                
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        memory_manager.cleanup()
        print("Goodbye!")

if __name__ == "__main__":
    main()
