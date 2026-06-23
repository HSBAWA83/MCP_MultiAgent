#!/usr/bin/env python3
"""
Product Management MCP Server
Handles product creation, retrieval, and management
"""

import asyncio
import json
from typing import Any
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

# In-memory storage
products_db = {}

app = Server("product-manager")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="create_product",
            description="Create a new product with name, description, and category",
            inputSchema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Unique product ID"},
                    "name": {"type": "string", "description": "Product name"},
                    "description": {"type": "string", "description": "Product description"},
                    "category": {"type": "string", "description": "Product category"},
                },
                "required": ["product_id", "name", "category"]
            }
        ),
        Tool(
            name="get_product",
            description="Retrieve product details by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product ID to retrieve"}
                },
                "required": ["product_id"]
            }
        ),
        Tool(
            name="list_products",
            description="List all products",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="update_product",
            description="Update product details",
            inputSchema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product ID to update"},
                    "name": {"type": "string", "description": "New product name"},
                    "description": {"type": "string", "description": "New description"},
                    "category": {"type": "string", "description": "New category"},
                },
                "required": ["product_id"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    if name == "create_product":
        product_id = arguments["product_id"]
        if product_id in products_db:
            return [TextContent(
                type="text",
                text=f"Error: Product {product_id} already exists"
            )]
        
        products_db[product_id] = {
            "product_id": product_id,
            "name": arguments["name"],
            "description": arguments.get("description", ""),
            "category": arguments["category"],
            "status": "active"
        }
        
        return [TextContent(
            type="text",
            text=f"Product created successfully: {json.dumps(products_db[product_id], indent=2)}"
        )]
    
    elif name == "get_product":
        product_id = arguments["product_id"]
        if product_id not in products_db:
            return [TextContent(
                type="text",
                text=f"Error: Product {product_id} not found"
            )]
        
        return [TextContent(
            type="text",
            text=json.dumps(products_db[product_id], indent=2)
        )]
    
    elif name == "list_products":
        if not products_db:
            return [TextContent(
                type="text",
                text="No products found"
            )]
        
        return [TextContent(
            type="text",
            text=json.dumps(list(products_db.values()), indent=2)
        )]
    
    elif name == "update_product":
        product_id = arguments["product_id"]
        if product_id not in products_db:
            return [TextContent(
                type="text",
                text=f"Error: Product {product_id} not found"
            )]
        
        if "name" in arguments:
            products_db[product_id]["name"] = arguments["name"]
        if "description" in arguments:
            products_db[product_id]["description"] = arguments["description"]
        if "category" in arguments:
            products_db[product_id]["category"] = arguments["category"]
        
        return [TextContent(
            type="text",
            text=f"Product updated successfully: {json.dumps(products_db[product_id], indent=2)}"
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
