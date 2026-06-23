# MCP Multi-Agent System: Product & Pricing Management

A practical implementation of Model Context Protocol (MCP) demonstrating how multiple agents communicate and collaborate through standardized tool interfaces.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                  Agent Orchestrator                      │
│            (Claude with Anthropic API)                   │
└──────────────┬──────────────────┬──────────────────────┘
               │                  │
               │                  │
       ┌───────▼────────┐  ┌─────▼──────────┐
       │  Product MCP   │  │  Pricing MCP   │
       │    Server      │  │    Server      │
       └───────┬────────┘  └─────┬──────────┘
               │                  │
       ┌───────▼────────┐  ┌─────▼──────────┐
       │  Products DB   │  │   Prices DB    │
       │  (in-memory)   │  │  (in-memory)   │
       └────────────────┘  └────────────────┘
```

## Components

### 1. Product MCP Server (`product_server.py`)
Manages product lifecycle with these tools:
- `create_product` - Create new products
- `get_product` - Retrieve product details
- `list_products` - List all products
- `update_product` - Update product information

### 2. Pricing MCP Server (`pricing_server.py`)
Manages pricing with these tools:
- `create_price` - Set initial product price
- `update_price` - Update price with history tracking
- `get_price` - Get current price
- `get_price_history` - View price change history
- `list_all_prices` - List all product prices
- `apply_discount` - Apply percentage discounts

### 3. Agent Orchestrator (`agent_orchestrator.py`)
Demonstrates three agent patterns:

**Product Creation Agent**
- Creates products
- Coordinates with pricing to set initial prices
- Multi-tool workflow execution

**Pricing Update Agent**
- Validates products exist
- Updates prices with reasoning
- Maintains price history

**Discount Workflow Agent**
- Retrieves product and price data
- Applies business logic (discounts)
- Tracks changes across both systems

## Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Environment Variable
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

### 3. Configure MCP Servers

For Claude Desktop, add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "product-manager": {
      "command": "python",
      "args": ["/absolute/path/to/product_server.py"]
    },
    "pricing-manager": {
      "command": "python",
      "args": ["/absolute/path/to/pricing_server.py"]
    }
  }
}
```

## Usage

### Option 1: Run the Demo Orchestrator
```bash
python agent_orchestrator.py
```

This runs three scenarios:
1. Create product with initial price
2. Update price with reason
3. Apply discount and track history

### Option 2: Run MCP Servers Directly

**Terminal 1 - Product Server:**
```bash
python product_server.py
```

**Terminal 2 - Pricing Server:**
```bash
python pricing_server.py
```

**Terminal 3 - Use with Claude Desktop:**
Open Claude Desktop and use natural language:
- "Create a laptop product called 'MacBook Pro 16' in Electronics category"
- "Set the price to $2499 USD for product LAPTOP-001"
- "Apply a 20% discount to LAPTOP-001"

## Example Workflows

### Workflow 1: New Product Launch
```python
# Agent 1: Product Creation
1. create_product(id="PHONE-001", name="Smartphone X", category="Electronics")

# Agent 2: Pricing
2. create_price(product_id="PHONE-001", price=799.99, currency="USD")

# Result: Product live with pricing
```

### Workflow 2: Price Update with History
```python
# Agent 1: Check product exists
1. get_product(product_id="PHONE-001")

# Agent 2: Update price
2. update_price(product_id="PHONE-001", price=749.99, reason="Competitor pricing")

# Agent 2: Verify history
3. get_price_history(product_id="PHONE-001")

# Result: Price updated with audit trail
```

### Workflow 3: Promotional Discount
```python
# Agent 1: Validate product
1. get_product(product_id="PHONE-001")

# Agent 2: Check current price
2. get_price(product_id="PHONE-001")

# Agent 2: Apply discount
3. apply_discount(product_id="PHONE-001", discount_percent=15)

# Result: Promotional price with tracking
```

## Key Features

### 🔄 Agent Communication
- Agents communicate through standardized MCP tool interfaces
- No direct coupling between agents
- Each agent has specialized domain knowledge

### 📊 Data Consistency
- Shared product_id as the coordination key
- Price history maintains audit trail
- Validation across agent boundaries

### 🎯 Modularity
- Add new MCP servers without changing existing code
- Agents are independently deployable
- Tools are composable and reusable

### 🔐 Separation of Concerns
- Product agent: Product data and lifecycle
- Pricing agent: Pricing logic and history
- Orchestrator: Business workflows and coordination

## Extending the System

### Add New MCP Server
```python
# 1. Create new server (e.g., inventory_server.py)
app = Server("inventory-manager")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(name="check_stock", ...),
        Tool(name="update_inventory", ...)
    ]

# 2. Add to mcp_config.json
{
  "inventory-manager": {
    "command": "python",
    "args": ["inventory_server.py"]
  }
}

# 3. Use in agent workflows
tools=[{
    "type": "mcp_tool",
    "mcp_tool": {
        "name": "check_stock",
        "server_name": "inventory-manager"
    }
}]
```

### Add New Agent
```python
async def inventory_agent(product_id, quantity):
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        tools=[...],  # Include relevant MCP tools
        messages=[{
            "role": "user",
            "content": f"Check and update inventory for {product_id}"
        }]
    )
    return response
```

## Best Practices

1. **Tool Granularity**: Keep tools focused on single responsibilities
2. **Error Handling**: Return clear error messages in tool responses
3. **Data Validation**: Validate inputs at the MCP server level
4. **History Tracking**: Maintain audit trails for critical operations
5. **Idempotency**: Design tools to be safely retryable
6. **Documentation**: Provide clear tool descriptions for Claude

## Testing

### Unit Test MCP Servers
```bash
# Test product creation
echo '{"product_id": "TEST-001", "name": "Test", "category": "Test"}' | \
  python -c "import sys, json; from product_server import create_product; \
  print(create_product(**json.load(sys.stdin)))"
```

### Integration Test
```bash
python agent_orchestrator.py
```

## Troubleshooting

**Issue: Tools not appearing in Claude Desktop**
- Verify MCP servers are running
- Check config file paths are absolute
- Restart Claude Desktop

**Issue: Tool calls failing**
- Check ANTHROPIC_API_KEY is set
- Verify server names match config
- Check tool input schemas

**Issue: Agent coordination problems**
- Ensure product_id consistency
- Verify tools return proper JSON
- Check error handling in agents

## Learn More

- [MCP Documentation](https://modelcontextprotocol.io/)
- [Anthropic API Docs](https://docs.anthropic.com/)
- [Claude Tool Use Guide](https://docs.anthropic.com/claude/docs/tool-use)

## License

MIT License - Feel free to use and modify for your projects.
