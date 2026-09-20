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

    print("\n--- LLM Graph Memory ---")
    print("Commands:")
    print("  tell <fact>  - Add a memory to the graph")
    print("  ask <query>  - Ask a question based on memory")
    print("  exit         - Quit the application")
    print("-" * 24)

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
                
            if user_input.lower().startswith("tell "):
                fact = user_input[5:].strip()
                print("Processing memory...")
                manager.add_memory(fact)
                print("Done.")
                
            elif user_input.lower().startswith("ask "):
                question = user_input[4:].strip()
                print("Searching memory...")
                answer = manager.ask(question)
                print(f"\nAnswer: {answer}")
                
            else:
                print("Invalid command. Use 'tell <fact>' or 'ask <query>'.")
                
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        manager.cleanup()
        print("Goodbye!")

if __name__ == "__main__":
    main()
