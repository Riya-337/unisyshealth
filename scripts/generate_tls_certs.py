#!/usr/bin/env python3
"""
scripts/generate_tls_certs.py — Generate self-signed TLS certificates for local LAN services.

Creates:
  - config/certs/server.key  (Private Key, 0600 permissions)
  - config/certs/server.crt  (Self-signed Certificate)

Usage:
  python3 scripts/generate_tls_certs.py
"""

import os
import sys
import subprocess
from datetime import datetime, timedelta, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_HERE)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from _paths import CONFIG_DIR

CERTS_DIR = os.path.join(CONFIG_DIR, "certs")
KEY_FILE  = os.path.join(CERTS_DIR, "server.key")
CRT_FILE  = os.path.join(CERTS_DIR, "server.crt")


def generate_self_signed_cert():
    os.makedirs(CERTS_DIR, exist_ok=True)

    if os.path.exists(KEY_FILE) and os.path.exists(CRT_FILE):
        print(f"[+] TLS certificates already exist in {CERTS_DIR}")
        return CERTS_DIR

    print(f"[*] Generating self-signed TLS certificates for local LAN in {CERTS_DIR}...")
    
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import ipaddress

        # Generate RSA Key
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Local"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Hospital LAN"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SentiHealth On-Prem"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now(timezone.utc)
        ).not_valid_after(
            datetime.now(timezone.utc) + timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("127.0.0.1"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            ]),
            critical=False,
        ).sign(key, hashes.SHA256())

        # Write private key with 0600 permissions
        with open(KEY_FILE, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ))
        os.chmod(KEY_FILE, 0o600)

        # Write certificate
        with open(CRT_FILE, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        print(f"[+] Successfully generated self-signed TLS certificates:")
        print(f"    - Key: {KEY_FILE} (0600)")
        print(f"    - Cert: {CRT_FILE}")

    except ImportError:
        # Fallback to OpenSSL CLI if cryptography package is missing
        cmd = [
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", KEY_FILE, "-out", CRT_FILE,
            "-days", "365", "-nodes",
            "-subj", "/C=US/ST=Local/L=Hospital LAN/O=SentiHealth/CN=localhost"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            os.chmod(KEY_FILE, 0o600)
            print(f"[+] Successfully generated TLS certificate via openssl CLI.")
        else:
            print(f"[!] OpenSSL certificate generation failed: {res.stderr}")
            sys.exit(1)

    return CERTS_DIR


if __name__ == "__main__":
    generate_self_signed_cert()
