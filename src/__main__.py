import os
import sys
import importlib
import traceback
from dotenv import load_dotenv

load_dotenv()


def run_module(module_name):
    print(f"Running {module_name}...")
    try:
        module = importlib.import_module(f"src.{module_name}")
        if hasattr(module, 'main'):
            if module_name == 'scraper':
                team_id = os.getenv('TEAM_ID')
                if team_id is None:
                    raise ValueError("TEAM_ID environment variable is not set")
                module.main(user_team_id=team_id)
            else:
                module.main()
        else:
            print(f"Warning: {module_name} has no main() function.")
    except Exception as e:
        print(f"Error running {module_name}:")
        print(str(e))
        print("Stack trace:")
        print(traceback.format_exc())
        sys.exit(1)
    print(f"{module_name} completed successfully.\n")


def main():
    # Run modules in order
    run_module('scraper')
    run_module('data_cleaner')
    run_module('data_maker')
    run_module('ai')

    print("All modules completed successfully.")


if __name__ == "__main__":
    main()
