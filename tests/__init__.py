# SPDX-License-Identifier: AGPL-3.0-or-later
import nest_asyncio

# Apply nest_asyncio globally for all tests to support nested event loops
# (e.g. running pytest from inside an existing loop, or tests calling asyncio.run)
nest_asyncio.apply()
