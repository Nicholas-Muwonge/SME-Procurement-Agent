"""
Tools Implementation – SME Procurement-Preparation Agent
Week 4 – Tools & Function Calling
"""

import json
import os
from datetime import datetime, date
from typing import Dict, Any, List
import uuid
from memory import rank_quotations_with_preferences

# ----------------------------
# Paths to synthetic data
# ----------------------------
INVENTORY_FILE = "data/inventory.json"
QUOTATIONS_FILE = "data/quotations.json"
REQUISITIONS_FILE = "data/requisitions.json"   # will be created automatically


# ----------------------------
# Helper functions
# ----------------------------
def load_json(path: str) -> List[Dict]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: List[Dict]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def find_item(data: List[Dict], item_id: str) -> Dict | None:
    for item in data:
        if item.get("item_id") == item_id:
            return item
    return None


# ----------------------------
# TOOL 1: get_inventory
# ----------------------------
def get_inventory(item_id: str) -> Dict[str, Any]:
    """
    Retrieve current inventory record for a given item.
    """
    if not item_id or not isinstance(item_id, str):
        return {
            "error": "ValidationError",
            "message": "item_id is required and must be a string"
        }

    inventory = load_json(INVENTORY_FILE)
    item = find_item(inventory, item_id)

    if not item:
        return {
            "error": "NotFound",
            "message": f"Item '{item_id}' not found in inventory"
        }

    current_stock = item.get("current_stock", 0)
    reorder_point = item.get("reorder_point", 0)

    status = "REORDER_REQUIRED" if current_stock <= reorder_point else "OK"

    return {
        "item_id": item["item_id"],
        "item_name": item.get("item_name", ""),
        "current_stock": current_stock,
        "reorder_point": reorder_point,
        "reorder_qty": item.get("reorder_qty", 0),
        "avg_monthly_usage": item.get("avg_monthly_usage", 0),
        "lead_time_days": item.get("lead_time_days", 0),
        "unit": item.get("unit", "pcs"),
        "status": status,
        "quotations": rank_quotations,
        #"message": f"Found {len(matching)} quotation(s). Preferred suppliers (if any) are shown first."
    
    }


# ----------------------------
# TOOL 2: get_quotations
# ----------------------------
def get_quotations(item_id: str) -> Dict[str, Any]:
    """
    Retrieve all valid supplier quotations for a given item.
    """
    if not item_id or not isinstance(item_id, str):
        return {
            "error": "ValidationError",
            "message": "item_id is required and must be a string"
        }

    quotations = load_json(QUOTATIONS_FILE)
    today = date.today()

    matching = []
    for q in quotations:
        if q.get("item_id") != item_id:
            continue

        valid_until_str = q.get("valid_until")
        is_valid = False

        if valid_until_str:
            try:
                valid_until = datetime.strptime(valid_until_str, "%Y-%m-%d").date()
                is_valid = valid_until >= today
            except ValueError:
                is_valid = False

        matching.append({
            "quotation_id": q.get("quotation_id"),
            "supplier_name": q.get("supplier_name"),
            "unit_price": q.get("unit_price"),
            "currency": q.get("currency", "UGX"),
            "lead_time_days": q.get("lead_time_days"),
            "valid_until": valid_until_str,
            "is_valid": is_valid
        })

    # Sort valid ones by unit price
    matching.sort(key=lambda x: (not x["is_valid"], x["unit_price"] or 999999))

    if not matching:
        return {
            "item_id": item_id,
            "quotations": [],
            "message": f"No quotations found for item '{item_id}'"
        }

    valid_count = sum(1 for q in matching if q["is_valid"])
    message = f"Found {len(matching)} quotation(s), {valid_count} valid."

    return {
        "item_id": item_id,
        "quotations": matching,
        "message": message
    }


# ----------------------------
# TOOL 3: create_draft_requisition
# ----------------------------
def create_draft_requisition(
    item_id: str,
    quantity: float,
    justification: str,
    requested_by: str
) -> Dict[str, Any]:
    """
    Create a new purchase requisition in Draft status.
    """
    # Validation
    if not item_id or not isinstance(item_id, str):
        return {"error": "ValidationError", "message": "item_id is required"}

    if not isinstance(quantity, (int, float)) or quantity < 1:
        return {"error": "ValidationError", "message": "quantity must be a number >= 1"}

    if not justification or not isinstance(justification, str):
        return {"error": "ValidationError", "message": "justification is required"}

    if not requested_by or not isinstance(requested_by, str):
        return {"error": "ValidationError", "message": "requested_by is required"}

    # Check item exists
    inventory = load_json(INVENTORY_FILE)
    item = find_item(inventory, item_id)
    if not item:
        return {
            "error": "NotFound",
            "message": f"Item '{item_id}' not found in inventory"
        }

    # Create draft
    requisitions = load_json(REQUISITIONS_FILE)

    new_req = {
        "requisition_id": f"PR-{str(uuid.uuid4())[:8].upper()}",
        "item_id": item_id,
        "item_name": item.get("item_name", ""),
        "quantity": int(quantity),
        "unit": item.get("unit", "pcs"),
        "justification": justification,
        "requested_by": requested_by,
        "status": "Draft – Awaiting Approval",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "approved_by": None,
        "approved_at": None
    }

    requisitions.append(new_req)
    save_json(REQUISITIONS_FILE, requisitions)

    return {
        "requisition_id": new_req["requisition_id"],
        "item_id": new_req["item_id"],
        "quantity": new_req["quantity"],
        "status": new_req["status"],
        "created_at": new_req["created_at"],
        "message": "Draft requisition created successfully. Awaiting human approval."
    }


# ----------------------------
# OpenAI Tools Definition
# (for function calling)
# ----------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_inventory",
            "description": "Retrieve current stock level, reorder point and related information for a specific inventory item.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "The unique item identifier (e.g. ITM-001)"
                    }
                },
                "required": ["item_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_quotations",
            "description": "Retrieve all supplier quotations for a specific item, including validity status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "The unique item identifier"
                    }
                },
                "required": ["item_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_draft_requisition",
            "description": "Create a new purchase requisition in Draft status. Requires human approval before any further action.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "Item to request"
                    },
                    "quantity": {
                        "type": "number",
                        "description": "Quantity to request (must be >= 1)"
                    },
                    "justification": {
                        "type": "string",
                        "description": "Reason for creating the requisition"
                    },
                    "requested_by": {
                        "type": "string",
                        "description": "Name or ID of the person creating the draft"
                    }
                },
                "required": ["item_id", "quantity", "justification", "requested_by"],
                "additionalProperties": False
            }
        }
    }
]


# Mapping from tool name to actual function
TOOL_FUNCTIONS = {
    "get_inventory": get_inventory,
    "get_quotations": get_quotations,
    "create_draft_requisition": create_draft_requisition
}


def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Safe wrapper to execute a tool by name.
    """
    if name not in TOOL_FUNCTIONS:
        return {"error": "UnknownTool", "message": f"Tool '{name}' is not available"}

    try:
        func = TOOL_FUNCTIONS[name]
        result = func(**arguments)
        return result
    except Exception as e:
        return {
            "error": "ToolExecutionError",
            "message": str(e)
        }