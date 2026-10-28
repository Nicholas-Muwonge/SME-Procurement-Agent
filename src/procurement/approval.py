import json
import os
from datetime import datetime
from typing import Dict, Any, List

REQUISITIONS_FILE = "data/requisitions.json"


def load_requisitions() -> List[Dict[str, Any]]:
    if not os.path.exists(REQUISITIONS_FILE):
        return []
    try:
        with open(REQUISITIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []


def save_requisitions(data: List[Dict[str, Any]]):
    os.makedirs(os.path.dirname(REQUISITIONS_FILE), exist_ok=True)
    with open(REQUISITIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def review_requisition(requisition_id: str, action: str, approver_name: str) -> Dict[str, Any]:
    """
    Approve or reject a draft purchase requisition.
    action: 'approve' or 'reject'
    """
    requisitions = load_requisitions()
    found = False

    for req in requisitions:
        if req["requisition_id"] == requisition_id:
            found = True
            
            if "Draft" not in req["status"]:
                return {
                    "success": False, 
                    "message": f"Requisition {requisition_id} has already been processed ({req['status']})."
                }

            action_lower = action.lower()
            if action_lower == "approve":
                req["status"] = "Approved"
                req["approved_by"] = approver_name
                req["approved_at"] = datetime.now().isoformat(timespec="seconds")
            elif action_lower == "reject":
                req["status"] = "Rejected"
                req["approved_by"] = approver_name
                req["approved_at"] = datetime.now().isoformat(timespec="seconds")
            else:
                return {"success": False, "message": "Invalid action. Choose 'approve' or 'reject'."}
            
            break

    if not found:
        return {"success": False, "message": f"Requisition ID '{requisition_id}' not found."}

    save_requisitions(requisitions)
    return {
        "success": True, 
        "message": f"Requisition {requisition_id} successfully marked as {req['status']} by {approver_name}."
    }