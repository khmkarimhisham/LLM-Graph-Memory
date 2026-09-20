import sys
from memory_manager import MemoryManager

def main():
    print("Initializing LLM Graph Memory...")
    manager = MemoryManager()
    
    print("Checking database connection...")
    try:
        manager.db.execute_query("RETURN 1")
        print("Database connected successfully!")
    except Exception as e:
        print(f"Warning: Could not connect to database. It might hang or fail. Error: {e}")
    
    # Optional: uncomment to clear the database on start for clean testing
    # manager.db.clear_database()
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
            response = manager.chat(user_input)
            print(f"\n{response}")
                
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        manager.cleanup()
        print("Goodbye!")

if __name__ == "__main__":
    main()
