"""Root runner delegating to scraping_assignment/main.py."""

import sys
from pathlib import Path

# Add scraping_assignment to path
assignment_dir = Path(__file__).resolve().parent / "scraping_assignment"
if str(assignment_dir) not in sys.path:
    sys.path.insert(0, str(assignment_dir))

from main import main

if __name__ == "__main__":
    main()
