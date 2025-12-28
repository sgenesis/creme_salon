import mercadopago
from django.conf import settings

sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

def create_mp_preference(*, amount, description, appointment_id):
    preference_data = {
        "items": [
            {
                "title": description,
                "quantity": 1,
                "currency_id": "MXN",
                "unit_price": float(amount),
            }
        ],
        "external_reference": str(appointment_id),
        "notification_url": settings.MP_WEBHOOK_URL,
        "auto_return": "approved",
        "back_urls": {
            "success": settings.MP_SUCCESS_URL,
            "failure": settings.MP_FAILURE_URL,
            "pending": settings.MP_PENDING_URL,
        },
    }

    return sdk.preference().create(preference_data)["response"]

    if result["status"] not in (200, 201):
        raise Exception(f"MercadoPago error: {result}")

    return result["response"]