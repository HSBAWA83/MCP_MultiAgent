#!/usr/bin/env python3
"""
TMS Agent Orchestrator (OpenAI GPT-4o-mini version)
Demonstrates multi-agent communication via 3 TMS MCP servers
"""

import asyncio
import json
import contextlib
from dotenv import load_dotenv
load_dotenv()  # loads OPENAI_API_KEY from .env file

from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

client = OpenAI()

PYTHON = "/opt/homebrew/bin/python3.11"
BASE = "/Users/harvindersingh/Documents/tech/MCP - Multi agent "

async def get_openai_tools(session):
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
    result = await session.call_tool(tool_name, tool_args)
    if result.content:
        item = result.content[0]
        return item.text if hasattr(item, "text") else str(item)
    return "Tool executed successfully"

async def run_agent(
    agent_name, user_message,
    fleet_session, finance_session, booking_session,
    fleet_tools, finance_tools, booking_tools,
    all_tools,
):
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

                if name in fleet_tools:
                    result = await call_mcp_tool(fleet_session, name, args)
                elif name in finance_tools:
                    result = await call_mcp_tool(finance_session, name, args)
                elif name in booking_tools:
                    result = await call_mcp_tool(booking_session, name, args)
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

@contextlib.asynccontextmanager
async def setup_mcp_clients():
    fleet_params = StdioServerParameters(command=PYTHON, args=[f"{BASE}/tms_fleet_server.py"])
    finance_params = StdioServerParameters(command=PYTHON, args=[f"{BASE}/tms_finance_server.py"])
    booking_params = StdioServerParameters(command=PYTHON, args=[f"{BASE}/tms_booking_server.py"])

    async with stdio_client(fleet_params) as (fr, fw):
        async with stdio_client(finance_params) as (fin_r, fin_w):
            async with stdio_client(booking_params) as (br, bw):
                async with ClientSession(fr, fw) as fleet_session:
                    async with ClientSession(fin_r, fin_w) as finance_session:
                        async with ClientSession(br, bw) as booking_session:
                            await fleet_session.initialize()
                            await finance_session.initialize()
                            await booking_session.initialize()
                            
                            yield fleet_session, finance_session, booking_session

async def main():
    print("\n" + "=" * 60)
    print("TMS MULTI-AGENT COMMUNICATION DEMO (OpenAI GPT-4o-mini)")
    print("=" * 60)

    async with setup_mcp_clients() as (fleet_session, finance_session, booking_session):
        fleet_tools_raw = await get_openai_tools(fleet_session)
        finance_tools_raw = await get_openai_tools(finance_session)
        booking_tools_raw = await get_openai_tools(booking_session)
        
        all_tools = fleet_tools_raw + finance_tools_raw + booking_tools_raw

        fleet_tool_names = {t["function"]["name"] for t in fleet_tools_raw}
        finance_tool_names = {t["function"]["name"] for t in finance_tools_raw}
        booking_tool_names = {t["function"]["name"] for t in booking_tools_raw}

        kwargs = dict(
            fleet_session=fleet_session,
            finance_session=finance_session,
            booking_session=booking_session,
            fleet_tools=fleet_tool_names,
            finance_tools=finance_tool_names,
            booking_tools=booking_tool_names,
            all_tools=all_tools,
        )

        # --- Scenario 1: Initialization ---
        print("\n\n### SCENARIO 1: Initialize Fleet and Rate Cards ###")
        await run_agent(
            "INITIALIZATION AGENT",
            """Please initialize our TMS system by:
1. Adding a new flatbed truck (truck_id: 'TRK-001') with 20000kg capacity and 40cbm volume.
2. Adding a new refrigerated truck (truck_id: 'TRK-002') with 15000kg capacity and 30cbm volume.
3. Adding a rate card for route 'NY-LA' for 'flatbed' trucks with a base rate of 3500.
4. Adding a rate card for route 'NY-LA' for 'refrigerated' trucks with a base rate of 4200.
""",
            **kwargs,
        )

        await asyncio.sleep(1)

        # --- Scenario 2: Dispatcher creates booking and assigns truck ---
        print("\n\n### SCENARIO 2: Dispatcher creates booking ###")
        await run_agent(
            "DISPATCHER AGENT",
            """We have a new load from NY to LA that requires a flatbed. It weighs 18000kg and needs 35cbm.
1. Check truck capacity to find an available truck matching these requirements.
2. If available, create a booking (booking_id: 'BKG-001', route_id: 'NY-LA', etc.)
3. Assign the available truck to the booking.
4. Update the truck status to 'in-transit'.
""",
            **kwargs,
        )

        await asyncio.sleep(1)

        # --- Scenario 3: Billing agent calculates and attaches charges ---
        print("\n\n### SCENARIO 3: Billing Agent calculates charges ###")
        await run_agent(
            "BILLING AGENT",
            """Please process billing for booking 'BKG-001':
1. Retrieve the booking details to find the route and required truck type.
2. Calculate the charges for this route and truck type with an accessorial charge of 250 (for tolls).
3. Attach the total calculated charges to the booking.
""",
            **kwargs,
        )
        
        await asyncio.sleep(1)

        # --- Scenario 4: Customer service agent tracking ---
        print("\n\n### SCENARIO 4: Tracking Update ###")
        await run_agent(
            "TRACKING AGENT",
            """A customer is asking for an update on booking 'BKG-001'.
1. Update its tracking location to 'Chicago, IL'.
2. Retrieve the full booking status and tell me the summary of its status, assigned truck, and total charges.
""",
            **kwargs,
        )

    print("\n\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
