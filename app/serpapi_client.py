import json
import os
from typing import Any
from urllib import parse, request
from urllib.error import HTTPError, URLError

SERPAPI_SEARCH_URL = "https://serpapi.com/search"


def _request_json(params: dict[str, Any]) -> dict[str, Any]:
    query = parse.urlencode({key: value for key, value in params.items() if value})
    req = request.Request(f"{SERPAPI_SEARCH_URL}?{query}", method="GET")
    with request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _simplify_flight_group(group: dict[str, Any]) -> dict[str, Any]:
    flights = group.get("flights") or []
    first_flight = flights[0] if flights else {}
    return {
        "price": group.get("price"),
        "currency": group.get("currency"),
        "total_duration": group.get("total_duration"),
        "airline": first_flight.get("airline"),
        "flight_number": first_flight.get("flight_number"),
        "departure_airport": first_flight.get("departure_airport"),
        "arrival_airport": first_flight.get("arrival_airport"),
        "stops": max(len(flights) - 1, 0),
    }


def search_google_flights(
    origin: str,
    destination: str,
    outbound_date: str,
    adults: int,
    currency: str,
    max_results: int,
) -> dict[str, Any]:
    """Search Google Flights through SerpApi for cash fare context."""
    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        return {
            "status": "unavailable",
            "provider": "serpapi_google_flights",
            "message": "Set SERPAPI_API_KEY in the local .env file to enable cash fare search.",
        }

    params = {
        "engine": "google_flights",
        "api_key": api_key,
        "departure_id": origin.upper(),
        "arrival_id": destination.upper(),
        "outbound_date": outbound_date,
        "type": "2",
        "currency": currency.upper(),
        "adults": adults,
        "hl": "pt",
        "gl": "br",
        "sort_by": "2",
    }
    try:
        response = _request_json(params)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {
            "status": "error",
            "provider": "serpapi_google_flights",
            "message": f"SerpApi request failed: {exc}",
        }

    if response.get("error"):
        return {
            "status": "error",
            "provider": "serpapi_google_flights",
            "message": response["error"],
        }

    groups = (response.get("best_flights") or []) + (response.get("other_flights") or [])
    offers = [_simplify_flight_group(group) for group in groups[:max_results]]
    prices = [offer["price"] for offer in offers if isinstance(offer.get("price"), int | float)]
    return {
        "status": "success",
        "provider": "serpapi_google_flights",
        "data_is_mocked": False,
        "origin": origin.upper(),
        "destination": destination.upper(),
        "outbound_date": outbound_date,
        "currency": currency.upper(),
        "lowest_price": min(prices) if prices else None,
        "offers": offers,
        "price_insights": response.get("price_insights"),
        "note": (
            "SerpApi/Google Flights provides cash fare context only. It does not "
            "provide loyalty-program transfer bonuses, award availability, or "
            "mileage redemption prices."
        ),
    }
