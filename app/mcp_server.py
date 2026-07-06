from mcp.server.fastmcp import FastMCP

from app.tools import (
    calculate_transfer_bonus,
    check_expiration_risk,
    compare_cash_vs_miles,
    get_promotions,
    get_route_options,
    score_transfer_decision,
    screen_sensitive_data,
    search_cash_flight_prices,
)

mcp = FastMCP("miles-agent-tools")

mcp.tool()(get_promotions)
mcp.tool()(get_route_options)
mcp.tool()(search_cash_flight_prices)
mcp.tool()(calculate_transfer_bonus)
mcp.tool()(compare_cash_vs_miles)
mcp.tool()(check_expiration_risk)
mcp.tool()(score_transfer_decision)
mcp.tool()(screen_sensitive_data)


if __name__ == "__main__":
    mcp.run()
