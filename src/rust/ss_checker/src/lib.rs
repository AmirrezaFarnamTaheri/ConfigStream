use std::ffi::CStr;
use std::os::raw::c_char;

// FFI function for Shadowsocks config validation.
// Called from Python via ctypes to verify config structure and cipher validity.
//
// [FIX] Replaced naive substring matching with proper field extraction.
// Previously, `str_slice.contains("aes-256-gcm")` would match the cipher name
// ANYWHERE in the JSON (e.g., in a "description" field), producing false positives.
// Now we extract the actual "method" field value and validate it against a whitelist.
//
// Also expanded the valid methods list to include xchacha20-ietf-poly1305 and
// 2022-blake3-chacha20-poly1305 which are commonly used in the wild.

/// Valid Shadowsocks encryption methods (must match sing-box schema).
const VALID_METHODS: &[&str] = &[
    "aes-128-gcm",
    "aes-256-gcm",
    "chacha20-ietf-poly1305",
    "xchacha20-ietf-poly1305",
    "2022-blake3-aes-128-gcm",
    "2022-blake3-aes-256-gcm",
    "2022-blake3-chacha20-poly1305",
    "aes-128-cfb",
    "aes-192-cfb",
    "aes-256-cfb",
    "aes-128-ctr",
    "aes-192-ctr",
    "aes-256-ctr",
    "rc4-md5",
    "chacha20-ietf",
    "xchacha20",
    "none",
];

#[no_mangle]
pub extern "C" fn verify_shadowsocks(config_json: *const c_char) -> i32 {
    // 0 = False/Fail, 1 = True/Pass
    if config_json.is_null() {
        return 0;
    }

    let c_str = unsafe { CStr::from_ptr(config_json) };
    let str_slice = match c_str.to_str() {
        Ok(s) => s,
        Err(_) => return 0,
    };

    // Extract JSON field values without pulling in serde_json (keeps binary small).
    // We use a simple but correct extraction: find `"field":"value"` patterns
    // accounting for whitespace around the colon.
    let method = extract_json_string_value(str_slice, "method");
    let password = extract_json_string_value(str_slice, "password");

    // Both method and password must be present and non-empty
    let method_str = match method {
        Some(m) if !m.is_empty() => m,
        _ => return 0,
    };

    match password {
        Some(p) if !p.is_empty() => {},
        _ => return 0,
    }

    // Validate method against whitelist
    for valid in VALID_METHODS.iter() {
        if method_str == *valid {
            return 1;
        }
    }

    0
}

/// Extract a string value for a given key from a JSON string.
/// Handles: `"key" : "value"` with optional whitespace around `:`.
/// Returns None if key not found or value is not a string.
fn extract_json_string_value<'a>(json: &'a str, key: &str) -> Option<&'a str> {
    // Build the search pattern: `"key"`
    let key_pattern = format!("\"{}\"", key);

    let key_pos = json.find(&key_pattern)?;
    let after_key = &json[key_pos + key_pattern.len()..];

    // Skip whitespace and find ':'
    let after_key = after_key.trim_start();
    if !after_key.starts_with(':') {
        return None;
    }
    let after_colon = after_key[1..].trim_start();

    // Value must start with '"'
    if !after_colon.starts_with('"') {
        return None;
    }

    // Find the closing quote (handle escaped quotes)
    let value_start = 1; // skip opening quote
    let value_bytes = after_colon.as_bytes();
    let mut i = value_start;
    while i < value_bytes.len() {
        if value_bytes[i] == b'\\' {
            i += 2; // skip escaped character
            continue;
        }
        if value_bytes[i] == b'"' {
            return Some(&after_colon[value_start..i]);
        }
        i += 1;
    }

    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_json_string_value() {
        let json = r#"{"method": "aes-256-gcm", "password": "test123", "server": "1.2.3.4"}"#;
        assert_eq!(extract_json_string_value(json, "method"), Some("aes-256-gcm"));
        assert_eq!(extract_json_string_value(json, "password"), Some("test123"));
        assert_eq!(extract_json_string_value(json, "server"), Some("1.2.3.4"));
        assert_eq!(extract_json_string_value(json, "missing"), None);
    }

    #[test]
    fn test_no_false_positive_from_description() {
        // Previously, substring matching would match "aes-256-gcm" in the description
        let json = r#"{"description": "uses aes-256-gcm method", "method": "invalid", "password": "x"}"#;
        assert_eq!(extract_json_string_value(json, "method"), Some("invalid"));
        // verify_shadowsocks should reject this because "invalid" is not in VALID_METHODS
    }

    #[test]
    fn test_valid_config() {
        let json = r#"{"method": "aes-256-gcm", "password": "mypass"}"#;
        let c_str = std::ffi::CString::new(json).unwrap();
        assert_eq!(unsafe { verify_shadowsocks(c_str.as_ptr()) }, 1);
    }

    #[test]
    fn test_invalid_method() {
        let json = r#"{"method": "invalid-cipher", "password": "mypass"}"#;
        let c_str = std::ffi::CString::new(json).unwrap();
        assert_eq!(unsafe { verify_shadowsocks(c_str.as_ptr()) }, 0);
    }

    #[test]
    fn test_missing_password() {
        let json = r#"{"method": "aes-256-gcm"}"#;
        let c_str = std::ffi::CString::new(json).unwrap();
        assert_eq!(unsafe { verify_shadowsocks(c_str.as_ptr()) }, 0);
    }
}
