from app.tools import (
    compare_cash_vs_miles,
    score_transfer_decision,
    screen_sensitive_data,
)


def _print_transfer_demo() -> None:
    print("\nScenario 1 - Transfer timing")
    print("Input: 40,000 Livelo points, 80% Smiles bonus, 2 months to expire.")
    result = score_transfer_decision(
        points=40000,
        bonus_percentage=80,
        cash_price_brl=1200,
        miles_required=42000,
        taxes_brl=90,
        months_until_points_expire=2,
    )
    details = result["details"]
    print(f"Recommendation: {result['recommendation']}")
    print(f"Score: {result['score']}/100")
    print(f"Miles after bonus: {details['transfer']['total_miles']}")
    print(f"Value per mile: {details['value']['value_cents_per_mile']} BRL cents")
    print(f"Expiration risk: {details['expiration']['risk']}")
    print("Data note: mocked data for capstone reproducibility.")


def _print_cash_demo() -> None:
    print("\nScenario 2 - Cash versus miles")
    print("Input: NAT-REC ticket costs BRL 380 or 16,000 miles + BRL 58.")
    result = compare_cash_vs_miles(
        cash_price_brl=380,
        miles_required=16000,
        taxes_brl=58,
    )
    print(f"Recommendation: {result['recommendation']}")
    print(f"Value per mile: {result['value_cents_per_mile']} BRL cents")
    print(f"Target value: {result['target_value_cents_per_mile']} BRL cents")


def _print_safety_demo() -> None:
    print("\nScenario 3 - Safety guardrail")
    print("Input: user shares a password and asks to sell miles.")
    result = screen_sensitive_data(
        "Minha senha do LATAM Pass e abc123. Quero vender milhas."
    )
    print(f"Safe to process: {result['is_safe']}")
    print(f"Sensitive matches: {', '.join(result['sensitive_matches'])}")
    print(f"Unsafe matches: {', '.join(result['unsafe_matches'])}")
    print(f"Guidance: {result['guidance']}")


def main() -> None:
    print("Milhas Claras - no-billing local demo")
    print("This demo uses deterministic tools and mocked data. No API key required.")
    _print_transfer_demo()
    _print_cash_demo()
    _print_safety_demo()


if __name__ == "__main__":
    main()
