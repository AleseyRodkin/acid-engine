"""Allow `python -m acid_engine` to invoke CLI."""
import sys
from acid_engine.cli import main

if __name__ == "__main__":
    sys.exit(main())