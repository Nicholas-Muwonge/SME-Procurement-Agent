import json
from datetime import date, timedelta
import pytest
from procurement.tools import (
    get_inventory,
    get_quotations,
    create_draft_requisition,
)

@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path, monkeypatch):
    """Overrides file paths to use temporary JSON files during testing."""
    test_inv = tmp_path / "inventory.json"
    test_quo = tmp_path / "quotations.json"
    test_req = tmp_path / "requisitions.json"

    # Sample test inventory data
    inv_data = [
        {
            "item_id": "ITM-001",
            "item_name": "Cement 50kg",
            "current_stock": 18,
            "reorder_point": 25,
            "reorder_qty": 50,
            "unit": "bags"
        }
    ]

    # Sample quotations: one valid, one expired
    future_date = (date.today() + timedelta(days=10)).strftime("%Y-%m-%d")
    past_date = (date.today() - timedelta(days=10)).strftime("%Y-%m-%d")
    quo_data = [
        {
            "quotation_id": "QT-1001",
            "item_id": "ITM-001",
            "supplier_name": "Supplier Alpha",
            "unit_price": 32000,
            "currency": "UGX",
            "valid_until": future_date
        },
        {
            "quotation_id": "QT-1002",
            "item_id": "ITM-001",
            "supplier_name": "Supplier Beta",
            "unit_price": 30000,
            "currency": "UGX",
            "valid_until": past_date
        }
    ]

    test_inv.write_text(json.dumps(inv_data))
    test_quo.write_text(json.dumps(quo_data))
    test_req.write_text(json.dumps([]))

    monkeypatch.setattr("procurement.tools.INVENTORY_FILE", str(test_inv))
    monkeypatch.setattr("procurement.tools.QUOTATIONS_FILE", str(test_quo))
    monkeypatch.setattr("procurement.tools.REQUISITIONS_FILE", str(test_req))


def test_get_inventory_success():
    result = get_inventory("ITM-001")
    assert result["item_id"] == "ITM-001"
    assert result["status"] == "REORDER_REQUIRED"
    assert result["current_stock"] == 18


def test_get_inventory_not_found():
    result = get_inventory("ITM-999")
    assert "error" in result
    assert result["error"] == "NotFound"


def test_get_quotations_filtering_and_sorting():
    result = get_quotations("ITM-001")
    quotes = result["quotations"]
    
    # Ensure matching quotations are returned
    assert len(quotes) == 2
    # Valid quotations should take priority in sorting
    assert quotes[0]["quotation_id"] == "QT-1001"
    assert quotes[0]["is_valid"] is True
    assert quotes[1]["is_valid"] is False


def test_create_draft_requisition_success():
    result = create_draft_requisition(
        item_id="ITM-001",
        quantity=50,
        justification="Stock below reorder point",
        requested_by="Procurement Officer"
    )
    assert "requisition_id" in result
    assert result["status"] == "Draft – Awaiting Approval"


def test_create_draft_requisition_validation_error():
    result = create_draft_requisition(
        item_id="ITM-001",
        quantity=0,  # Invalid quantity
        justification="",
        requested_by=""
    )
    assert "error" in result
    assert result["error"] == "ValidationError"