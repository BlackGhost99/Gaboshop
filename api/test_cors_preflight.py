"""Contrat CORS du checkout : le navigateur doit pouvoir envoyer Idempotency-Key.
Ne nécessite aucune commande ni aucun accès à la base réelle.
"""
from django.test import Client, SimpleTestCase, override_settings

STAGING_ORIGIN = "https://gaboshop-web-staging-uvn1.onrender.com"

@override_settings(CORS_ALLOWED_ORIGINS=[STAGING_ORIGIN])
class CheckoutCorsTests(SimpleTestCase):
    def test_idempotency_header_allowed_on_preflight(self):
        response = Client().options(
            "/api/v1/orders/create/",
            HTTP_ORIGIN=STAGING_ORIGIN,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type,idempotency-key",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["access-control-allow-origin"], STAGING_ORIGIN)
        allowed = {
            name.strip().lower()
            for name in response["access-control-allow-headers"].split(",")
        }
        self.assertTrue({"authorization", "content-type", "idempotency-key"} <= allowed)
        self.assertIn("POST", response["access-control-allow-methods"])
