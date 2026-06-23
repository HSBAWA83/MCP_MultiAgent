#!/usr/bin/env python3
"""
TMS Booking & Tracking MCP Server
Handles transport bookings, route assignments, and tracking.
"""

import asyncio
import json
from typing import Any
from datetime import datetime
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

# In-memory storage
bookings_db = {} 

app = Server("tms-booking-manager")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="create_booking",
            description="Initiate a new transport booking",
            inputSchema={
                "type": "object",
                "properties": {
                    "booking_id": {"type": "string", "description": "Unique booking reference ID"},
                    "route_id": {"type": "string", "description": "Route ID (e.g., NY-LA)"},
                    "required_truck_type": {"type": "string", "description": "Required truck type"},
                    "weight": {"type": "number", "description": "Total weight (kg)"},
                    "volume": {"type": "number", "description": "Total volume (cbm)"}
                },
                "required": ["booking_id", "route_id", "required_truck_type", "weight", "volume"]
            }
        ),
        Tool(
            name="assign_truck",
            description="Assign an available truck to a booking",
            inputSchema={
                "type": "object",
                "properties": {
                    "booking_id": {"type": "string", "description": "Booking ID"},
                    "truck_id": {"type": "string", "description": "ID of the truck to assign"}
                },
                "required": ["booking_id", "truck_id"]
            }
        ),
        Tool(
            name="update_tracking",
            description="Update the location/status of an active booking",
            inputSchema={
                "type": "object",
                "properties": {
                    "booking_id": {"type": "string", "description": "Booking ID"},
                    "status": {"type": "string", "description": "Booking status (e.g., pending, in-transit, delivered)"},
                    "location": {"type": "string", "description": "Current location"}
                },
                "required": ["booking_id", "status", "location"]
            }
        ),
        Tool(
            name="get_booking_status",
            description="Retrieve full details and tracking of a booking",
            inputSchema={
                "type": "object",
                "properties": {
                    "booking_id": {"type": "string", "description": "Booking ID"}
                },
                "required": ["booking_id"]
            }
        ),
        Tool(
            name="attach_charges",
            description="Attach calculated charges to a booking",
            inputSchema={
                "type": "object",
                "properties": {
                    "booking_id": {"type": "string", "description": "Booking ID"},
                    "total_charges": {"type": "number", "description": "Total charges amount"}
                },
                "required": ["booking_id", "total_charges"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    if name == "create_booking":
        booking_id = arguments["booking_id"]
        if booking_id in bookings_db:
            return [TextContent(type="text", text=f"Error: Booking {booking_id} already exists.")]
        
        booking_data = {
            "booking_id": booking_id,
            "route_id": arguments["route_id"],
            "required_truck_type": arguments["required_truck_type"],
            "weight": arguments["weight"],
            "volume": arguments["volume"],
            "status": "pending",
            "assigned_truck_id": None,
            "location": "Origin",
            "total_charges": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "tracking_history": []
        }
        bookings_db[booking_id] = booking_data
        return [TextContent(type="text", text=f"Booking created successfully: {json.dumps(booking_data, indent=2)}")]

    elif name == "assign_truck":
        booking_id = arguments["booking_id"]
        truck_id = arguments["truck_id"]
        
        if booking_id not in bookings_db:
            return [TextContent(type="text", text=f"Error: Booking {booking_id} not found.")]
            
        bookings_db[booking_id]["assigned_truck_id"] = truck_id
        bookings_db[booking_id]["updated_at"] = datetime.now().isoformat()
        
        return [TextContent(type="text", text=f"Truck {truck_id} assigned to booking {booking_id}.")]

    elif name == "update_tracking":
        booking_id = arguments["booking_id"]
        if booking_id not in bookings_db:
            return [TextContent(type="text", text=f"Error: Booking {booking_id} not found.")]
            
        status = arguments["status"]
        location = arguments["location"]
        
        bookings_db[booking_id]["status"] = status
        bookings_db[booking_id]["location"] = location
        bookings_db[booking_id]["updated_at"] = datetime.now().isoformat()
        
        event = {
            "status": status,
            "location": location,
            "timestamp": datetime.now().isoformat()
        }
        bookings_db[booking_id]["tracking_history"].append(event)
        
        return [TextContent(type="text", text=f"Tracking updated for booking {booking_id}: {json.dumps(event, indent=2)}")]

    elif name == "get_booking_status":
        booking_id = arguments["booking_id"]
        if booking_id not in bookings_db:
            return [TextContent(type="text", text=f"Error: Booking {booking_id} not found.")]
            
        return [TextContent(type="text", text=json.dumps(bookings_db[booking_id], indent=2))]

    elif name == "attach_charges":
        booking_id = arguments["booking_id"]
        if booking_id not in bookings_db:
            return [TextContent(type="text", text=f"Error: Booking {booking_id} not found.")]
            
        bookings_db[booking_id]["total_charges"] = arguments["total_charges"]
        bookings_db[booking_id]["updated_at"] = datetime.now().isoformat()
        
        return [TextContent(type="text", text=f"Charges of {arguments['total_charges']} attached to booking {booking_id}.")]

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
