"""
Preferred Suppliers Memory
SME Procurement-Preparation Agent – Week 6
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional

MEMORY_FILE = "data/preferred_suppliers.json"

def _load_memory() -> List[Dict]:
    """Load preferred suppliers from disk."""
    if not os.path.exists(MEMORY_FILE):
        return []
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save_memory(data: List[Dict]) -> None:
    """Save preferred suppliers to disk."""
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

def add_preferred_supplier(
    item_id: str,
    supplier_name: str,
    marked_by: str,
    quotation_id: Optional[str] = None,
    notes: Optional[str] = None
) -> Dict:
    """
    Mark a supplier as preferred for a specific item.
    If the preference already exists, it is updated.
    """
    if not item_id or not supplier_name or not marked_by:
        return {
            "success": False,
            "error": "item_id, supplier_name and marked_by are required"
        }

    memory = _load_memory()
    
    memory = [
        m for m in memory
        if not (m["item_id"] == item_id and m["supplier_name"].lower() == supplier_name.lower())
    ]

    new_entry = {
        "item_id": item_id,
        "supplier_name": supplier_name,
        "quotation_id": quotation_id,
        "marked_by": marked_by,
        "marked_at": datetime.now().isoformat(timespec="seconds"),
        "notes": notes or ""
    }

    memory.append(new_entry)
    _save_memory(memory)

    return {
        "success": True,
        "message": f"'{supplier_name}' marked as preferred for item {item_id}",
        "entry": new_entry
    }


def remove_preferred_supplier(item_id: str, supplier_name: str) -> Dict:
    """Remove a preferred supplier for a given item."""
    memory = _load_memory()
    original_count = len(memory)

    memory = [
        m for m in memory
        if not (m["item_id"] == item_id and m["supplier_name"].lower() == supplier_name.lower())
    ]

    if len(memory) == original_count:
        return {
            "success": False,
            "message": f"No preference found for '{supplier_name}' on item {item_id}"
        }

    _save_memory(memory)
    return {
        "success": True,
        "message": f"Preference for '{supplier_name}' on item {item_id} has been removed"
    }


def get_preferred_suppliers(item_id: str) -> List[Dict]:
    """
    Return all preferred suppliers for a specific item.
    Returns an empty list if none exist.
    """
    memory = _load_memory()
    return [m for m in memory if m["item_id"] == item_id]


def list_all_preferences() -> List[Dict]:
    """Return the entire preferred suppliers memory (for admin/debug)."""
    return _load_memory()


def clear_all_preferences() -> Dict:
    """Delete the entire preferred suppliers memory (use with caution)."""
    _save_memory([])
    return {"success": True, "message": "All preferred supplier preferences have been cleared"}

def rank_quotations_with_preferences(item_id: str, quotations: List[Dict]) -> List[Dict]:
    preferred = get_preferred_suppliers(item_id)
    preferred_names = {p["supplier_name"].lower() for p in preferred}

    preferred_quotes = []
    other_quotes = []

    for q in quotations:
        supplier = q.get("supplier_name", "").lower()
        if supplier in preferred_names:
            # Add a clear label
            q_with_label = q.copy()
            q_with_label["is_preferred"] = True
            q_with_label["preference_note"] = "Preferred supplier"
            preferred_quotes.append(q_with_label)
        else:
            q_with_label = q.copy()
            q_with_label["is_preferred"] = False
            other_quotes.append(q_with_label)

    return preferred_quotes + other_quotes