// frontend/assets/js/stego.js

const logger = window.createLogger ? window.createLogger("Stego") : console;

// Legacy marker kept for backward compatibility with old append-mode artifacts.
const LEGACY_MAGIC_MARKER = "CSTREAM_PAYLOAD_START>>";
const LSB_MAGIC = "CSP2";
const LSB_HEADER_SIZE = 8;

function _configuredSecretKey() {
  const runtimeConfig = window.CS_RUNTIME_CONFIG || {};
  return typeof runtimeConfig.STEGO_KEY === "string" ? runtimeConfig.STEGO_KEY : "";
}

function _isPlaceholderSecretKey(secretKey) {
  return secretKey === "PLACEHOLDER_" + "KEY_INJECTED_BY_CI";
}

// A valid Fernet key is 32 bytes encoded as URL-safe base64 = 44 characters
// (no padding).  Accept anything ≥ 40 to be tolerant of minor encoding
// variants while still rejecting clearly wrong values.
const MIN_VALID_KEY_LENGTH = 40;

function _ensureConfiguredKey() {
  const secretKey = _configuredSecretKey();
  if (
    _isPlaceholderSecretKey(secretKey) ||
    typeof secretKey !== "string" ||
    secretKey.length < MIN_VALID_KEY_LENGTH
  ) {
    throw new Error(
      "Stego key not configured or too short. This deployment did not inject a valid STEGO_KEY."
    );
  }
  return secretKey;
}

function _bytesToUtf8(bytes) {
  return new TextDecoder().decode(bytes);
}

function _utf8ToBytes(text) {
  return new TextEncoder().encode(text);
}

function _bytesToBase64Url(bytes) {
  let binary = "";
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function _base64UrlToBytes(input) {
  const normalized = input.replace(/-/g, "+").replace(/_/g, "/");
  const pad = normalized.length % 4;
  const padded = pad ? normalized + "=".repeat(4 - pad) : normalized;
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

async function _sha256Bytes(inputBytes) {
  const digest = await crypto.subtle.digest("SHA-256", inputBytes);
  return new Uint8Array(digest);
}

function _gcd(a, b) {
  let x = Math.abs(a);
  let y = Math.abs(b);
  while (y !== 0) {
    const t = y;
    y = x % y;
    x = t;
  }
  return x;
}

function _u64From(bytes, start) {
  let v = 0n;
  for (let i = 0; i < 8; i++) {
    v = (v << 8n) | BigInt(bytes[start + i]);
  }
  return v;
}

async function _deriveOffsets(secretKey, carrierLen) {
  if (carrierLen <= 0) throw new Error("Invalid stego carrier length");
  const hash = await _sha256Bytes(_utf8ToBytes(secretKey));
  const start = Number(_u64From(hash, 0) % BigInt(carrierLen));
  let stride = Number(_u64From(hash, 8) % BigInt(carrierLen)) | 1;
  if (stride <= 0) stride = 1;
  while (_gcd(stride, carrierLen) !== 1) {
    stride = (stride + 2) % carrierLen;
    if (stride === 0) stride = 1;
  }
  return { start, stride };
}

function _collectCarrierPositions(imageData) {
  const positions = [];
  for (let i = 0; i < imageData.length; i += 4) {
    positions.push(i, i + 1, i + 2); // RGB only
  }
  return positions;
}

function _extractPayloadBytes(imageData, positions, start, stride, byteLen) {
  const out = new Uint8Array(byteLen);
  const totalBits = byteLen * 8;
  for (let bitIndex = 0; bitIndex < totalBits; bitIndex++) {
    const posIdx = (start + bitIndex * stride) % positions.length;
    const dataIdx = positions[posIdx];
    const bit = imageData[dataIdx] & 1;
    const outByte = Math.floor(bitIndex / 8);
    out[outByte] = (out[outByte] << 1) | bit;
  }
  return out;
}

function _parseLsbHeader(headerBytes) {
  const magic = _bytesToUtf8(headerBytes.slice(0, 4));
  if (magic !== LSB_MAGIC) throw new Error("LSB stego marker not found");
  const version = headerBytes[4];
  if (version !== 1) throw new Error(`Unsupported stego payload version: ${version}`);
  const tokenLen = (headerBytes[6] << 8) | headerBytes[7];
  return { tokenLen };
}

async function _decodeFernetToken(tokenBytes, secretKey) {
  const keyBytes = _base64UrlToBytes(secretKey);
  if (keyBytes.length !== 32) throw new Error("Invalid Fernet key length");

  const signingKey = keyBytes.slice(0, 16);
  const encryptionKey = keyBytes.slice(16, 32);

  const tokenBase64 = _bytesToUtf8(tokenBytes);
  const tokenRaw = _base64UrlToBytes(tokenBase64);
  if (tokenRaw.length < 1 + 8 + 16 + 32) throw new Error("Invalid Fernet token");

  const macStart = tokenRaw.length - 32;
  const signedData = tokenRaw.slice(0, macStart);
  const tokenMac = tokenRaw.slice(macStart);
  const iv = tokenRaw.slice(9, 25);
  const ciphertext = tokenRaw.slice(25, macStart);

  const hmacKey = await crypto.subtle.importKey(
    "raw",
    signingKey,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["verify"]
  );
  const macValid = await crypto.subtle.verify("HMAC", hmacKey, tokenMac, signedData);
  if (!macValid) throw new Error("Fernet HMAC verification failed");

  const aesKey = await crypto.subtle.importKey(
    "raw",
    encryptionKey,
    { name: "AES-CBC" },
    false,
    ["decrypt"]
  );
  const plaintextBuf = await crypto.subtle.decrypt(
    { name: "AES-CBC", iv },
    aesKey,
    ciphertext
  );
  const plain = new Uint8Array(plaintextBuf);

  // WebCrypto returns raw plaintext for AES-CBC, so remove PKCS#7 padding.
  const pad = plain[plain.length - 1];
  if (pad <= 0 || pad > 16 || pad > plain.length) {
    throw new Error("Invalid Fernet padding");
  }
  for (let i = plain.length - pad; i < plain.length; i++) {
    if (plain[i] !== pad) throw new Error("Invalid Fernet padding bytes");
  }
  return plain.slice(0, plain.length - pad);
}

async function _extractLsbPayload(buffer, secretKey) {
  const blob = new Blob([buffer], { type: "image/png" });
  const bitmap = await createImageBitmap(blob);
  const canvas = document.createElement("canvas");
  canvas.width = bitmap.width;
  canvas.height = bitmap.height;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) throw new Error("Canvas context unavailable for stego decode");
  ctx.drawImage(bitmap, 0, 0);

  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
  const positions = _collectCarrierPositions(imageData);
  const { start, stride } = await _deriveOffsets(secretKey, positions.length);

  const header = _extractPayloadBytes(
    imageData,
    positions,
    start,
    stride,
    LSB_HEADER_SIZE
  );
  const { tokenLen } = _parseLsbHeader(header);

  // Guard against NaN/undefined from CS_CONSTANTS: fall back to the hard-coded
  // default if the value is not a positive finite number.
  const rawMaxSize =
    window.CS_CONSTANTS && typeof window.CS_CONSTANTS.STEGO_MAX_PAYLOAD_SIZE === "number"
      ? window.CS_CONSTANTS.STEGO_MAX_PAYLOAD_SIZE
      : NaN;
  const maxSize = Number.isFinite(rawMaxSize) && rawMaxSize > 0 ? rawMaxSize : 2_000_000;
  if (tokenLen <= 0 || !Number.isInteger(tokenLen) || tokenLen > maxSize) {
    throw new Error(`Invalid stego token length: ${tokenLen}`);
  }

  const fullPayload = _extractPayloadBytes(
    imageData,
    positions,
    start,
    stride,
    LSB_HEADER_SIZE + tokenLen
  );
  const tokenBytes = fullPayload.slice(LSB_HEADER_SIZE);
  const compressed = await _decodeFernetToken(tokenBytes, secretKey);
  const jsonString = pako.inflate(compressed, { to: "string" });
  return JSON.parse(jsonString);
}

function _extractLegacyPayload(buffer, secretKey) {
  const markerBytes = _utf8ToBytes(LEGACY_MAGIC_MARKER);
  const data = new Uint8Array(buffer);
  let markerPos = -1;

  // Scan tail window for marker.
  const maxWindow = window.CS_CONSTANTS ? window.CS_CONSTANTS.STEGO_SEARCH_WINDOW : 500000;
  const start = Math.max(0, data.length - maxWindow);
  for (let i = start; i < data.length - markerBytes.length; i++) {
    let match = true;
    for (let j = 0; j < markerBytes.length; j++) {
      if (data[i + j] !== markerBytes[j]) {
        match = false;
        break;
      }
    }
    if (match) {
      markerPos = i + markerBytes.length;
      break;
    }
  }
  if (markerPos < 0) throw new Error("No legacy stego marker found");

  // Legacy path still uses fernetBrowser for old append mode.
  if (typeof fernet === "undefined") {
    throw new Error("Legacy stego decode requires fernetBrowser script");
  }
  const encryptedStr = _bytesToUtf8(data.slice(markerPos));
  const secret = new fernet.Secret(secretKey);
  const token = new fernet.Token({ secret, token: encryptedStr, ttl: 0 });
  const blob = token.decode();
  if (blob.length <= 32) throw new Error("Invalid legacy stego payload");
  const compressed = blob.slice(32);
  const jsonString = pako.inflate(compressed, { to: "string" });
  return JSON.parse(jsonString);
}

async function fetchStegoConfig(imageUrl) {
  try {
    const secretKey = _ensureConfiguredKey();
    if (window.updateStatus) updateStatus("Fetching stealth image...");

    const response = await fetch(imageUrl, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const buffer = await response.arrayBuffer();

    try {
      return await _extractLsbPayload(buffer, secretKey);
    } catch (lsbError) {
      logger.warn("LSB decode failed, trying legacy mode:", lsbError);
      return _extractLegacyPayload(buffer, secretKey);
    }
  } catch (e) {
    logger.error("Stego extraction failed:", e);
    alert("Failed to load stealth config. See console.");
    return null;
  }
}

function loadAndApplyStego(url) {
  fetchStegoConfig(url).then((config) => {
    if (!config) return;
    const blob = new Blob([JSON.stringify(config, null, 2)], {
      type: "application/json",
    });
    const dlUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = dlUrl;
    a.download = "singbox-stealth.json";
    // Append → click → schedule revoke. Revoking synchronously before the
    // browser has dispatched the download causes a race where some browsers
    // (especially Firefox) cancel the download before it starts.  A short
    // setTimeout gives the UA time to initiate the download.
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(dlUrl), 5000);
  });
}

window.stego = {
  extract: fetchStegoConfig,
  loadAndApplyStego,
};
