# ConfigStream Universal Plugin System

This directory contains WASM plugins for parsing proxy configurations.

## Protocol Interface

Each `.wasm` plugin must export the following functions:

1.  `alloc(size: usize) -> *mut u8`: Allocate memory for input string.
2.  `parse(ptr: *mut u8, len: usize) -> *mut c_char`: Parse the config string and return a pointer to a null-terminated JSON string.
3.  `free_string(ptr: *mut c_char)`: Deallocate the string returned by `parse`.

### JSON Output Format

The output JSON should match the `Proxy` model fields:

```json
{
  "protocol": "vless",
  "address": "example.com",
  "port": 443,
  "uuid": "...",
  "remarks": "My Proxy",
  "details": {
      "type": "grpc",
      "serviceName": "example"
  }
}
```

If parsing fails, return `null` or an empty string.

## Building a Plugin (Rust Example)

You can use Rust with `wasm32-unknown-unknown` target.

```rust
use std::ffi::{CString, CStr};
use std::os::raw::c_char;
use std::mem;

#[no_mangle]
pub extern "C" fn alloc(size: usize) -> *mut u8 {
    let mut buf = Vec::with_capacity(size);
    let ptr = buf.as_mut_ptr();
    mem::forget(buf);
    ptr
}

#[no_mangle]
pub extern "C" fn dealloc(ptr: *mut u8, size: usize) {
    unsafe {
        let _ = Vec::from_raw_parts(ptr, 0, size);
    }
}

#[no_mangle]
pub extern "C" fn parse(ptr: *mut u8, len: usize) -> *mut c_char {
    let slice = unsafe { std::slice::from_raw_parts(ptr, len) };
    let config = String::from_utf8_lossy(slice);

    // ... parsing logic ...
    let json_output = "{\"protocol\": \"dummy\", ...}";

    let c_str = CString::new(json_output).unwrap();
    let res_ptr = c_str.into_raw();

    // Dealloc input buffer if not handled by caller (Caller handles input dealloc via generic dealloc or assume consumed?)
    // In this ABI, the caller owns the input buffer and should dealloc it if it allocated it via alloc.
    // Ideally, we provide a dealloc function for the input buffer too.
    unsafe {
        let _ = Vec::from_raw_parts(ptr, 0, len);
    }

    res_ptr
}

#[no_mangle]
pub extern "C" fn free_string(ptr: *mut c_char) {
    unsafe {
        if !ptr.is_null() {
            let _ = CString::from_raw(ptr);
        }
    }
}
```
