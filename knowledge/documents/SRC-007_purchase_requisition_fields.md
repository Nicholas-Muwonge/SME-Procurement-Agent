# Purchase Requisition Template Explanation

A complete Purchase Requisition (PR) draft must contain the following required fields:

## Required Fields

1. **Requisition Date**  
   The date the draft is created.

2. **Item ID and Item Name**  
   Clear identification of what is being requested.

3. **Quantity Requested**  
   The number of units required (must be a positive integer).

4. **Unit of Measure**  
   e.g., bags, pieces, kg, litres, metres.

5. **Estimated Unit Price** (if quotations are available)  
   Taken from the selected quotation(s).

6. **Estimated Total Cost**  
   Quantity × Unit Price (calculated deterministically).

7. **Justification / Reason for Request**  
   Short explanation why the item is needed (e.g., “Stock below reorder point”).

8. **Suggested Supplier Options** (optional but recommended)  
   Top 2–3 valid quotations for reference only.

9. **Status**  
   Must start as “Draft – Awaiting Approval”.

10. **Requested By**  
    Name or ID of the person initiating the requisition.

## Important Rules
- The system may generate the draft, but it cannot approve it.
- All numerical calculations (totals) must be performed by deterministic code, not by the language model.
- The requisition remains in Draft status until a human explicitly approves, rejects, or requests changes.
