#!/usr/bin/env python3
"""
Agent Orchestrator (OpenAI GPT-4o version)
Demonstrates how multiple agents communicate via MCP servers
"""

import asyncio
import json
from dotenv import load_dotenv
load_dotenv()  # loads OPENAI_API_KEY from .env file

from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

client = OpenAI()  # reads OPENAI_API_KEY from environment

PYTHON = "/opt/homebrew/bin/python3.11"
BASE = "/Users/harvindersingh/Documents/tech/MCP - Multi agent "


async def get_openai_tools(session):
    """Convert MCP tool definitions to OpenAI function-calling format."""
    result = await session.list_tools()
    tools = []
    for tool in result.tools:
        tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema or {"type": "object", "properties": {}},
            },
        })
    return tools


async def call_mcp_tool(session, tool_name, tool_args):
    """Forward an OpenAI tool call to the appropriate MCP server."""
    result = await session.call_tool(tool_name, tool_args)
    if result.content:
        item = result.content[0]
        return item.text if hasattr(item, "text") else str(item)
    return "Tool executed successfully"


async def run_agent(
    agent_name, user_message,
    product_session, pricing_session,
    product_tool_names, pricing_tool_names,
    all_tools,
):
    """Agentic loop: call GPT-4o, handle tool calls via MCP, repeat until done."""
    print(f"\n{'='*60}")
    print(f"{agent_name} - Starting workflow")
    print("=" * 60)

    messages = [{"role": "user", "content": user_message}]

    while True:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=all_tools,
            tool_choice="auto",
        )

        choice = response.choices[0]
        msg = choice.message

        # Append assistant turn (serialisable dict)
        assistant_msg = {"role": "assistant", "content": msg.content}
        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ]
        messages.append(assistant_msg)

        if choice.finish_reason == "tool_calls" and msg.tool_calls:
            for tc in msg.tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments)

                print(f"\n[{agent_name}] → Tool: {name}")
                print(f"[{agent_name}]   Args: {json.dumps(args, indent=2)}")

                # Route to the right MCP server
                if name in product_tool_names:
                    result = await call_mcp_tool(product_session, name, args)
                elif name in pricing_tool_names:
                    result = await call_mcp_tool(pricing_session, name, args)
                else:
                    result = f"Unknown tool: {name}"

                print(f"[{agent_name}]   Result: {result}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result),
                })
        else:
            print(f"\n[{agent_name}] ✓ Done: {msg.content}")
            return msg.content


async def main():
    print("\n" + "=" * 60)
    print("MCP AGENT COMMUNICATION DEMO  (OpenAI GPT-4o-mini)")
    print("=" * 60)
    print("\nAgents:")
    print("  1. Product Creation Agent  - Creates products")
    print("  2. Pricing Update Agent    - Updates prices")
    print("  3. Discount Workflow Agent - Applies discounts")

    product_params = StdioServerParameters(
        command=PYTHON, args=[f"{BASE}/product_server.py"]
    )
    pricing_params = StdioServerParameters(
        command=PYTHON, args=[f"{BASE}/pricing_server.py"]
    )

    async with stdio_client(product_params) as (pr, pw):
        async with stdio_client(pricing_params) as (rr, rw):
            async with ClientSession(pr, pw) as product_session:
                async with ClientSession(rr, rw) as pricing_session:
                    await product_session.initialize()
                    await pricing_session.initialize()

                    product_tools = await get_openai_tools(product_session)
                    pricing_tools = await get_openai_tools(pricing_session)
                    all_tools = product_tools + pricing_tools

                    product_tool_names = {t["function"]["name"] for t in product_tools}
                    pricing_tool_names = {t["function"]["name"] for t in pricing_tools}

                    kwargs = dict(
                        product_session=product_session,
                        pricing_session=pricing_session,
                        product_tool_names=product_tool_names,
                        pricing_tool_names=pricing_tool_names,
                        all_tools=all_tools,
                    )

                    # --- Scenario 1 ---
                    print("\n\n### SCENARIO 1: Create New Product with Price ###")
                    await run_agent(
                        "PRODUCT CREATION AGENT",
                        """Create a new product with this data:
{
  "product_id": "LAPTOP-001",
  "name": "Professional Laptop Pro 15",
  "description": "High-performance laptop for professionals",
  "category": "Electronics",
  "price": 1299.99,
  "currency": "USD"
}
After creating the product, also create a price for it using the price info above.""",
                        **kwargs,
                    )

                    await asyncio.sleep(1)

                    # --- Scenario 2 ---
                    print("\n\n### SCENARIO 2: Update Product Price ###")
                    await run_agent(
                        "PRICING UPDATE AGENT",
                        'Get the product details for product_id: LAPTOP-001. '
                        'Then update the price to $1199.99 with reason: "Holiday sale pricing". '
                        'Finally, retrieve the price history to confirm the update.',
                        **kwargs,
                    )

                    await asyncio.sleep(1)

                    # --- Scenario 3 ---
                    print("\n\n### SCENARIO 3: Apply Discount ###")
                    await run_agent(
                        "DISCOUNT WORKFLOW AGENT",
                        "Apply a 15% discount to product LAPTOP-001. "
                        "First get the product details and current price, "
                        "then apply the discount, "
                        "then show the price history to confirm it was applied.",
                        **kwargs,
                    )

    print("\n\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("- Agents communicate through standardised MCP tool interfaces")
    print("- Each agent specialises in its domain (products or pricing)")
    print("- GPT-4o orchestrates multi-tool workflows automatically")
    print("- MCP enables modular, scalable agent architectures")


if __name__ == "__main__":
    asyncio.run(main())
