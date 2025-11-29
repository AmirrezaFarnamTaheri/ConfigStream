// Loads configuration from a Polyglot Image (PNG + Zip)
// Requires 'unzipit' library (https://unpkg.com/unzipit@1.4.0/dist/unzipit.module.js)

import { unzip } from 'https://unpkg.com/unzipit@1.4.0/dist/unzipit.module.js';

export async function loadPolyglot(url, password = null) {
    console.log(`Fetching polyglot image from ${url}...`);
    const response = await fetch(url);
    if (!response.ok) throw new Error("Failed to fetch image");

    const blob = await response.blob();

    // unzipit scans for the PK signature at the end of the file
    const { entries } = await unzip(blob);

    let content;
    if (entries['config.json']) {
        content = await entries['config.json'].text();
        return JSON.parse(content);
    } else if (entries['config.enc']) {
        // Handle encrypted payload
        const encryptedBytes = await entries['config.enc'].arrayBuffer();
        if (!password) throw new Error("Password required for encrypted config");

        // Decrypt logic matching python's AES-GCM
        content = await decryptPayload(encryptedBytes, password);
        return JSON.parse(new TextDecoder().decode(content));
    } else {
        throw new Error("No config found in image");
    }
}

async function decryptPayload(buffer, password) {
    // Expected format: IV (12) + Tag (16) + Ciphertext
    const iv = buffer.slice(0, 12);
    const tag = buffer.slice(12, 28); // not needed explicitly for WebCrypto GCM (it's appended)
    // WebCrypto expects Tag to be at the end of ciphertext.
    // Python cryptography library: iv + tag + ciphertext
    // WebCrypto decrypt: ciphertext + tag

    const ciphertext = buffer.slice(28);
    const tagBytes = new Uint8Array(buffer.slice(12, 28));
    const encrypted = new Uint8Array(ciphertext.byteLength + tagBytes.byteLength);
    encrypted.set(new Uint8Array(ciphertext));
    encrypted.set(tagBytes, ciphertext.byteLength);

    const keyMaterial = await window.crypto.subtle.importKey(
        "raw",
        new TextEncoder().encode(password.padEnd(32, '\0').slice(0, 32)),
        "AES-GCM",
        false,
        ["decrypt"]
    );

    return await window.crypto.subtle.decrypt(
        {
            name: "AES-GCM",
            iv: iv
        },
        keyMaterial,
        encrypted
    );
}
