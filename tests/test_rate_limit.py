"""
tests/test_rate_limit.py — Test rate limiting and account lockout after 5 failed attempts.
"""

import sys
import os
import pytest
import json

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from dashboard import app, init_db, _failed_login_attempts, _failed_attempts_lock


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        init_db()
        with _failed_attempts_lock:
            _failed_login_attempts.clear()
        yield client


def test_rate_limiting_after_5_failed_logins(client):
    test_user = "admin"
    bad_payload = {"username": test_user, "password": "wrongpassword123"}

    # 1. Attempt 4 invalid logins — should receive 401 Unauthorized
    for i in range(4):
        res = client.post("/api/auth/login", json=bad_payload)
        assert res.status_code == 401, f"Attempt {i+1} expected 401, got {res.status_code}"

    # 2. 5th invalid login attempt — triggers 5th failure threshold
    res5 = client.post("/api/auth/login", json=bad_payload)
    assert res5.status_code in (401, 429), f"5th attempt expected 401 or 429, got {res5.status_code}"

    # 3. 6th login attempt — MUST be blocked with 429 Too Many Requests (Account Locked)
    res6 = client.post("/api/auth/login", json=bad_payload)
    assert res6.status_code == 429, f"6th attempt expected 429, got {res6.status_code}"
    data = res6.get_json()
    assert "locked" in data["message"].lower() or "5 consecutive" in data["message"].lower()


def test_rate_limiting_verify_otp(client):
    test_user = "admin"
    bad_otp_payload = {"username": test_user, "code": "999999"}

    # 1. Attempt 5 invalid OTP verifications
    for i in range(5):
        client.post("/api/auth/verify-otp", json=bad_otp_payload)

    # 2. 6th OTP attempt — MUST be blocked with 429
    res = client.post("/api/auth/verify-otp", json=bad_otp_payload)
    assert res.status_code == 429
    data = res.get_json()
    assert "locked" in data["message"].lower()
