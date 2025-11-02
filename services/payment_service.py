# services/payment_service.py
import os
import stripe
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/payments", tags=["Payments"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL")


@router.post("/create-checkout-session")
async def create_checkout_session(data: dict):
    price_id = data.get("price_id")
    if not price_id:
        raise HTTPException(status_code=400, detail="Price ID is required")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=f"{FRONTEND_URL}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/payment/cancel",
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except stripe.error.InvalidRequestError as e:
        raise HTTPException(status_code=400, detail=f"Invalid price ID: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")