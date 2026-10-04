import os
import yaml
from dotenv import load_dotenv

def load_config():
    """Loads environment variables and parses the settings.yaml file."""
    # Load environment variables
    load_dotenv()
    
    # Check for required API keys
    if not os.environ.get("GOOGLE_API_KEY"):
        print("Warning: GOOGLE_API_KEY is not set in environment variables.")
        
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'settings.yaml')
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
            return config
    except FileNotFoundError:
        print(f"Error: Could not find config file at {config_path}")
        return None

if __name__ == "__main__":
    config = load_config()
    print("Config loaded successfully:", config['project']['name'])
