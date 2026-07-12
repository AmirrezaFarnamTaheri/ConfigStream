# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Serialization helpers for the public proxy contract.

The runtime Proxy model intentionally carries private provenance and diagnostic
state.  Public output must therefore be produced through an explicit boundary
instead of serializing arbitrary ``details`` mappings verbatim