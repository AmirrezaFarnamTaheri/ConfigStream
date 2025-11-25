import zipfile
import io
import os
from typing import Optional

# Using cryptography for encryption if needed, though zipfile password is easier for simple obfuscation.
# The spec suggests AES encryption before zipping.
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


def encrypt_payload(data: bytes, key: bytes) -> bytes:
    """
    Encrypts data using AES-GCM.
    """
    iv = os.urandom(12)
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext: bytes = encryptor.update(data) + encryptor.finalize()
    tag: bytes = encryptor.tag  # type: ignore[assignment]
    result: bytes = iv + tag + ciphertext
    return result


def create_polyglot_image(
    image_path: str, config_json: str, output_path: str, password: Optional[str] = None
):
    """
    Creates a PNG + Zip polyglot file.
    """
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    # Prepare payload
    payload_bytes = config_json.encode("utf-8")

    # Optional: Encrypt payload manually if password provided
    # For now, we just Zip it.
    # NOTE: Standard zipfile in Python does not support strong encryption (AES).
    # It only supports legacy ZipCrypto.
    # To follow the spec "Encrypt ... then append", we can encrypt the JSON first.

    if password:
        # Pad key to 32 bytes
        key = password.encode("utf-8").ljust(32, b"\0")[:32]
        payload_bytes = encrypt_payload(payload_bytes, key)
        filename = "config.enc"
    else:
        filename = "config.json"

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(filename, payload_bytes)

    zip_data = zip_buffer.getvalue()

    with open(output_path, "wb") as out:
        out.write(image_bytes)
        out.write(zip_data)

    print(f"Created polyglot image at {output_path}")
