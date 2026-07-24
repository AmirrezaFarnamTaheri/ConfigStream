# Parser Extension Specification: TUIC v5 and Hysteria3

## 1. Current Parser Architecture Diagram

```ascii
+-------------------------------------------------+
|               extraction.py                     |
|  (Line splitting, format detection, filtering)  |
+------------------------+------------------------+
                         |
                         v
+------------------------+------------------------+
|                   others.py                     |
|         (Protocol-specific parser logic)        |
+------------------------+------------------------+
                         |
      +------------------+------------------+
      |                                     |
      v                                     v
+-------------+                       +-------------+
| parse_tuic  |                       | parse_hy3   |
| (TUIC v5)   |                       | (Hysteria3) |
+-------------+                       +-------------+
      |                                     |
      +------------------+------------------+
                         |
                         v
+------------------------+------------------------+
|                base.py / models.py              |
| (normalize_proxy_details, Proxy model creation) |
+-------------------------------------------------+
```

## 2. TUIC v5 Parser Specification

The TUIC parser currently supports basic v5 URIs. The next-generation parser contract extends support for advanced QUIC and congestion control parameters.

### Interface
```python
def parse_tuic(c: str) -> Optional[Proxy]:
    """
    Parses a TUIC v5 URI string.
    URI Format: tuic://<uuid>:<password>@<host>:<port>/?alpn=<alpn>&cc_algo=<cc_algo>&max_idle_time=<ms>&initial_max_streams=<int>#<remarks>
    """
```

### Field Mapping
| URI Query/Auth Field  | Proxy Model Attribute | Data Type | Default/Fallback | Description |
|-----------------------|-----------------------|-----------|------------------|-------------|
| `uuid` (Username)     | `uuid`                | `str`     | -                | TUIC User ID |
| `password` (Password) | `details["password"]` | `str`     | `uuid` fallback  | User password |
| `cc_algo`             | `details["cc_algo"]`  | `str`     | `bbr`            | Congestion control algorithm (e.g., `bbr`, `cubic`, `new_reno`) |
| `max_idle_time`       | `details["max_idle_time"]`| `int` | `15000`          | Max idle time in milliseconds |
| `initial_max_streams` | `details["initial_max_streams"]`| `int` | `100`    | Max concurrent streams |
| `alpn`                | `details["alpn"]`     | `list`    | `["h3"]`         | ALPN protocol list |


## 3. Hysteria3 Parser Specification

Hysteria3 introduces a revised obfuscation framework and new padding mechanisms.

### Interface
```python
def parse_hysteria3(c: str) -> Optional[Proxy]:
    """
    Parses a Hysteria3 URI string.
    URI Format: hy3://<uuid>@<host>:<port>/?multi_port=<ports>&obfs_v2=<type>&obfs-password=<pass>&padding_len=<int>#<remarks>
    """
```

### Field Mapping
| URI Query/Auth Field  | Proxy Model Attribute | Data Type | Default/Fallback | Description |
|-----------------------|-----------------------|-----------|------------------|-------------|
| `uuid` (Username)     | `uuid`                | `str`     | -                | Client auth payload/UUID |
| `multi_port`          | `details["multi_port"]`| `str`    | -                | Port hopping/multi-port spec (e.g., `443,8000-8010`) |
| `obfs_v2`             | `details["obfs_v2"]`  | `str`     | `none`           | Next-gen obfuscation type (e.g., `salamander_v2`) |
| `padding_len`         | `details["padding_len"]`| `int`   | `0`              | Static or dynamic padding bytes |


## 4. `protocol_matrix.json` Entries

To formally register the updated capabilities, the `docs/protocol_matrix.json` requires the following new or updated entries:

```json
    {"id": "tuic", "public": true, "kind": "canonical", "parser": "parse_tuic", "normalized_to": null, "schema": true, "frontend": true, "singbox_export": true, "clash_export": true, "notes": "TUIC v5 URI parsing with password fallback, cc_algo, max_idle_time, and initial_max_streams support."},
    {"id": "hysteria3", "public": true, "kind": "canonical", "parser": "parse_hysteria3", "normalized_to": null, "schema": true, "frontend": true, "singbox_export": true, "clash_export": true, "notes": "Hysteria3 URI parsing with multi_port, obfs_v2, and padding_len support."},
    {"id": "hy3", "public": true, "kind": "alias", "parser": "parse_hysteria3", "normalized_to": "hysteria3", "schema": true, "frontend": true, "singbox_export": true, "clash_export": true, "notes": "Input alias normalized to hysteria3."}
```

## 5. Unit Test Specification

### TUIC v5 Test Cases
**Test Case 1: Complete fields**
- **Input:** `tuic://550e8400-e29b-41d4-a716-446655440000:mypwd@tuic.example.com:8443/?alpn=h3&cc_algo=bbr&max_idle_time=20000&initial_max_streams=200#MyTUIC`
- **Expected Output:**
  - `uuid`: `550e8400-e29b-41d4-a716-446655440000`
  - `details["password"]`: `mypwd`
  - `details["alpn"]`: `h3`
  - `details["cc_algo"]`: `bbr`
  - `details["max_idle_time"]`: `20000`
  - `details["initial_max_streams"]`: `200`
  - `remarks`: `MyTUIC`

**Test Case 2: Missing optional fields (Defaulting)**
- **Input:** `tuic://550e8400-e29b-41d4-a716-446655440000@tuic.example.com:8443/#MinimalTUIC`
- **Expected Output:**
  - `uuid`: `550e8400-e29b-41d4-a716-446655440000`
  - `details["password"]`: `550e8400-e29b-41d4-a716-446655440000` (Fallback to UUID)
  - `details["alpn"]`: `["h3"]` (Injected default)

### Hysteria3 Test Cases
**Test Case 1: Complete fields with port hopping and obfuscation**
- **Input:** `hy3://my-auth-token@hy3.example.com:443/?multi_port=443,8000-8010&obfs_v2=salamander_v2&obfs-password=secret&padding_len=128#MyHy3`
- **Expected Output:**
  - `protocol`: `hysteria3`
  - `uuid`: `my-auth-token`
  - `details["multi_port"]`: `443,8000-8010`
  - `details["obfs_v2"]`: `salamander_v2`
  - `details["obfs-password"]`: `secret`
  - `details["padding_len"]`: `128`
  - `remarks`: `MyHy3`

**Test Case 2: Validation Failure (Missing Obfs Password)**
- **Input:** `hy3://auth@hy3.example.com:443/?obfs_v2=salamander_v2`
- **Expected Output:** `None` (Parsing dropped due to missing `obfs-password` when `obfs_v2` requires it).

## 6. Integration Path into `parsers/__init__.py`

The new `parse_hysteria3` function and updated `parse_tuic` function will be exposed centrally.

1. Implement `parse_hysteria3` in `src/configstream/parsers/others.py`.
2. Modify `parse_tuic` in `src/configstream/parsers/others.py` to cast `max_idle_time` and `initial_max_streams` to integers.
3. Update `src/configstream/parsers/__init__.py` to import and export the new parser:

```python
from .others import (
    parse_hysteria,
    parse_hysteria2,
    parse_hysteria3,  # Added
    parse_tuic,
    ...
)

__all__ = [
    ...
    "parse_hysteria",
    "parse_hysteria2",
    "parse_hysteria3",  # Added
    "parse_tuic",
    ...
]
```
