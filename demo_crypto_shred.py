import os
import sys
import json

# Ensure project root is on sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from privacy.crypto_shred import encrypt_field, decrypt_field, erase_subject

# 1. Define sensitive patient data
patient_id = "PATIENT_9084"
patient_info = "Patient Name: Jane Doe | DOB: 1989-10-12 | Diagnosis: Acute Appendicitis | Medication: Ibuprofen 400mg"

print("="*60)
print("🛡️  SENTINELHEALTH PRIVACY & CRYPTO-SHREDDING DEMO")
print("="*60)
print(f"Original Sensitive PHI Data:\n  '{patient_info}'\n")

# 2. Encrypt the data
print("[*] Encrypting patient information...")
ciphertext_bytes = encrypt_field(patient_id, patient_info)
ciphertext_hex = ciphertext_bytes.hex()
print(f"Encrypted Ciphertext (stored in logs):\n  {ciphertext_hex}\n")

# Write to mock log entry
mock_log = {
    "event_id": "e456-bf89-4112",
    "timestamp": "2026-06-08T21:46:00Z",
    "patient_id": patient_id,
    "user_display_name_enc": ciphertext_hex
}

mock_log_path = os.path.join("logs", "mock_patient_log.json")
with open(mock_log_path, "w") as f:
    json.dump(mock_log, f, indent=2)
print(f"✅ Mock log entry written to: {mock_log_path}")
print(f"✅ Encryption key created in: config/shred_keystore.json")
print("="*60)
print("👉 Check config/shred_keystore.json in VS Code now! You will see the active key.")
input("👉 Press [Enter] in this terminal when you are ready to trigger crypto-shredding...")
print("="*60)

# 3. Decrypt the data (while key exists)
print("[*] Attempting decryption (key is active)...")
decrypted_info = decrypt_field(patient_id, bytes.fromhex(ciphertext_hex))
print(f"Decrypted Result:\n  '{decrypted_info}'\n")

# 4. Trigger Crypto-Shredding (Right to Erasure)
print("="*60)
print("⚠️  USER TRIGGERS 'RIGHT TO BE FORGOTTEN' (DPDP / GDPR)")
print("="*60)
print(f"[*] Shredding key for subject ID '{patient_id}'...")
erase_subject(patient_id)
print("✅ Key destroyed from config/shred_keystore.json.")
print("👉 Check config/shred_keystore.json again in VS Code! It is now empty.")
input("👉 Press [Enter] to test decryption after key deletion...")
print("="*60)

# 5. Try decrypting again
print("[*] Attempting decryption again after key erasure...")
try:
    decrypt_field(patient_id, bytes.fromhex(ciphertext_hex))
except KeyError as e:
    print(f"❌ DECRYPTION FAILED: {e}")
    print("\n✅ Success: The plaintext data is now permanently unrecoverable 'digital dust'.")
    print("   The log file itself remains intact for compliance audits (no broken hash chains).")
print("="*60)
