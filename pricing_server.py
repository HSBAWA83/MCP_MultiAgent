#!/usr/bin/env python3
"""
Pricing Management MCP Server
Handles price creation, updates, and price history
"""

import asyncio
import json
from typing import Any
from datetime import datetime
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

# In-memory storage
prices_db = {}
price_history = {}

app = Server("pricing-manager")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="create_price",
            description="Create a price for a product",
            inputSchema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product ID to price"},
                    "price": {"type": "number", "description": "Price amount"},
                    "currency": {"type": "string", "description": "Currency code (e.g., USD, EUR)"},
                },
                "required": ["product_id", "price", "currency"]
            }
        ),
        Tool(
            name="update_price",
            description="Update the price for a product",
            inputSchema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product ID"},
                    "price": {"type": "number", "description": "New price amount"},
                    "reason": {"type": "string", "description": "Reason for price change"}
                },
                "required": ["product_id", "price"]
            }
        ),
        Tool(
            name="get_price",
            description="Get current price for a product",
            inputSchema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product ID"}
                },
                "required": ["product_id"]
            }
        ),
        Tool(
            name="get_price_history",
            description="Get price history for a product",
            inputSchema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product ID"}
                },
                "required": ["product_id"]
            }
        ),
        Tool(
            name="list_all_prices",
            description="List all product prices",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="apply_discount",
            description="Apply a percentage discount to a product",
            inputSchema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product ID"},
                    "discount_percent": {"type": "number", "description": "Discount percentage (0-100)"}
                },
                "required": ["product_id", "discount_percent"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    if name == "create_price":
        product_id = arguments["product_id"]
        if product_id in prices_db:
            return [TextContent(
                type="text",
                text=f"Error: Price already exists for product {product_id}. Use update_price instead."
            )]
        
        price_data = {
            "product_id": product_id,
            "price": arguments["price"],
            "currency": arguments["currency"],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        prices_db[product_id] = price_data
        price_history[product_id] = [price_data.copy()]
        
        return [TextContent(
            type="text",
            text=f"Price created successfully: {json.dumps(price_data, indent=2)}"
        )]
    
    elif name == "update_price":
        product_id = arguments["product_id"]
        if product_id not in prices_db:
            return [TextContent(
                type="text",
                text=f"Error: No price found for product {product_id}. Use create_price first."
            )]
        
        old_price = prices_db[product_id]["price"]
        new_price = arguments["price"]
        
        price_data = {
            "product_id": product_id,
            "price": new_price,
            "currency": prices_db[product_id]["currency"],
            "previous_price": old_price,
            "change_percent": round(((new_price - old_price) / old_price) * 100, 2),
            "reason": arguments.get("reason", "Price update"),
            "updated_at": datetime.now().isoformat()
        }
        
        prices_db[product_id].update({
            "price": new_price,
            "previous_price": old_price,
            "updated_at": price_data["updated_at"]
        })
        
        price_history[product_id].append(price_data.copy())
        
        return [TextContent(
            type="text",
            text=f"Price updated successfully: {json.dumps(price_data, indent=2)}"
        )]
    
    elif name == "get_price":
        product_id = arguments["product_id"]
        if product_id not in prices_db:
            return [TextContent(
                type="text",
                text=f"Error: No price found for product {product_id}"
            )]
        
        return [TextContent(
            type="text",
            text=json.dumps(prices_db[product_id], indent=2)
        )]
    
    elif name == "get_price_history":
        product_id = arguments["product_id"]
        if product_id not in price_history:
            return [TextContent(
                type="text",
                text=f"Error: No price history found for product {product_id}"
            )]
        
        return [TextContent(
            type="text",
            text=json.dumps(price_history[product_id], indent=2)
        )]
    
    elif name == "list_all_prices":
        if not prices_db:
            return [TextContent(
                type="text",
                text="No prices found"
            )]
        
        return [TextContent(
            type="text",
            text=json.dumps(list(prices_db.values()), indent=2)
        )]
    
    elif name == "apply_discount":
        product_id = arguments["product_id"]
        discount_percent = arguments["discount_percent"]
        
        if product_id not in prices_db:
            return [TextContent(
                type="text",
                text=f"Error: No price found for product {product_id}"
            )]
        
        if discount_percent < 0 or discount_percent > 100:
            return [TextContent(
                type="text",
                text="Error: Discount must be between 0 and 100"
            )]
        
        current_price = prices_db[product_id]["price"]
        discounted_price = round(current_price * (1 - discount_percent / 100), 2)
        
        # Update the price with discount reason
        old_price = prices_db[product_id]["price"]
        prices_db[product_id].update({
            "price": discounted_price,
            "previous_price": old_price,
            "discount_applied": discount_percent,
            "updated_at": datetime.now().isoformat()
        })
        
        price_history[product_id].append({
            "product_id": product_id,
            "price": discounted_price,
            "previous_price": old_price,
            "reason": f"Applied {discount_percent}% discount",
            "updated_at": datetime.now().isoformat()
        })
        
        return [TextContent(
            type="text",
            text=f"Discount applied: {discount_percent}% off. New price: {discounted_price} {prices_db[product_id]['currency']}"
        )]
    
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
