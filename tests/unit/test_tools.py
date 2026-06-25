from app.tools import (
    calculate_transfer_bonus,
    compare_cash_vs_miles,
    score_transfer_decision,
    screen_sensitive_data,
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
    result = screen_sensitive_data("minha senha e abc123 e quero vender milhas")

    assert result["status"] == "success"
    assert result["is_safe"] is False
    assert "password" in result["sensitive_matches"]
    assert "vender milhas" in result["unsafe_matches"]
