from app.tools import (
    calculate_transfer_bonus,
    compare_cash_vs_miles,
    score_transfer_decision,
    screen_sensitive_data,
    search_cash_flight_prices,
)


def test_calculate_transfer_bonus() -> None:
    result = calculate_transfer_bonus(points=40000, bonus_percentage=80)

    assert result["status"] == "success"
    assert result["bonus_miles"] == 32000
    assert result["total_miles"] == 72000


def test_compare_cash_vs_miles_recommends_miles_for_high_value() -> None:
    result = compare_cash_vs_miles(
        cash_price_brl=1200,
        miles_required=42000,
        taxes_brl=90,
    )

    assert result["status"] == "success"
    assert result["value_cents_per_mile"] == 2.64
    assert result["recommendation"] == "use_miles"


def test_score_transfer_decision_waits_when_miles_value_is_low() -> None:
    result = score_transfer_decision(
        points=20000,
        bonus_percentage=100,
        cash_price_brl=380,
        miles_required=16000,
        taxes_brl=58,
        months_until_points_expire=10,
    )

    assert result["status"] == "success"
    assert result["recommendation"] == "wait_or_pay_cash"


def test_screen_sensitive_data_blocks_credentials() -> None:
    result = screen_sensitive_data("my password is abc123 and I want to sell miles")

    assert result["status"] == "success"
    assert result["is_safe"] is False
    assert "password" in result["sensitive_matches"]
    assert "sell miles" in result["unsafe_matches"]


def test_search_cash_flight_prices_is_optional_without_api_key(
    monkeypatch,
) -> None:
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)

    result = search_cash_flight_prices(
        origin="NAT",
        destination="SAO",
        outbound_date="2026-09-10",
    )

    assert result["status"] == "unavailable"
    assert result["provider"] == "serpapi_google_flights"


def test_search_cash_flight_prices_validates_max_results() -> None:
    result = search_cash_flight_prices(
        origin="NAT",
        destination="SAO",
        outbound_date="2026-09-10",
        max_results=0,
    )

    assert result["status"] == "error"
    assert result["message"] == "max_results must be positive"
