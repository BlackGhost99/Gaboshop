"""Payment provider utility stubs (simulation for local dev)."""
import hashlib
import hmac
from datetime import timedelta
from django.utils import timezone


def call_cinetpay_init(payload):
    return {"data": {"payment_token": "SIM_TOKEN", "payment_url": "https://cinetpay.local/pay"}}


def call_cinetpay_check(reference):
    return {"status": "SUCCESS", "reference": reference}


def call_cinetpay_refund(reference):
    return {"status": "REFUND_SUCCESS", "reference": reference}


def call_airtel_money_init(payload):
    return {"status": "SUCCESS", "transaction_id": f"AIR_{payload.get('reference','REF')}"}


def call_airtel_money_check(reference):
    return {"status": "SUCCESS", "reference": reference}


def call_moov_money_init(payload):
    return {"status": "SUCCESS", "transaction_id": f"MOOV_{payload.get('reference','REF')}"}


def call_moov_money_check(reference):
    return {"status": "SUCCESS", "reference": reference}


def verify_hmac_signature(raw_body: bytes, signature: str, secret: str = "secret") -> bool:
    computed = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)


def build_cinetpay_payload(intent, channels, lang):
    return {
        "reference": intent.reference,
        "amount": intent.amount,
        "currency": intent.currency,
        "channels": channels,
        "lang": lang,
        "expires_at": (intent.expires_at or (timezone.now() + timedelta(minutes=30))).isoformat(),
    }


def build_airtel_payload(intent, phone=None):
    return {
        "reference": intent.reference,
        "amount": intent.amount,
        "currency": intent.currency,
        "phone": phone,
    }


def build_moov_payload(intent, phone=None):
    return {
        "reference": intent.reference,
        "amount": intent.amount,
        "currency": intent.currency,
        "phone": phone,
    }
