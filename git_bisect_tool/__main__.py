"""Entry point for running as a module: python -m git_bisect_tool"""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
