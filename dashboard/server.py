#!/usr/bin/env python3
"""
Dashboard API Server for MCP Multi-Agent System
Embeds product/pricing logic directly and exposes REST endpoints + agent runner.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

# Load API key from parent directory .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

app = FastAPI(title="MCP Agent Dashboard")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

client = OpenAI()

# ── In-memory stores ──────────────────────────────────────────────────────────
products_db: Dict[str, dict] = {}
prices_db: Dict[str, dict] = {}
price_history_db: Dict[str, List[dict]] = {}
activity_log: List[dict] = []


def _log(agent: str, action: str, details: Any):
    activity_log.append({
        "timestamp": datetime.now().isoformat(),
        "agent": agent,
        "action": action,
        "details": details,
    })


# ── Business logic (mirrors MCP servers) ─────────────────────────────────────
def _create_product(product_id, name, category, description=""):
    if product_id in products_db:
        existing = products_db[product_id]
        return {
            "error": "CONFLICT",
            "message": (
                f"Product '{product_id}' already exists. "
                "STOP — do not update or proceed automatically. "
                "You MUST ask the user: do they want to (1) update the existing product, "
                "or (2) create a new one with a different ID? "
                "Wait for explicit user confirmation before taking any further action."
            ),
            "existing_product": existing,
        }
    products_db[product_id] = {
        "product_id": product_id, "name": name,
        "description": description, "category": category, "status": "active",
    }
    return products_db[product_id]


def _get_product(product_id):
    return products_db.get(product_id, {"error": f"Product {product_id} not found"})


def _list_products():
    return list(products_db.values())


def _update_product(product_id, name=None, description=None, category=None):
    if product_id not in products_db:
        return {"error": f"Product {product_id} not found"}
    for field, val in [("name", name), ("description", description), ("category", category)]:
        if val is not None:
            products_db[product_id][field] = val
    return products_db[product_id]


def _create_price(product_id, price, currency="USD"):
    entry = {
        "product_id": product_id, "price": price, "currency": currency,
        "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat(),
    }
    prices_db[product_id] = entry
    price_history_db.setdefault(product_id, []).append(dict(entry))
    return entry


def _get_price(product_id):
    return prices_db.get(product_id, {"error": f"No price for {product_id}"})


def _update_price(product_id, price, reason=""):
    if product_id not in prices_db:
        return {"error": f"No price for {product_id}"}
    old = prices_db[product_id]["price"]
    entry = {
        "product_id": product_id, "price": price,
        "currency": prices_db[product_id].get("currency", "USD"),
        "previous_price": old,
        "change_percent": round((price - old) / old * 100, 2),
        "reason": reason,
        "updated_at": datetime.now().isoformat(),
    }
    prices_db[product_id] = entry
    price_history_db.setdefault(product_id, []).append(dict(entry))
    return entry


def _get_price_history(product_id):
    return price_history_db.get(product_id, [])


def _list_all_prices():
    return list(prices_db.values())


def _apply_discount(product_id, discount_percent):
    if product_id not in prices_db:
        return {"error": f"No price for {product_id}"}
    old = prices_db[product_id]["price"]
    new_price = round(old * (1 - discount_percent / 100), 2)
    return _update_price(product_id, new_price, reason=f"Applied {discount_percent}% discount")


# ── OpenAI tool definitions ───────────────────────────────────────────────────
ALL_TOOLS = [
    {"type": "function", "function": {
        "name": "create_product",
        "description": (
            "Create a new product. "
            "If the product ID already exists, the tool will return a CONFLICT error. "
            "On conflict you MUST stop immediately and ask the user whether they want to "
            "update the existing product or use a different product ID. "
            "Never autonomously resolve a conflict by calling update_product."
        ),
        "parameters": {"type": "object", "properties": {
            "product_id": {"type": "string"}, "name": {"type": "string"},
            "category": {"type": "string"}, "description": {"type": "string"},
        }, "required": ["product_id", "name", "category"]},
    }},
    {"type": "function", "function": {
        "name": "get_product", "description": "Get a product by ID",
        "parameters": {"type": "object", "properties": {
            "product_id": {"type": "string"}}, "required": ["product_id"]},
    }},
    {"type": "function", "function": {
        "name": "list_products", "description": "List all products",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "update_product", "description": "Update product fields",
        "parameters": {"type": "object", "properties": {
            "product_id": {"type": "string"}, "name": {"type": "string"},
            "description": {"type": "string"}, "category": {"type": "string"},
        }, "required": ["product_id"]},
    }},
    {"type": "function", "function": {
        "name": "create_price", "description": "Set initial price for a product",
        "parameters": {"type": "object", "properties": {
            "product_id": {"type": "string"}, "price": {"type": "number"},
            "currency": {"type": "string"},
        }, "required": ["product_id", "price"]},
    }},
    {"type": "function", "function": {
        "name": "get_price", "description": "Get current price for a product",
        "parameters": {"type": "object", "properties": {
            "product_id": {"type": "string"}}, "required": ["product_id"]},
    }},
    {"type": "function", "function": {
        "name": "update_price", "description": "Update price with reason",
        "parameters": {"type": "object", "properties": {
            "product_id": {"type": "string"}, "price": {"type": "number"},
            "reason": {"type": "string"},
        }, "required": ["product_id", "price"]},
    }},
    {"type": "function", "function": {
        "name": "get_price_history", "description": "Get price change history",
        "parameters": {"type": "object", "properties": {
            "product_id": {"type": "string"}}, "required": ["product_id"]},
    }},
    {"type": "function", "function": {
        "name": "list_all_prices", "description": "List all product prices",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "apply_discount", "description": "Apply a percentage discount to a product",
        "parameters": {"type": "object", "properties": {
            "product_id": {"type": "string"}, "discount_percent": {"type": "number"},
        }, "required": ["product_id", "discount_percent"]},
    }},
]

TOOL_MAP = {
    "create_product":   lambda a: _create_product(**a),
    "get_product":      lambda a: _get_product(a["product_id"]),
    "list_products":    lambda a: _list_products(),
    "update_product":   lambda a: _update_product(**a),
    "create_price":     lambda a: _create_price(**a),
    "get_price":        lambda a: _get_price(a["product_id"]),
    "update_price":     lambda a: _update_price(**a),
    "get_price_history": lambda a: _get_price_history(a["product_id"]),
    "list_all_prices":  lambda a: _list_all_prices(),
    "apply_discount":   lambda a: _apply_discount(**a),
}


def run_agent(agent_name: str, user_message: str) -> dict:
    """Agentic loop: GPT-4o calls tools until done."""
    messages = [{"role": "user", "content": user_message}]
    steps = []
    _log(agent_name, "started", user_message)

    while True:
        response = client.chat.completions.create(
            model="gpt-4o", messages=messages,
            tools=ALL_TOOLS, tool_choice="auto",
        )
        choice = response.choices[0]
        msg = choice.message

        assistant_msg: dict = {"role": "assistant", "content": msg.content}
        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ]
        messages.append(assistant_msg)

        if choice.finish_reason == "tool_calls" and msg.tool_calls:
            for tc in msg.tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments)
                result = TOOL_MAP[name](args)
                steps.append({"tool": name, "args": args, "result": result})
                _log(agent_name, f"tool:{name}", {"args": args, "result": result})
                messages.append({
                    "role": "tool", "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })
        else:
            _log(agent_name, "completed", msg.content)
            return {"summary": msg.content, "steps": steps}


# ── REST Endpoints ────────────────────────────────────────────────────────────

# Products
@app.get("/api/products")
def api_list_products():
    return {"products": _list_products()}


@app.post("/api/products")
def api_create_product(body: dict):
    result = _create_product(**body)
    if "error" in result:
        raise HTTPException(400, result["error"])
    _log("Dashboard", "create_product", result)
    return result


@app.get("/api/products/{product_id}")
def api_get_product(product_id: str):
    result = _get_product(product_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@app.put("/api/products/{product_id}")
def api_update_product(product_id: str, body: dict):
    result = _update_product(product_id, **{k: v for k, v in body.items() if k != "product_id"})
    if "error" in result:
        raise HTTPException(404, result["error"])
    _log("Dashboard", "update_product", result)
    return result


# Prices
@app.get("/api/prices")
def api_list_prices():
    return {"prices": _list_all_prices()}


@app.post("/api/prices")
def api_create_price(body: dict):
    result = _create_price(**body)
    _log("Dashboard", "create_price", result)
    return result


@app.put("/api/prices/{product_id}")
def api_update_price(product_id: str, body: dict):
    result = _update_price(product_id, body["price"], body.get("reason", ""))
    if "error" in result:
        raise HTTPException(404, result["error"])
    _log("Dashboard", "update_price", result)
    return result


@app.post("/api/prices/{product_id}/discount")
def api_apply_discount(product_id: str, body: dict):
    result = _apply_discount(product_id, body["discount_percent"])
    if "error" in result:
        raise HTTPException(404, result["error"])
    _log("Dashboard", "apply_discount", result)
    return result


@app.get("/api/prices/{product_id}/history")
def api_price_history(product_id: str):
    return {"history": _get_price_history(product_id)}


# Activity
@app.get("/api/activity")
def api_activity():
    return {"activity": list(reversed(activity_log))}


# Agents
@app.post("/api/agents/run")
def api_run_agent(body: dict):
    agent_name = body.get("agent", "Agent")
    message = body.get("message", "").strip()
    if not message:
        raise HTTPException(400, "message is required")
    return run_agent(agent_name, message)


# Frontend
@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path) as f:
        return f.read()


if __name__ == "__main__":
    print("\n🚀  MCP Agent Dashboard starting at http://localhost:3000\n")
    uvicorn.run(app, host="0.0.0.0", port=3000)
