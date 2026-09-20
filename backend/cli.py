import sys
from app.agent.service import ask_restock_agent

def main():
    print("ReStockAI Manager Assistant CLI")
    print("Type 'exit' to quit.\n")
    
    while True:
        try:
            question = input("Manager: ")
            if question.strip().lower() in ['exit', 'quit']:
                break
            if not question.strip():
                continue
                
            print("\nThinking...")
            result = ask_restock_agent(question)
            
            print(f"\nAgent:\n{result['answer']}")
            if result.get('tools_used'):
                print(f"\n[Tools used: {', '.join(result['tools_used'])}]")
            print("-" * 50)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\nError: {e}")
            break

if __name__ == "__main__":
    main()
