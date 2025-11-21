import pytest
import nest_asyncio

# Apply nest_asyncio to allow nested event loops (e.g. internal run calls)
# This is critical for tests that call code using asyncio.run() or loop.run_until_complete()
nest_asyncio.apply()
