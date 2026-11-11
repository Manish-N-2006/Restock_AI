import time
import uuid
import logging
from typing import Dict, Any, Optional
import httpx

from .config import paypal_settings

logger = logging.getLogger("payments.paypal_client")

class PayPalClientError(Exception):
    def __init__(self, message: str, status_code: int = 400, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details

class PayPalClient:
    """
    Client for PayPal Orders API v2 & OAuth 2.0.
    Directly interfaces with PayPal Sandbox (https://api-m.sandbox.paypal.com).
    Provides resilient fallback simulation for isolated automated tests / environments
    where sandbox credentials are not yet populated.
    """

    def __init__(self):
        self._cached_token: Optional[str] = None
        self._token_expires_at: float = 0.0
        # In-memory store for mock simulation when credentials are unset or during tests
        self._mock_orders: Dict[str, Dict[str, Any]] = {}

    def get_access_token(self) -> str:
        """
        Retrieves PayPal OAuth 2.0 bearer token using client credentials grant.
        Caches the token with an expiration buffer.
        """
        now = time.time()
        if self._cached_token and now < self._token_expires_at:
            return self._cached_token

        if not paypal_settings.is_configured:
            if not paypal_settings.allow_mock:
                logger.error("PayPal credentials missing and PAYPAL_ALLOW_MOCK is disabled.")
                raise PayPalClientError("PayPal Sandbox credentials not configured. Set RESTOCKAI_PAYPAL_CLIENT_ID and RESTOCKAI_PAYPAL_CLIENT_SECRET.", status_code=503)
            # Deterministic sandbox mock token when mock is explicitly allowed
            self._cached_token = f"A21AA_SANDBOX_MOCK_TOKEN_{int(now)}"
            self._token_expires_at = now + 3600
            return self._cached_token

        url = f"{paypal_settings.api_base}/v1/oauth2/token"
        headers = {
            "Accept": "application/json",
            "Accept-Language": "en_US",
        }
        data = {"grant_type": "client_credentials"}

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(
                    url,
                    auth=(paypal_settings.client_id, paypal_settings.client_secret),
                    headers=headers,
                    data=data,
                )
                debug_id = response.headers.get("paypal-debug-id", "N/A")
                if response.status_code != 200:
                    logger.error(f"PayPal OAuth failed (HTTP {response.status_code}, debug-id={debug_id}): {response.text}")
                    raise PayPalClientError(
                        f"PayPal OAuth authentication failed (debug-id: {debug_id}): {response.text}",
                        status_code=response.status_code,
                    )

                body = response.json()
                self._cached_token = body.get("access_token")
                expires_in = body.get("expires_in", 3600)
                self._token_expires_at = now + max(60, expires_in - 120)
                logger.info(f"PayPal OAuth successful (HTTP 200, debug-id={debug_id}, expires_in={expires_in}s)")
                return self._cached_token

        except httpx.RequestError as exc:
            logger.error(f"Network error during PayPal OAuth: {exc}")
            raise PayPalClientError(f"Could not connect to PayPal OAuth: {str(exc)}", status_code=502)

    def create_order(
        self,
        amount: float,
        currency: str,
        reference_id: str,
        custom_id: str,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates a PayPal Order using Orders API v2 (POST /v2/checkout/orders).
        Intent is CAPTURE. Amount is formatted to 2 decimal places.
        """
        formatted_amount = f"{amount:.2f}"
        ret_url = return_url or paypal_settings.return_url
        cnc_url = cancel_url or paypal_settings.cancel_url

        if not paypal_settings.is_configured:
            if not paypal_settings.allow_mock:
                logger.error("create_order attempted without credentials and mock mode disabled.")
                raise PayPalClientError("PayPal Sandbox credentials not configured. Mock mode is disabled.", status_code=503)
            # Realistic PayPal Orders v2 schema mock
            order_id = f"PAYPAL-ORD-{uuid.uuid4().hex[:12].upper()}"
            mock_order = {
                "id": order_id,
                "status": "CREATED",
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "reference_id": reference_id,
                        "custom_id": custom_id,
                        "amount": {
                            "currency_code": currency,
                            "value": formatted_amount,
                        },
                    }
                ],
                "links": [
                    {
                        "href": f"https://www.sandbox.paypal.com/checkoutnow?token={order_id}",
                        "rel": "approve",
                        "method": "GET",
                    },
                    {
                        "href": f"{paypal_settings.api_base}/v2/checkout/orders/{order_id}/capture",
                        "rel": "capture",
                        "method": "POST",
                    },
                ],
                "create_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            self._mock_orders[order_id] = mock_order
            return mock_order

        token = self.get_access_token()
        url = f"{paypal_settings.api_base}/v2/checkout/orders"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        if idempotency_key:
            headers["PayPal-Request-Id"] = idempotency_key

        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": reference_id,
                    "description": f"ReStockAI Commercial Recovery Order {reference_id}",
                    "custom_id": custom_id,
                    "amount": {
                        "currency_code": currency,
                        "value": formatted_amount,
                    },
                }
            ],
            "application_context": {
                "brand_name": "ReStockAI",
                "landing_page": "NO_PREFERENCE",
                "user_action": "PAY_NOW",
                "return_url": ret_url,
                "cancel_url": cnc_url,
            },
        }

        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.post(url, headers=headers, json=payload)
                debug_id = response.headers.get("paypal-debug-id", "N/A")
                if response.status_code not in (200, 201):
                    logger.error(f"PayPal create_order failed (HTTP {response.status_code}, debug-id={debug_id}): {response.text}")
                    raise PayPalClientError(
                        f"PayPal order creation failed (debug-id: {debug_id}): {response.text}",
                        status_code=response.status_code,
                        details=response.text,
                    )
                order_data = response.json()
                logger.info(f"PayPal create_order successful (HTTP {response.status_code}, debug-id={debug_id}, id={order_data.get('id')})")
                return order_data
        except httpx.RequestError as exc:
            logger.error(f"Network error creating PayPal order: {exc}")
            raise PayPalClientError(f"Could not connect to PayPal Orders API: {str(exc)}", status_code=502)

    def capture_order(
        self,
        paypal_order_id: str,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Captures payment for a buyer-approved PayPal order (POST /v2/checkout/orders/{id}/capture).
        """
        if not paypal_settings.is_configured:
            if not paypal_settings.allow_mock:
                logger.error("capture_order attempted without credentials and mock mode disabled.")
                raise PayPalClientError("PayPal Sandbox credentials not configured. Mock mode is disabled.", status_code=503)
            # Check mock orders
            existing = self._mock_orders.get(paypal_order_id)
            if not existing:
                amount_val = "100.00"
                currency_code = "USD"
            else:
                amount_val = existing["purchase_units"][0]["amount"]["value"]
                currency_code = existing["purchase_units"][0]["amount"]["currency_code"]

            capture_id = f"CAP-{uuid.uuid4().hex[:14].upper()}"
            payer_id = f"PAYER-{uuid.uuid4().hex[:8].upper()}"
            payer_email = "sandbox-buyer@restockai.io"

            mock_capture_resp = {
                "id": paypal_order_id,
                "status": "COMPLETED",
                "payment_source": {
                    "paypal": {
                        "email_address": payer_email,
                        "account_id": payer_id,
                        "name": {"given_name": "Sandbox", "surname": "Buyer"},
                    }
                },
                "purchase_units": [
                    {
                        "reference_id": existing.get("purchase_units", [{}])[0].get("reference_id", "REF-001") if existing else "REF-001",
                        "payments": {
                            "captures": [
                                {
                                    "id": capture_id,
                                    "status": "COMPLETED",
                                    "amount": {
                                        "currency_code": currency_code,
                                        "value": amount_val,
                                    },
                                    "seller_protection": {"status": "ELIGIBLE"},
                                    "final_capture": True,
                                    "seller_receivable_breakdown": {
                                        "gross_amount": {"currency_code": currency_code, "value": amount_val},
                                        "paypal_fee": {"currency_code": currency_code, "value": f"{float(amount_val)*0.0349 + 0.49:.2f}"},
                                        "net_amount": {"currency_code": currency_code, "value": f"{float(amount_val) - (float(amount_val)*0.0349 + 0.49):.2f}"},
                                    },
                                    "create_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                }
                            ]
                        },
                    }
                ],
                "payer": {
                    "name": {"given_name": "Sandbox", "surname": "Buyer"},
                    "email_address": payer_email,
                    "payer_id": payer_id,
                },
            }
            if existing:
                existing["status"] = "COMPLETED"
            return mock_capture_resp

        token = self.get_access_token()
        url = f"{paypal_settings.api_base}/v2/checkout/orders/{paypal_order_id}/capture"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        if idempotency_key:
            headers["PayPal-Request-Id"] = idempotency_key

        try:
            with httpx.Client(timeout=25.0) as client:
                response = client.post(url, headers=headers, json={})
                debug_id = response.headers.get("paypal-debug-id", "N/A")
                if response.status_code not in (200, 201):
                    logger.error(f"PayPal capture failed (HTTP {response.status_code}, debug-id={debug_id}): {response.text}")
                    raise PayPalClientError(
                        f"PayPal capture failed (debug-id: {debug_id}): {response.text}",
                        status_code=response.status_code,
                        details=response.text,
                    )
                capture_data = response.json()
                logger.info(f"PayPal capture successful (HTTP {response.status_code}, debug-id={debug_id}, status={capture_data.get('status')})")
                return capture_data
        except httpx.RequestError as exc:
            logger.error(f"Network error capturing PayPal order: {exc}")
            raise PayPalClientError(f"Could not connect to PayPal capture endpoint: {str(exc)}", status_code=502)

    def get_order_details(self, paypal_order_id: str) -> Dict[str, Any]:
        """
        Retrieves PayPal order details (GET /v2/checkout/orders/{id}).
        """
        if not paypal_settings.is_configured:
            order = self._mock_orders.get(paypal_order_id)
            if not order:
                raise PayPalClientError(f"Mock PayPal Order {paypal_order_id} not found", status_code=404)
            return order

        token = self.get_access_token()
        url = f"{paypal_settings.api_base}/v2/checkout/orders/{paypal_order_id}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(url, headers=headers)
                if response.status_code != 200:
                    raise PayPalClientError(f"Order query failed: {response.text}", status_code=response.status_code)
                return response.json()
        except httpx.RequestError as exc:
            raise PayPalClientError(f"Could not retrieve PayPal order details: {str(exc)}", status_code=502)

paypal_client = PayPalClient()
