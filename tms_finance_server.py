#!/usr/bin/env python3
"""
TMS Finance & Rate Card MCP Server
Handles rate cards based on routes, truck types, and calculates charges.
"""

import asyncio
import json
from typing import Any
from datetime import datetime
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

# In-memory storage
rate_cards_db = {} # format: route_id_truck_type -> {route, truck_type, base_rate, per_km_rate}

app = Server("tms-finance-manager")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="add_rate_card",
            description="Define pricing for a specific route and truck type",
            inputSchema={
                "type": "object",
                "properties": {
                    "route_id": {"type": "string", "description": "Identifier for the route (e.g., NY-LA)"},
                    "truck_type": {"type": "string", "description": "Type of truck (e.g., flatbed, refrigerated)"},
                    "base_rate": {"type": "number", "description": "Base flat rate for the route"}
                },
                "required": ["route_id", "truck_type", "base_rate"]
            }
        ),
        Tool(
            name="get_rate",
            description="Retrieve the rate card for a given route and truck type",
            inputSchema={
                "type": "object",
                "properties": {
                    "route_id": {"type": "string", "description": "Identifier for the route"},
                    "truck_type": {"type": "string", "description": "Type of truck"}
                },
                "required": ["route_id", "truck_type"]
            }
        ),
        Tool(
            name="calculate_charges",
            description="Calculate total charges for a booking including any accessorial charges",
            inputSchema={
                "type": "object",
                "properties": {
                    "route_id": {"type": "string", "description": "Identifier for the route"},
                    "truck_type": {"type": "string", "description": "Type of truck"},
                    "accessorial_charges": {"type": "number", "description": "Any additional charges (e.g., tolls, waiting time)"}
                },
                "required": ["route_id", "truck_type"]
            }
        ),
        Tool(
            name="list_rate_cards",
            description="View all active rate cards",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    if name == "add_rate_card":
        route_id = arguments["route_id"]
        truck_type = arguments["truck_type"]
        card_id = f"{route_id}_{truck_type}"
        
        rate_data = {
            "route_id": route_id,
            "truck_type": truck_type,
            "base_rate": arguments["base_rate"],
            "currency": "USD",
            "updated_at": datetime.now().isoformat()
        }
        rate_cards_db[card_id] = rate_data
        return [TextContent(type="text", text=f"Rate card added successfully: {json.dumps(rate_data, indent=2)}")]

    elif name == "get_rate":
        route_id = arguments["route_id"]
        truck_type = arguments["truck_type"]
        card_id = f"{route_id}_{truck_type}"
        
        if card_id not in rate_cards_db:
            return [TextContent(type="text", text=f"Error: No rate card found for route {route_id} and truck {truck_type}.")]
            
        return [TextContent(type="text", text=json.dumps(rate_cards_db[card_id], indent=2))]

    elif name == "calculate_charges":
        route_id = arguments["route_id"]
        truck_type = arguments["truck_type"]
        accessorial = arguments.get("accessorial_charges", 0)
        card_id = f"{route_id}_{truck_type}"
        
        if card_id not in rate_cards_db:
            return [TextContent(type="text", text=f"Error: Cannot calculate. No rate card found for route {route_id} and truck {truck_type}.")]
            
        base_rate = rate_cards_db[card_id]["base_rate"]
        total = base_rate + accessorial
        
        result = {
            "route_id": route_id,
            "truck_type": truck_type,
            "base_rate": base_rate,
            "accessorial_charges": accessorial,
            "total_charges": total,
            "currency": rate_cards_db[card_id]["currency"]
        }
        
        return [TextContent(type="text", text=f"Charges calculated: {json.dumps(result, indent=2)}")]

    elif name == "list_rate_cards":
        if not rate_cards_db:
            return [TextContent(type="text", text="No rate cards found.")]
        return [TextContent(type="text", text=json.dumps(list(rate_cards_db.values()), indent=2))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
