"""Payment provider utilities (Cinetpay + SingPay)."""
import hashlib
import hmac
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
import logging

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def call_cinetpay_init(payload):
    return {"data": {"payment_token": "SIM_TOKEN", "payment_url": "https://cinetpay.local/pay"}}


def call_cinetpay_check(reference):
    return {"status": "SUCCESS", "reference": reference}


def call_cinetpay_refund(reference, amount=None):
    payload = {"reference": reference}
    if amount is not None:
        payload["amount"] = amount
    return {"status": "REFUND_SUCCESS", **payload}


def _singpay_headers(wallet_id=None, require_wallet=True):
    client_id = getattr(settings, "SINGPAY_CLIENT_ID", "") or ""
    client_secret = getattr(settings, "SINGPAY_CLIENT_SECRET", "") or ""
    wallet = wallet_id or getattr(settings, "SINGPAY_WALLET_ID", "") or ""
    headers = {
        "x-client-id": client_id,
        "x-client-secret": client_secret,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if require_wallet and wallet:
        headers["x-wallet"] = wallet
        # Some gateways/documentation variants expect this alias.
        headers["x-wallet-id"] = wallet
    return headers


def _singpay_base_url():
    base = getattr(settings, "SINGPAY_BASE_URL", "") or ""
    return base.rstrip("/")


def _singpay_timeout():
    return int(getattr(settings, "SINGPAY_TIMEOUT", 30) or 30)


def _singpay_missing_config(wallet_id=None, require_wallet=True):
    client_id = getattr(settings, "SINGPAY_CLIENT_ID", "") or ""
    client_secret = getattr(settings, "SINGPAY_CLIENT_SECRET", "") or ""
    wallet = wallet_id or getattr(settings, "SINGPAY_WALLET_ID", "") or ""
    missing = []
    if not client_id:
        missing.append("SINGPAY_CLIENT_ID")
    if not client_secret:
        missing.append("SINGPAY_CLIENT_SECRET")
    if require_wallet and not wallet:
        missing.append("SINGPAY_WALLET_ID")
    return missing


def _normalize_amount(amount):
    if amount is None:
        return None
    try:
        return int(Decimal(str(amount)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except Exception:
        return amount


def _normalize_msisdn(phone):
    if phone is None:
        return None
    normalized = (
        str(phone)
        .strip()
        .replace(" ", "")
        .replace("-", "")
        .replace(".", "")
    )
    if normalized.startswith("+"):
        normalized = normalized[1:]
    # SingPay attend le numéro au format local gabonais : 9 chiffres avec le 0 (ex. 074000000).
    if normalized.startswith("241") and len(normalized) == 11:
        normalized = normalized[3:]
    if len(normalized) == 8 and normalized.isdigit():
        normalized = "0" + normalized
    return normalized


def _singpay_request(method, path, payload=None, params=None, wallet_id=None, require_wallet=True):
    base = _singpay_base_url()
    if not base:
        return {"error": "SINGPAY_BASE_URL manquant"}
    missing = _singpay_missing_config(wallet_id, require_wallet=require_wallet)
    if missing:
        return {"error": "Config SingPay manquante", "missing": missing}
    url = f"{base}{path}"
    try:
        resp = requests.request(
            method,
            url,
            headers=_singpay_headers(wallet_id, require_wallet=require_wallet),
            json=payload,
            params=params,
            timeout=_singpay_timeout(),
        )
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
        if resp.status_code >= 400:
            # Réponse complète de SingPay dans les journaux Render (jamais nos clés).
            logger.error("SingPay %s %s -> HTTP %s : %s", method, path, resp.status_code, str(data)[:2000])
            return {
                "error": f"SingPay HTTP {resp.status_code}",
                "response": data,
                "request": {"method": method, "path": path},
            }
        return data
    except Exception as exc:
        logger.error("SingPay %s %s -> echec de l'appel : %s", method, path, exc)
        return {"error": f"SingPay request failed: {exc}"}


def call_singpay_payment(
    operator,
    amount,
    reference,
    phone,
    portefeuille=None,
    disbursement=None,
    is_transfer=False,
):
    if operator == "airtel":
        path = "/74/paiement"
    elif operator == "moov":
        path = "/62/paiement"
    elif operator == "maviance":
        path = "/maviance/paiement"
    else:
        return {"error": f"Operateur SingPay non supporte: {operator}"}

    normalized_amount = _normalize_amount(amount)
    normalized_phone = _normalize_msisdn(phone)

    payload = {
        "amount": normalized_amount,
        "reference": reference,
        "client_msisdn": normalized_phone,
        "portefeuille": portefeuille or getattr(settings, "SINGPAY_WALLET_ID", ""),
    }
    if disbursement:
        payload["disbursement"] = disbursement
    if is_transfer:
        payload["isTransfer"] = True

    return _singpay_request("POST", path, payload=payload, wallet_id=payload["portefeuille"])


def call_airtel_money_init(payload=None, **kwargs):
    # Support both old signature (payload dict) and new kwargs
    if payload is None:
        payload = kwargs
    return call_singpay_payment(
        "airtel",
        amount=payload.get("amount"),
        reference=payload.get("reference"),
        phone=payload.get("phone") or payload.get("client_msisdn"),
        portefeuille=payload.get("portefeuille"),
        disbursement=payload.get("disbursement"),
        is_transfer=payload.get("isTransfer") or payload.get("is_transfer", False),
    )


def call_singpay_status(transaction_id):
    # Status endpoint requires only client_id/client_secret per SingPay docs.
    return _singpay_request(
        "GET",
        f"/transaction/api/status/{transaction_id}",
        require_wallet=False,
    )


def call_singpay_transfer(reference, disbursement, amount, portefeuille=None):
    payload = {
        "reference": reference,
        "disbursement": disbursement,
        "amount": amount,
    }
    wallet_id = portefeuille or getattr(settings, "SINGPAY_WALLET_ID", "")
    return _singpay_request("POST", "/transfer", payload=payload, wallet_id=wallet_id)


def call_singpay_wallet_transactions(portefeuille_id=None):
    wallet_id = portefeuille_id or getattr(settings, "SINGPAY_WALLET_ID", "")
    if not wallet_id:
        return {"error": "SINGPAY_WALLET_ID manquant"}
    return _singpay_request(
        "GET",
        f"/transaction/api/search/by-portefeuille/{wallet_id}",
        wallet_id=wallet_id,
        require_wallet=True,
    )


def call_singpay_transaction_by_reference(reference, portefeuille_id=None):
    wallet_id = portefeuille_id or getattr(settings, "SINGPAY_WALLET_ID", "")
    if not wallet_id:
        return {"error": "SINGPAY_WALLET_ID manquant"}
    return _singpay_request(
        "GET",
        f"/transaction/api/search/by-reference/{reference}",
        wallet_id=wallet_id,
        require_wallet=True,
    )


def call_singpay_transaction_by_id(transaction_id):
    return _singpay_request(
        "GET",
        f"/transaction/api/{transaction_id}",
        require_wallet=False,
    )


def call_singpay_transfers_by_reference(reference):
    return _singpay_request(
        "GET",
        f"/transfer/transaction/{reference}",
        require_wallet=False,
    )


def call_airtel_money_check(reference):
    return call_singpay_status(reference)


def call_moov_money_init(payload=None, **kwargs):
    if payload is None:
        payload = kwargs
    return call_singpay_payment(
        "moov",
        amount=payload.get("amount"),
        reference=payload.get("reference"),
        phone=payload.get("phone") or payload.get("client_msisdn"),
        portefeuille=payload.get("portefeuille"),
        disbursement=payload.get("disbursement"),
        is_transfer=payload.get("isTransfer") or payload.get("is_transfer", False),
    )


def call_moov_money_check(reference):
    return call_singpay_status(reference)


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
