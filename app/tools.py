import json
import re
from pathlib import Path
from typing import Any

from app.serpapi_client import search_google_flights

DATA_DIR = Path(__file__).parent / "data"
TARGET_VALUE_CENTS_PER_MILE = 2.2
SENSITIVE_PATTERNS = {
    "password": re.compile(r"\b(password|passcode|2fa|token|code)\b", re.I),
    "cpf": re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
    "card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
}


def _load_json(filename: str) -> list[dict[str, Any]]:
    with (DATA_DIR / filename).open(encoding="utf-8") as file:
        return json.load(file)


def get_promotions(
    source_program: str | None = None,
    destination_program: str | None = None,
) -> dict[str, Any]:
    """Return mocked transfer promotions, optionally filtered by program."""
    promotions = _load_json("promotions.json")
    if source_program:
        promotions = [
            promo
            for promo in promotions
            if promo["source_program"].lower() == source_program.lower()
        ]
    if destination_program:
        promotions = [
            promo
            for promo in promotions
            if promo["destination_program"].lower() == destination_program.lower()
        ]
    return {
        "status": "success",
        "data_is_mocked": True,
        "promotions": promotions,
    }


def get_route_options(
    origin: str | None = None,
    destination: str | None = None,
    travel_window: str | None = None,
) -> dict[str, Any]:
    """Return mocked cash and mileage redemption options for sample routes."""
    routes = _load_json("routes.json")
    if origin:
        routes = [route for route in routes if route["origin"].lower() == origin.lower()]
    if destination:
        routes = [
            route
            for route in routes
            if route["destination"].lower() == destination.lower()
        ]
    if travel_window:
        routes = [
            route
            for route in routes
            if travel_window.lower() in route["travel_window"].lower()
        ]
    return {
        "status": "success",
        "data_is_mocked": True,
        "routes": routes,
    }


def search_cash_flight_prices(
    origin: str,
    destination: str,
    outbound_date: str,
    adults: int = 1,
    currency: str = "BRL",
    max_results: int = 5,
) -> dict[str, Any]:
    """Return cash flight prices from SerpApi Google Flights when configured."""
    if adults <= 0:
        return {"status": "error", "message": "adults must be positive"}
    if max_results <= 0:
        return {"status": "error", "message": "max_results must be positive"}
    return search_google_flights(
        origin=origin,
        destination=destination,
        outbound_date=outbound_date,
        adults=adults,
        currency=currency,
        max_results=max_results,
    )


def calculate_transfer_bonus(points: int, bonus_percentage: float) -> dict[str, Any]:
    """Calculate how many miles a transfer yields after a bonus campaign."""
    if points < 0:
        return {"status": "error", "message": "points must be non-negative"}
    if bonus_percentage < 0:
        return {"status": "error", "message": "bonus_percentage must be non-negative"}

    bonus_miles = round(points * (bonus_percentage / 100))
    total_miles = points + bonus_miles
    return {
        "status": "success",
        "points_transferred": points,
        "bonus_percentage": bonus_percentage,
        "bonus_miles": bonus_miles,
        "total_miles": total_miles,
    }


def compare_cash_vs_miles(
    cash_price_brl: float,
    miles_required: int,
    taxes_brl: float = 0,
) -> dict[str, Any]:
    """Compare the effective value of redeeming miles against paying cash."""
    if cash_price_brl < 0 or taxes_brl < 0:
        return {"status": "error", "message": "prices and taxes must be non-negative"}
    if miles_required <= 0:
        return {"status": "error", "message": "miles_required must be positive"}

    net_cash_value = max(cash_price_brl - taxes_brl, 0)
    value_per_mile_brl = net_cash_value / miles_required
    value_cents_per_mile = value_per_mile_brl * 100
    recommendation = (
        "use_miles"
        if value_cents_per_mile >= TARGET_VALUE_CENTS_PER_MILE
        else "pay_cash_or_wait"
    )
    return {
        "status": "success",
        "cash_price_brl": round(cash_price_brl, 2),
        "taxes_brl": round(taxes_brl, 2),
        "miles_required": miles_required,
        "net_cash_value_brl": round(net_cash_value, 2),
        "value_cents_per_mile": round(value_cents_per_mile, 2),
        "target_value_cents_per_mile": TARGET_VALUE_CENTS_PER_MILE,
        "recommendation": recommendation,
    }


def check_expiration_risk(months_until_points_expire: int) -> dict[str, Any]:
    """Classify point-expiration risk."""
    if months_until_points_expire < 0:
        return {"status": "error", "message": "months_until_points_expire must be >= 0"}
    if months_until_points_expire <= 3:
        risk = "high"
    elif months_until_points_expire <= 6:
        risk = "medium"
    else:
        risk = "low"
    return {
        "status": "success",
        "months_until_points_expire": months_until_points_expire,
        "risk": risk,
    }


def score_transfer_decision(
    points: int,
    bonus_percentage: float,
    cash_price_brl: float,
    miles_required: int,
    taxes_brl: float,
    months_until_points_expire: int,
) -> dict[str, Any]:
    """Score whether a user should transfer points for a concrete redemption."""
    transfer = calculate_transfer_bonus(points, bonus_percentage)
    value = compare_cash_vs_miles(cash_price_brl, miles_required, taxes_brl)
    expiration = check_expiration_risk(months_until_points_expire)
    if any(item["status"] == "error" for item in (transfer, value, expiration)):
        return {
            "status": "error",
            "details": {"transfer": transfer, "value": value, "expiration": expiration},
        }

    enough_miles = transfer["total_miles"] >= miles_required
    strong_value = (
        value["value_cents_per_mile"] >= value["target_value_cents_per_mile"]
    )
    expiration_pressure = expiration["risk"] in {"high", "medium"}

    score = 0
    score += 35 if enough_miles else -20
    score += 35 if strong_value else -15
    score += 15 if bonus_percentage >= 80 else 5
    score += 10 if expiration_pressure else 0

    if not enough_miles:
        recommendation = "do_not_transfer_yet"
    elif strong_value and (bonus_percentage >= 80 or expiration_pressure):
        recommendation = "transfer_for_this_redemption"
    elif strong_value:
        recommendation = "consider_transfer_only_if_booking_now"
    else:
        recommendation = "wait_or_pay_cash"

    return {
        "status": "success",
        "data_is_mocked": True,
        "score": max(0, min(score, 100)),
        "recommendation": recommendation,
        "enough_miles_after_bonus": enough_miles,
        "details": {"transfer": transfer, "value": value, "expiration": expiration},
    }


def screen_sensitive_data(user_text: str) -> dict[str, Any]:
    """Detect sensitive information that should not be processed by the agent."""
    matches = [
        label
        for label, pattern in SENSITIVE_PATTERNS.items()
        if pattern.search(user_text or "")
    ]
    unsafe_terms = [
        "sell miles",
        "buy account",
        "borrow account",
        "share password",
        "bypass",
    ]
    unsafe_matches = [
        term for term in unsafe_terms if term in (user_text or "").lower()
    ]
    return {
        "status": "success",
        "is_safe": not matches and not unsafe_matches,
        "sensitive_matches": matches,
        "unsafe_matches": unsafe_matches,
        "guidance": (
            "Use only non-sensitive inputs: approximate balance, expiration month, "
            "program, route, travel window, cash price, miles required, and taxes."
        ),
    }
