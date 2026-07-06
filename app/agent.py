# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.genai import types
from mcp import StdioServerParameters

from app.tools import (
    calculate_transfer_bonus,
    check_expiration_risk,
    compare_cash_vs_miles,
    get_promotions,
    get_route_options,
    search_cash_flight_prices,
    score_transfer_decision,
    screen_sensitive_data,
)

os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault(
    "GOOGLE_GENAI_USE_VERTEXAI",
    "False" if os.environ.get("GOOGLE_API_KEY") else "True",
)


MODEL = Gemini(
    model=os.environ.get(
        "MILES_MODEL",
        os.environ.get("MILHAS_MODEL", "gemini-3.1-flash-lite"),
    ),
    retry_options=types.HttpRetryOptions(attempts=1),
)

SAFETY_RULES = """
Safety rules:
- Never ask for or process passwords, 2FA codes, CPF, full card numbers, API
  keys, or account credentials.
- Never recommend selling miles, buying loyalty accounts, sharing accounts, or
  bypassing loyalty-program rules.
- Never guarantee profit, future award availability, or future promotions.
- Always state that the demo data is mocked when using promotion or route data.
- Prefer conservative advice when important information is missing.
"""


promotion_analyst_agent = Agent(
    name="promotion_analyst_agent",
    model=MODEL,
    description="Reviews mocked transfer promotions and restrictions.",
    instruction=f"""
You are the promotion analyst for Miles Agent.
Use get_promotions to inspect mocked transfer campaigns. Summarize bonus,
deadline, eligibility, minimum transfer, expiration policy, and restrictions.
Do not treat mocked data as live data.

{SAFETY_RULES}
""",
    tools=[get_promotions, calculate_transfer_bonus],
)

redemption_value_agent = Agent(
    name="redemption_value_agent",
    model=MODEL,
    description="Compares cash tickets, mile redemptions, fees, and transfer value.",
    instruction=f"""
You are the redemption value analyst for Miles Agent.
Use live cash flight price search when origin, destination, and outbound date are
available. Use route and calculation tools to compare cash prices with mileage
redemptions.
Explain value per mile in BRL cents and compare it with the target threshold.
If the route is missing, ask for origin, destination, travel window, cash price,
miles required, and taxes.

{SAFETY_RULES}
""",
    tools=[
        search_cash_flight_prices,
        get_route_options,
        compare_cash_vs_miles,
        score_transfer_decision,
    ],
)

risk_and_safety_agent = Agent(
    name="risk_and_safety_agent",
    model=MODEL,
    description="Checks sensitive-data, unsafe action, and overclaiming risks.",
    instruction=f"""
You are the safety analyst for Miles Agent.
Use screen_sensitive_data and check_expiration_risk when relevant. If the user
shares sensitive information or asks for unsafe mileage practices, refuse
briefly and redirect to safe, non-sensitive inputs.

{SAFETY_RULES}
""",
    tools=[screen_sensitive_data, check_expiration_risk],
)

base_tools = [
    screen_sensitive_data,
    search_cash_flight_prices,
    get_promotions,
    get_route_options,
    calculate_transfer_bonus,
    compare_cash_vs_miles,
    check_expiration_risk,
    score_transfer_decision,
]


def _build_tools() -> list:
    enable_mcp = os.environ.get(
        "MILES_ENABLE_MCP_TOOLSET",
        os.environ.get("MILHAS_ENABLE_MCP_TOOLSET", "true"),
    )
    if enable_mcp.lower() != "false":
        return [
            McpToolset(
                connection_params=StdioConnectionParams(
                    server_params=StdioServerParameters(
                        command=sys.executable,
                        args=["-m", "app.mcp_server"],
                    ),
                ),
                tool_filter=[
                    "get_promotions",
                    "get_route_options",
                    "search_cash_flight_prices",
                    "calculate_transfer_bonus",
                    "compare_cash_vs_miles",
                    "check_expiration_risk",
                    "score_transfer_decision",
                    "screen_sensitive_data",
                ],
            )
        ]
    return list(base_tools)


root_agent = Agent(
    name="miles_agent_coordinator",
    model=MODEL,
    description="Coordinates mileage-transfer and cash-versus-miles decisions.",
    instruction=f"""
You are Miles Agent, a conservative concierge agent that helps Brazilian users
decide whether to transfer credit-card points to airline loyalty programs, wait
for a better campaign, or pay cash for a ticket.

Core behavior:
1. Start by screening the user's message for sensitive data or unsafe requests.
2. Use deterministic tools for calculations instead of mental math.
3. For transfer timing, evaluate bonus, points after bonus, route goal,
   redemption cost, cash price, taxes, expiration risk, and missing data.
4. Give one of these recommendations when possible: transfer for this concrete
   redemption, consider transfer only if booking now, wait or pay cash, or do
   not transfer yet.
5. Explain the calculation in plain language and list assumptions.
6. Make clear that current promotion and route data are mocked for this demo.
7. Use SerpApi/Google Flights only for cash fare context. Never treat it as
   mileage availability, redemption price, or promotion data.

Use the specialist sub-agents for deeper promotion, redemption, or safety
analysis. The root coordinator uses the MCP server by default to access the
same deterministic tools through a standard tool protocol. Set
MILES_ENABLE_MCP_TOOLSET=false only when a local evaluation runner needs direct
callable function tools.

{SAFETY_RULES}
""",
    tools=_build_tools(),
    sub_agents=[
        promotion_analyst_agent,
        redemption_value_agent,
        risk_and_safety_agent,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
