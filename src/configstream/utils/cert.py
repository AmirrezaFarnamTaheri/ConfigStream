# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Certificate generation utilities.
Derived from nobetci-main.
"""
from typing import Dict
try:
    from OpenSSL import crypto
except ImportError:
    crypto = None  # Optional dependency

def generate_self_signed_cert(cn: str = "configstream-local") -> Dict[str, str]:
    """
    Generates a self-signed RSA-4096 certificate.
    Returns: {"cert": pem_string, "key": pem_string}
    """
    if not crypto:
        raise ImportError("pyopenssl is required for certificate generation.")

    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 4096)
    cert = crypto.X509()
    cert.get_subject().CN = cn
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60) # 10 years
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, "sha512")
    
    cert_pem = crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode("utf-8")
    key_pem = crypto.dump_privatekey(crypto.FILETYPE_PEM, k).decode("utf-8")

    return {"cert": cert_pem, "key": key_pem}
