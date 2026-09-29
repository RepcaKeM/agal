#!/usr/bin/env python3
"""agal — Agent Agnostic Launch

Shim for backward compatibility. Delegates to agal.cli.main().
"""
import sys
from agal.cli import main

if __name__ == "__main__":
    main(sys.argv[1:])
