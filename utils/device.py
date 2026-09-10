#!/usr/bin/env python3
"""Lenskart Fake Device - Spoofs Android device for API calls (Enhanced Multi-Header & Fallback Support)"""

import random
import time
import uuid
import hashlib
import base64
import logging
import requests
from datetime import datetime
from config import LENSKART_BASE_URL, DEFAULT_STEPS, DEFAULT_CAMPAIGN

logger = logging.getLogger(__name__)

# Device fingerprint pools
BRANDS = ["xiaomi", "realme", "samsung", "oneplus", "oppo", "vivo"]
MODELS = {
    "xiaomi": ["Mi 11X", "Redmi Note 10", "Mi 10", "Poco X3", "Redmi Note 12", "Poco F5"],
    "realme": ["RMX3031", "RMX3370", "RMX3360", "RMX3263", "RMX3771"],
    "samsung": ["SM-G998B", "SM-G991B", "SM-A526B", "SM-M515F", "SM-A546B"],
    "oneplus": ["LE2115", "LE2125", "KB2001", "IN2015", "CPH2449"],
    "oppo": ["CPH2207", "CPH2249", "CPH2217", "CPH2381"],
    "vivo": ["V2024", "V2036", "V2041", "V2115", "V2237"]
}
ANDROID_VERSIONS = ["12", "13", "14"]


class LenskartDevice:
    """Spoofed Android device for Lenskart API interaction."""

    def __init__(self, phone: str, phone_code: str = "+91"):
        self.phone = phone
        self.phone_code = phone_code
        self.brand = random.choice(BRANDS)
        self.model = random.choice(MODELS.get(self.brand, ["RMX3031"]))
        self.android_version = random.choice(ANDROID_VERSIONS)
        self.udid = uuid.uuid4().hex[:16]
        self.advertising_id = str(uuid.uuid4())
        self.build_version = f"TP1A.220905.00{random.randint(1, 9)}"
        self.session_token = None
        self.auth_token = None
        self.user_id = None
        self.customer_type = "EXISTING"
        self.session = requests.Session()
        self.x_assertion = self._generate_assertion()
        self.last_error = None  # Stores last API error for debugging

    @property
    def _bare_phone(self) -> str:
        """Phone number without country code prefix (e.g. '8564789268')."""
        p = self.phone
        if p.startswith('+'):
            p = p[1:]  # strip +
        code = self.phone_code.replace('+', '')
        if p.startswith(code):
            p = p[len(code):]
        return p

    def _generate_assertion(self) -> str:
        """Generate fake x-assertion header."""
        device_data = f"{self.udid}:{self.advertising_id}:{self.brand}:{self.model}:{self.phone}"
        hash_bytes = hashlib.sha256(device_data.encode()).digest()
        assertion = base64.b64encode(hash_bytes).decode('utf-8')
        assertion = assertion.replace('+', '-').replace('/', '_')
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        while len(assertion) < 100:
            assertion += random.choice(chars)
        return assertion[:100]

    def _headers(self, extra: dict = None) -> dict:
        """Build request headers with device fingerprint & multi-auth support."""
        h = {
            "Content-Type": "application/json; charset=UTF-8",
            "api_key": "valyoo123",
            "x-api-client": "android",
            "x-app-version": "5.8.2 (260713001)",
            "appversion": "5.8.2 (260713001)",
            "X-Build-Version": "260713001",
            "x-country-code": "IN",
            "x-country-code-override": "IN",
            "x-accept-language": "en",
            "accept-language": "en",
            "x-customer-type": self.customer_type,
            "udid": self.udid,
            "uniqueId": self.advertising_id[:16],
            "brand": self.brand,
            "model": self.model,
            "x-b3-traceid": str(int(time.time() * 1000)),
            "User-Agent": f"Dalvik/2.1.0 (Linux; U; Android {self.android_version}; {self.model} Build/{self.build_version})",
            "Accept-Encoding": "gzip",
            "Connection": "Keep-Alive",
        }
        if self.phone:
            h["x-customer-phone"] = self.phone
            h["x-customer-phone-code"] = self.phone_code.replace("+", "")
        if self.session_token:
            h["x-session-token"] = self.session_token
            h["authorization"] = f"Bearer {self.session_token}"
            h["Authorization"] = f"Bearer {self.session_token}"
        if self.x_assertion:
            h["x-assertion"] = self.x_assertion
        if extra:
            h.update(extra)
        return h

    def _post(self, path: str, body: dict = None, params: dict = None):
        """Make POST request to Lenskart API."""
        url = f"{LENSKART_BASE_URL}{path}"
        if params:
            url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
        try:
            r = self.session.post(url, headers=self._headers(), json=body, timeout=30)
            logger.info(f"POST {path} -> {r.status_code}")
            if r.status_code != 200:
                logger.warning(f"POST {path} body={body} -> {r.status_code}: {r.text[:300]}")
            return r
        except Exception as e:
            logger.error(f"POST {path} exception: {e}")
            self.last_error = str(e)
            return None

    def _get(self, path: str, params: dict = None):
        """Make GET request to Lenskart API."""
        url = f"{LENSKART_BASE_URL}{path}"
        if params:
            url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
        try:
            r = self.session.get(url, headers=self._headers(), timeout=30)
            logger.info(f"GET {path} -> {r.status_code}")
            if r.status_code != 200:
                logger.warning(f"GET {path} -> {r.status_code}: {r.text[:300]}")
            return r
        except Exception as e:
            logger.error(f"GET {path} exception: {e}")
            self.last_error = str(e)
            return None

    def create_session(self) -> bool:
        """Initialize API session."""
        r = self._post("/v2/sessions", {})
        if r and r.status_code == 200:
            data = r.json()
            res = data.get("result") or data.get("data") or {}
            self.session_token = res.get("id") or res.get("sessionToken") or res.get("token")
            return bool(self.session_token)
        self.last_error = f"Session failed ({r.status_code if r else 'No response'})"
        return False

    def send_otp(self) -> dict:
        """Send OTP to phone number."""
        if not self.session_token:
            self.last_error = "No session token"
            return None
        body = {"phoneCode": self.phone_code, "telephone": self._bare_phone}
        r = self._post("/v3/customers/sendOtp", body)
        if r and r.status_code == 200:
            data = r.json()
            res = data.get("result") or data.get("data") or {}
            self.customer_type = "NEW" if res.get("isNewUser") else "EXISTING"
            return res
        if r:
            try:
                self.last_error = f"{r.status_code}: {r.json()}"
            except Exception:
                self.last_error = f"{r.status_code}: {r.text[:200]}"
        else:
            self.last_error = "No response from API"
        return None

    def verify_otp(self, code: str) -> dict:
        """Verify OTP and authenticate session."""
        body = {"code": code, "phoneCode": self.phone_code, "telephone": self._bare_phone}
        r = self._post("/v2/customers/authenticate/mobile", body)
        if r and r.status_code == 200:
            data = r.json()
            res = data.get("result") or data.get("data") or {}
            token = res.get("token") or res.get("id") or res.get("sessionToken") or res.get("accessToken")
            if token:
                self.auth_token = token
                self.session_token = token
            self.user_id = res.get("user_id") or res.get("id")
            return res
        if r:
            try:
                self.last_error = f"{r.status_code}: {r.json()}"
            except Exception:
                self.last_error = f"{r.status_code}: {r.text[:200]}"
        return None

    def get_me(self) -> dict:
        """Get current user profile."""
        r = self._get("/v2/customers/me")
        if r and r.status_code == 200:
            data = r.json()
            res = data.get("result") or data.get("data") or {}
            self.user_id = res.get("id") or res.get("user_id")
            return data
        return None

    def _build_steps_payload(self, steps: int = None) -> list:
        """Build fake step count payload for 7 days."""
        steps = steps or DEFAULT_STEPS
        DAY_MS = 86400000
        ist_offset_ms = int(5.5 * 3600 * 1000)
        now_utc_ms = int(time.time() * 1000)
        now_ist_ms = now_utc_ms + ist_offset_ms
        today_midnight_ist = (now_ist_ms // DAY_MS) * DAY_MS
        today_midnight_utc = today_midnight_ist - ist_offset_ms
        step_counts = [0, 0, 0, 0, 0, 0, steps]
        payload = []
        for i in range(6, -1, -1):
            ts = today_midnight_utc - i * DAY_MS
            payload.append({"distance": 0.0, "steps": step_counts[i], "timestamp": int(ts)})
        return payload

    def claim_reward(self, steps: int = None, campaign: str = None) -> dict:
        """Submit fake steps and claim reward with fallback voucher lookup."""
        body = self._build_steps_payload(steps)
        params = {"campaignName": campaign or DEFAULT_CAMPAIGN}
        r = self._post("/v2/customers/bff/campaign/eligibility", body, params)
        
        if r and r.status_code == 200:
            data = r.json()
            res = data.get("result") or data.get("data") or data
            if isinstance(res, dict):
                code = (
                    res.get("giftVoucher") or
                    res.get("voucherCode") or
                    res.get("code") or
                    res.get("couponCode") or
                    (res.get("result") if isinstance(res.get("result"), dict) else {}).get("giftVoucher")
                )
                if code:
                    res["giftVoucher"] = code
                    return res

        # Fallback check: check user's vouchers directly from API
        vouchers = self.check_vouchers(campaign)
        if vouchers:
            if isinstance(vouchers, list) and len(vouchers) > 0:
                first = vouchers[0]
                if isinstance(first, dict):
                    code = first.get("giftVoucher") or first.get("voucherCode") or first.get("code")
                    if code:
                        first["giftVoucher"] = code
                        return first
            elif isinstance(vouchers, dict):
                code = vouchers.get("giftVoucher") or vouchers.get("voucherCode") or vouchers.get("code")
                if code:
                    vouchers["giftVoucher"] = code
                    return vouchers

        if r:
            try:
                self.last_error = f"{r.status_code}: {r.json()}"
            except Exception:
                self.last_error = f"{r.status_code}: {r.text[:200]}"
        return None

    def check_vouchers(self, campaign: str = None) -> dict:
        """Check existing vouchers for logged in account."""
        r = self._get("/v2/customers/me/giftVoucher", params={"campaignName": campaign or DEFAULT_CAMPAIGN})
        if r and r.status_code == 200:
            data = r.json()
            return data.get("result") or data.get("data") or data
        return None

    @property
    def device_info(self) -> str:
        """Human-readable device string."""
        return f"{self.brand.title()} {self.model} (Android {self.android_version})"
