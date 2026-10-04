import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.rag.query_engine import QueryEngine

def main():
    print("=====================================================")
    print("🤖 Google Photos Discovery Engine — Interactive Q&A")
    print("=====================================================")
    print("Type your question (or 'quit' to exit):")
    
    engine = QueryEngine()
    chat_history = []
    current_filters = {}
    
    while True:
        try:
            if current_filters:
                print(f"  [Active Filters: {current_filters}]")
            query = input("\n🔍 > ")
            
            if query.lower() in ['quit', 'exit', 'q']:
                break
            
            if not query.strip():
                continue
            
            if query.startswith('/filter'):
                parts = query.split(' ')
                if len(parts) >= 2:
                    if parts[1] == 'clear':
                        current_filters = {}
                        print("✅ Filters cleared.")
                    else:
                        for p in parts[1:]:
                            if '=' in p:
                                k, v = p.split('=', 1)
                                current_filters[k] = v
                        print(f"✅ Filters updated: {current_filters}")
                else:
                    print("Usage: /filter key=value OR /filter clear")
                continue
            
            # Format chat history for the prompt
            if not chat_history:
                history_text = "None"
            else:
                history_text = "\n".join([f"{role}: {msg}" for role, msg in chat_history])
                
            response = engine.process_query(query, chat_history=history_text, filters=current_filters if current_filters else None)
            
            print("\n📊 Answer:")
            print("="*50)
            print(response)
            print("="*50)
            
            # Append to history, keep only last 5 turns to avoid token overflow
            chat_history.append(("User", query))
            chat_history.append(("Assistant", response))
            if len(chat_history) > 10:
                chat_history = chat_history[-10:]
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
