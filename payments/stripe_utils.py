import stripe
from django.conf import settings

#stripe.api_key = settings.STRIPE_SECRET_KEY

def create_payment_intent(amount_decimal, currency="USD", metadata=None):
    """
    amount_decimal: Decimal o float (ej 12.50). Stripe necesita cents (integer).
    Devuelve el PaymentIntent dict.
    """
    # Stripe espera monto en centavos como entero
    amount_cents = int((amount_decimal * 100).to_integral_value()) if hasattr(amount_decimal, 'quantize') else int(amount_decimal * 100)
    intent = stripe.PaymentIntent.create(
        amount=amount_cents,
        currency=currency.lower(),
        metadata=metadata or {},
    )
    return intent

def retrieve_payment_intent(intent_id):
    return stripe.PaymentIntent.retrieve(intent_id)