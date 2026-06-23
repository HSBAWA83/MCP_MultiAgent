#!/usr/bin/env python3
"""
Simple test script to verify MCP servers work correctly
Run this to test your MCP servers without using the Anthropic API
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_product_server():
    """Test Product MCP Server"""
    print("\n" + "="*60)
    print("Testing Product MCP Server")
    print("="*60)
    
    server_params = StdioServerParameters(
        command="python",
        args=["product_server.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Test 1: Create Product
            print("\n1. Creating product...")
            result = await session.call_tool(
                "create_product",
                arguments={
                    "product_id": "TEST-001",
                    "name": "Test Laptop",
                    "description": "A test laptop product",
                    "category": "Electronics"
                }
            )
            print(f"Result: {result.content[0].text}")
            
            # Test 2: Get Product
            print("\n2. Getting product...")
            result = await session.call_tool(
                "get_product",
                arguments={"product_id": "TEST-001"}
            )
            print(f"Result: {result.content[0].text}")
            
            # Test 3: List Products
            print("\n3. Listing all products...")
            result = await session.call_tool(
                "list_products",
                arguments={}
            )
            print(f"Result: {result.content[0].text}")
            
            # Test 4: Update Product
            print("\n4. Updating product...")
            result = await session.call_tool(
                "update_product",
                arguments={
                    "product_id": "TEST-001",
                    "name": "Updated Test Laptop",
                    "description": "An updated test laptop"
                }
            )
            print(f"Result: {result.content[0].text}")

async def test_pricing_server():
    """Test Pricing MCP Server"""
    print("\n" + "="*60)
    print("Testing Pricing MCP Server")
    print("="*60)
    
    server_params = StdioServerParameters(
        command="python",
        args=["pricing_server.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Test 1: Create Price
            print("\n1. Creating price...")
            result = await session.call_tool(
                "create_price",
                arguments={
                    "product_id": "TEST-001",
                    "price": 999.99,
                    "currency": "USD"
                }
            )
            print(f"Result: {result.content[0].text}")
            
            # Test 2: Get Price
            print("\n2. Getting price...")
            result = await session.call_tool(
                "get_price",
                arguments={"product_id": "TEST-001"}
            )
            print(f"Result: {result.content[0].text}")
            
            # Test 3: Update Price
            print("\n3. Updating price...")
            result = await session.call_tool(
                "update_price",
                arguments={
                    "product_id": "TEST-001",
                    "price": 899.99,
                    "reason": "Holiday sale"
                }
            )
            print(f"Result: {result.content[0].text}")
            
            # Test 4: Apply Discount
            print("\n4. Applying discount...")
            result = await session.call_tool(
                "apply_discount",
                arguments={
                    "product_id": "TEST-001",
                    "discount_percent": 20
                }
            )
            print(f"Result: {result.content[0].text}")
            
            # Test 5: Get Price History
            print("\n5. Getting price history...")
            result = await session.call_tool(
                "get_price_history",
                arguments={"product_id": "TEST-001"}
            )
            print(f"Result: {result.content[0].text}")
            
            # Test 6: List All Prices
            print("\n6. Listing all prices...")
            result = await session.call_tool(
                "list_all_prices",
                arguments={}
            )
            print(f"Result: {result.content[0].text}")

async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("MCP SERVER TESTING SUITE")
    print("="*60)
    
    try:
        await test_product_server()
        await test_pricing_server()
        
        print("\n" + "="*60)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
