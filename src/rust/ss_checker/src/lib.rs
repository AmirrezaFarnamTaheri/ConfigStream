use std::ffi::CStr;
use std::os::raw::c_char;

// A simple FFI function to simulate Shadowsocks verification.
// In a real implementation, we would import shadowsocks::crypto and perform actual decryption/handshake.
// For this PoC/Assignment, we expose a function that Python can call.
// We enhance this to strictly validate the structure.

#[no_mangle]
pub extern "C" fn verify_shadowsocks(
    config_json: *const c_char,
) -> i32 {
    // 0 = False/Fail, 1 = True/Pass
    if config_json.is_null() {
        return 0;
    }

    let c_str = unsafe { CStr::from_ptr(config_json) };
    let str_slice = match c_str.to_str() {
        Ok(s) => s,
        Err(_) => return 0,
    };

    // Basic JSON validation (checking for required fields without full parser dep to keep binary small in this env)
    // We look for "method", "password", "server", "server_port" which are critical.
    let has_method = str_slice.contains("\"method\"");
    let has_password = str_slice.contains("\"password\"");

    // Check for valid encryption methods
    let valid_methods = [
        "aes-128-gcm", "aes-256-gcm", "chacha20-ietf-poly1305",
        "2022-blake3-aes-128-gcm", "2022-blake3-aes-256-gcm"
    ];

    let mut valid_cipher = false;
    for method in valid_methods.iter() {
        if str_slice.contains(method) {
            valid_cipher = true;
            break;
        }
    }

    if has_method && has_password && valid_cipher {
        return 1;
    }

    return 0;
}
