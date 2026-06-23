#!/usr/bin/env python3
"""
TMS Fleet Management MCP Server
Handles trucks, their capacities, types, and current status.
"""

import asyncio
import json
from typing import Any
from datetime import datetime
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

# In-memory storage
fleet_db = {}

app = Server("tms-fleet-manager")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="add_truck",
            description="Register a new truck to the fleet",
            inputSchema={
                "type": "object",
                "properties": {
                    "truck_id": {"type": "string", "description": "Unique truck ID"},
                    "truck_type": {"type": "string", "description": "Type of truck (e.g., flatbed, refrigerated)"},
                    "capacity_weight": {"type": "number", "description": "Maximum weight capacity (kg)"},
                    "capacity_volume": {"type": "number", "description": "Maximum volume capacity (cbm)"}
                },
                "required": ["truck_id", "truck_type", "capacity_weight", "capacity_volume"]
            }
        ),
        Tool(
            name="update_truck_status",
            description="Update availability status of a truck",
            inputSchema={
                "type": "object",
                "properties": {
                    "truck_id": {"type": "string", "description": "Truck ID"},
                    "status": {"type": "string", "description": "Status: available, in-transit, maintenance"}
                },
                "required": ["truck_id", "status"]
            }
        ),
        Tool(
            name="check_capacity",
            description="Find available trucks meeting specific requirements",
            inputSchema={
                "type": "object",
                "properties": {
                    "truck_type": {"type": "string", "description": "Required truck type"},
                    "min_weight": {"type": "number", "description": "Minimum weight capacity required"},
                    "min_volume": {"type": "number", "description": "Minimum volume capacity required"}
                },
                "required": ["truck_type", "min_weight", "min_volume"]
            }
        ),
        Tool(
            name="list_fleet",
            description="View all trucks and their current status",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    if name == "add_truck":
        truck_id = arguments["truck_id"]
        if truck_id in fleet_db:
            return [TextContent(type="text", text=f"Error: Truck {truck_id} already exists.")]
        
        truck_data = {
            "truck_id": truck_id,
            "truck_type": arguments["truck_type"],
            "capacity_weight": arguments["capacity_weight"],
            "capacity_volume": arguments["capacity_volume"],
            "status": "available",
            "updated_at": datetime.now().isoformat()
        }
        fleet_db[truck_id] = truck_data
        return [TextContent(type="text", text=f"Truck added successfully: {json.dumps(truck_data, indent=2)}")]

    elif name == "update_truck_status":
        truck_id = arguments["truck_id"]
        status = arguments["status"]
        if truck_id not in fleet_db:
            return [TextContent(type="text", text=f"Error: Truck {truck_id} not found.")]
        
        valid_statuses = ["available", "in-transit", "maintenance"]
        if status not in valid_statuses:
            return [TextContent(type="text", text=f"Error: Invalid status. Must be one of {valid_statuses}.")]

        fleet_db[truck_id]["status"] = status
        fleet_db[truck_id]["updated_at"] = datetime.now().isoformat()
        return [TextContent(type="text", text=f"Truck {truck_id} status updated to {status}.")]

    elif name == "check_capacity":
        req_type = arguments["truck_type"]
        req_weight = arguments["min_weight"]
        req_vol = arguments["min_volume"]
        
        available_trucks = []
        for truck in fleet_db.values():
            if (truck["status"] == "available" and 
                truck["truck_type"] == req_type and 
                truck["capacity_weight"] >= req_weight and 
                truck["capacity_volume"] >= req_vol):
                available_trucks.append(truck)
                
        if not available_trucks:
            return [TextContent(type="text", text="No available trucks found matching the criteria.")]
            
        return [TextContent(type="text", text=f"Found {len(available_trucks)} suitable truck(s): {json.dumps(available_trucks, indent=2)}")]

    elif name == "list_fleet":
        if not fleet_db:
            return [TextContent(type="text", text="Fleet is empty.")]
        return [TextContent(type="text", text=json.dumps(list(fleet_db.values()), indent=2))]

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
