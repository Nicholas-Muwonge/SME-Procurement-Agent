# Handling Missing Inventory Data

## Policy
If any of the following critical fields are missing or null for an item:
- Current Stock
- Reorder Point

then the system must:
1. Skip that item from automatic reorder recommendations.
2. Clearly report: “Insufficient data for Item [ID] – cannot evaluate reorder status.”
3. Never invent or assume a stock level or reorder point.

The procurement officer must update the missing data before the item can be processed.
