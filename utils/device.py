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
        """Build realistic fake step count payload for 7 days ending on today."""
        target_steps = steps or DEFAULT_STEPS
        DAY_MS = 86400000
        now_ms = int(time.time() * 1000)
        payload = []
        
        # Build 7 days: i=6 (6 days ago) to i=0 (today)
        for i in range(6, -1, -1):
            ts = now_ms - (i * DAY_MS)
            if i == 0:
                day_steps = target_steps
            else:
                day_steps = random.randint(25000, target_steps)
            distance = round(day_steps * 0.00075, 2)
            payload.append({
                "distance": distance,
                "steps": day_steps,
                "timestamp": int(ts)
            })
        return payload

    def _find_voucher_code(self, obj):
        """Recursively search for voucher code, tier, and expiry date in API response."""
        if not obj:
            return None, None, None
        if isinstance(obj, dict):
            code = (
                obj.get("giftVoucher") or
                obj.get("voucherCode") or
                obj.get("gift_voucher") or
                obj.get("code") or
                obj.get("couponCode") or
                (obj.get("voucher") if isinstance(obj.get("voucher"), str) else None)
            )
            if code and isinstance(code, str) and len(code) >= 4:
                tier = obj.get("tier") or obj.get("voucherTier")
                expiry = obj.get("giftVoucherExpiryDate") or obj.get("expiryDate") or obj.get("expiry_date")
                return code, tier, expiry

            for key in ("result", "data", "voucher", "giftVoucherDetails", "vouchers", "giftVouchers"):
                if key in obj:
                    c, t, e = self._find_voucher_code(obj[key])
                    if c:
                        return c, t or obj.get("tier"), e or obj.get("giftVoucherExpiryDate")
        elif isinstance(obj, list):
            for item in obj:
                c, t, e = self._find_voucher_code(item)
                if c:
                    return c, t, e
        return None, None, None

    def claim_reward(self, steps: int = None, campaign: str = None) -> dict:
        """Submit fake steps and claim reward with fallback voucher lookup."""
        body = self._build_steps_payload(steps)
        camp = campaign or DEFAULT_CAMPAIGN
        params = {"campaignName": camp}
        
        # Try primary v2 eligibility endpoint
        r = self._post("/v2/customers/bff/campaign/eligibility", body, params)
        
        if r and r.status_code == 200:
            try:
                data = r.json()
            except Exception:
                data = {}
            logger.info(f"Eligibility response: {data}")
            
            code, tier, expiry = self._find_voucher_code(data)
            if code:
                return {
                    "giftVoucher": code,
                    "tier": tier,
                    "giftVoucherExpiryDate": expiry
                }

            # Check for API message if no voucher in response
            res = data.get("result") or data.get("data") or data
            if isinstance(res, dict):
                msg = res.get("message") or res.get("reason") or res.get("status") or data.get("message")
                if msg:
                    self.last_error = str(msg)
                else:
                    self.last_error = f"API Status: {data}"
            elif isinstance(data, dict) and data.get("message"):
                self.last_error = str(data["message"])
        elif r:
            try:
                err_data = r.json()
                msg = err_data.get("message") or err_data.get("error") or err_data.get("result", {}).get("message")
                self.last_error = str(msg) if msg else f"{r.status_code}: {err_data}"
            except Exception:
                self.last_error = f"{r.status_code}: {r.text[:200]}"
        else:
            self.last_error = "No response from Lenskart API"

        # Fallback check: check user's vouchers directly from API endpoints
        vouchers = self.check_vouchers(camp)
        if vouchers:
            code, tier, expiry = self._find_voucher_code(vouchers)
            if code:
                return {
                    "giftVoucher": code,
                    "tier": tier,
                    "giftVoucherExpiryDate": expiry
                }

        return None

    def check_vouchers(self, campaign: str = None) -> list:
        """Check existing vouchers for logged in account across endpoints."""
        camp = campaign or DEFAULT_CAMPAIGN
        endpoints = [
            f"/v2/customers/me/giftVoucher?campaignName={camp}",
            "/v2/customers/me/giftVoucher",
            "/v1/customers/me/giftVoucher"
        ]
        for ep in endpoints:
            r = self._get(ep)
            if r and r.status_code == 200:
                try:
                    data = r.json()
                    res = data.get("result") or data.get("data") or data
                    if res:
                        return res
                except Exception:
                    pass
        return None

    @property
    def device_info(self) -> str:
        """Human-readable device string."""
        return f"{self.brand.title()} {self.model} (Android {self.android_version})"
