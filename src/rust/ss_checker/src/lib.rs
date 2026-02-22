use std::ffi::CStr;
use std::os::raw::c_char;
use std::collections::HashSet;
use once_cell::sync::Lazy;

static VALID_METHODS: Lazy<HashSet<&'static str>> = Lazy::new(|| {
    let mut s = HashSet::new();
    // AEAD
    s.insert("aes-128-gcm");
    s.insert("aes-256-gcm");
    s.insert("chacha20-poly1305");
    s.insert("chacha20-ietf-poly1305");
    s.insert("xchacha20-ietf-poly1305");
    // Stream (Legacy/Deprecated but widely used)
    s.insert("aes-128-cfb");
    s.insert("aes-192-cfb");
    s.insert("aes-256-cfb");
    s.insert("aes-128-ctr");
    s.insert("aes-192-ctr");
    s.insert("aes-256-ctr");
    s.insert("rc4-md5");
    s.insert("chacha20");
    // Shadowsocks-2022 (New additions for Phase 6)
    s.insert("2022-blake3-aes-128-gcm");
    s.insert("2022-blake3-aes-256-gcm");
    s.insert("2022-blake3-chacha20-poly1305");
    s
});

#[no_mangle]
pub unsafe extern "C" fn verify_shadowsocks(json_ptr: *const c_char) -> i32 {
    if json_ptr.is_null() {
        return 0;
    }

    let c_str = match CStr::from_ptr(json_ptr).to_str() {
        Ok(s) => s,
        Err(_) => return 0,
    };

    // Lightweight JSON parsing (no heavy dependencies)
    // Extract "method" and "password"
    let method = match extract_json_string_value(c_str, "method") {
        Some(m) => m,
        None => return 0,
    };

    let password = match extract_json_string_value(c_str, "password") {
        Some(p) => p,
        None => return 0,
    };

    // Validation Rules
    if !VALID_METHODS.contains(method) {
        return 0;
    }

    // SS-2022 Key Length Validation
    if method.starts_with("2022-blake3-") {
        // Password must be base64 and decode to specific length
        // 16 bytes for aes-128, 32 bytes for others
        // For simple validation without base64 decode (to save deps), check length.
        // Base64 16 bytes -> 24 chars (approx)
        // Base64 32 bytes -> 44 chars (approx)
        let pw_len = password.len();
        if method.contains("aes-128-gcm") {
             if pw_len < 22 || pw_len > 26 { return 0; }
        } else {
             if pw_len < 42 || pw_len > 46 { return 0; }
        }
    } else {
        if password.is_empty() {
            return 0;
        }
    }

    1
}

// Helper to extract string value by key from JSON-like string
fn extract_json_string_value<'a>(json: &'a str, key: &str) -> Option<&'a str> {
    let key_pattern = format!("\"{}\"", key);
    let key_pos = json.find(&key_pattern)?;
    let after_key = &json[key_pos + key_pattern.len()..];
    let after_key = after_key.trim_start();
    if !after_key.starts_with(':') { return None; }
    let after_colon = after_key[1..].trim_start();
    if !after_colon.starts_with('"') { return None; }
    let value_start = 1;
    let value_bytes = after_colon.as_bytes();
    let mut i = value_start;
    while i < value_bytes.len() {
        if value_bytes[i] == b'\' { i += 2; continue; }
        if value_bytes[i] == b'"' { return Some(&after_colon[value_start..i]); }
        i += 1;
    }
    None
}
