#!/usr/bin/env python3
"""Entry point script for Discord Weather Bot."""

import asyncio
from src.bot import main

if __name__ == "__main__":
    asyncio.run(main())