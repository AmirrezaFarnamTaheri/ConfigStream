# AST Symbol Inventory & LSP Refactoring Safety Audit

## 1. Package Export (`__all__`) Compliance Matrix

An inspection of all `__init__.py` files across the `src/configstream/` packages reveals a significant gap in explicit symbol exports. Relying on implicit exports breaks encapsulation and reduces LSP auto-completion reliability.

| Package | `__init__.py` Present | `__all__` Defined | Compliance Status |
| :--- | :--- | :--- | :--- |
| `configstream` (root) | ✅ Yes | ✅ Yes | 🟢 Compliant |
| `configstream.adapters` | ✅ Yes | ❌ No | 🔴 Non-Compliant |
| `configstream.converters` | ✅ Yes | ❌ No | 🔴 Non-Compliant |
| `configstream.generators` | ✅ Yes | ❌ No | 🔴 Non-Compliant |
| `configstream.history` | ✅ Yes | ❌ No | 🔴 Non-Compliant |
| `configstream.output` | ✅ Yes | ❌ No | 🔴 Non-Compliant |
| `configstream.parsers` | ✅ Yes | ❌ No | 🔴 Non-Compliant |
| `configstream.pipeline` | ✅ Yes | ❌ No | 🔴 Non-Compliant |
| `configstream.quality` | ✅ Yes | ❌ No | 🔴 Non-Compliant |
| `configstream.server` | ✅ Yes | ❌ No | 🔴 Non-Compliant |
| `configstream.testers` | ✅ Yes | ❌ No | 🔴 Non-Compliant |
| `configstream.tools` | ✅ Yes | ❌ No | 🔴 Non-Compliant |
| `configstream.utils` | ✅ Yes | ❌ No | 🔴 Non-Compliant |

**Action Item:** Define explicit `__all__` lists in all sub-packages to explicitly declare the public API boundary.

## 2. Dead Symbol & Unused Import Inventory

An AST-based static analysis was conducted (using `flake8` and AST traversal).
- **Unused Imports:** 0 instances found. The codebase is impeccably clean regarding dangling imports (Flake8 F401/F841 compliant).
- **Dead Symbols / Internal Bleed:** A few internal helper functions (e.g., `_patch_sniffio_for_asyncio`, `_apply_compat_patches` in root `__init__.py`, `_get_lock` in `adaptive_timeout.py`) exist but are strictly scoped. 
- **Risk:** Due to the lack of `__all__` declarations in sub-packages, any internal class or function lacking a `_` prefix is implicitly considered part of the public module API, risking external entanglement.

## 3. Type Hint & Diagnostics Health Assessment

An AST traversal analyzed 155 `.py` files across `src/configstream/`:
- **Total Files Analyzed:** 155
- **Missing Return Types:** 61 occurrences
- **Missing Argument Annotations:** 50 occurrences
- **LSP Diagnostics (Flake8):** 0 errors found (Max line length 120, standard strict subset).

**Health Status: 🟢 Good, but Needs Strictification**
The type hinting density is remarkably high, but missing annotations (especially return types) break the LSP type inference chain. This reduces the safety net during complex AST-level refactorings.

## 4. AST Refactoring Safety Protocols

To ensure safe architectural evolution, the following protocols must be adhered to before and during any symbol refactoring (renaming, deletion, or moving):

1. **Explicit API Boundaries (`__all__`):** 
   - No module shall implicitly export symbols. 
   - Before extracting or moving a symbol, ensure its visibility is explicitly scoped via `__all__`.
2. **Type Continuity:**
   - Any function being refactored MUST have 100% complete type hints (both arguments and return type). If missing, backfill the annotations *before* moving.
3. **AST-Aware Renaming:**
   - Do not use text-based search-and-replace for renaming symbols. Use AST-aware LSP tools (e.g., `rope`, `pylsp`, `jedi`) to prevent shadowing and string-literal false positives.
4. **Deprecation Strategy (Deletion):**
   - Public symbols slated for deletion must not be removed outright. 
   - Use the `warnings.warn("...", DeprecationWarning, stacklevel=2)` pattern and preserve the symbol for at least one minor release cycle.
5. **Private Symbol Encapsulation:**
   - Prefix any unexported internal functions with `_`. This signals to downstream tools that the symbol is volatile and immune to semantic versioning guarantees.
