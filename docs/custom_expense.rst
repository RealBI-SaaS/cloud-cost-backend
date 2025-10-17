
Custom Expense Overview
==============================

This section documents the backend data models and logic for handling user-defined
recurring costs.

Models
------

1. **CustomExpenseVendor**
   Represents known subscription service providers (e.g. Slack, ChatGPT, Netflix). They will be created once by admins and reused as option for dropdown menus on ``CustomExpense`` registering.

   **Fields**
     - ``name`` *(str)* – Vendor name (unique).
     - ``website`` *(URLField)* – Official website link.
     - ``logo`` *(ImageField, required)* – Logo image for display in dropdowns and grids.
     - ``description`` *(TextField, optional)* – Short info about the service.

2. **CustomExpense**
   Represents an individual recurring cost entry for an org. Can be linked to a known
   vendor or have just a custom name (ie. ``logo`` and ``description`` will not be available).

   **Fields**
     - ``vendor`` *(ForeignKey → CustomExpenseVendor, optional)* – Linked vendor.
     - ``custom_name`` *(CharField, optional)* – Used when no vendor is selected.
     - ``amount`` *(DecimalField)* – Cost amount.
     - ``currency`` *(CharField)* – Currency code (e.g. USD, EUR).
     - ``frequency`` *(CharField)* – Recurrence frequency (daily, weekly, monthly, yearly).

   **Validation Rules**
     - Either ``vendor`` as ``vendor_id`` **or** ``custom_name`` must be provided. If both are passed the ``vendor`` will be used and ``custom_name`` will be ``null``.
     - Both cannot be empty.
     - ``amount`` and ``frequency`` cannot be blank too.

Frontend Usage
--------------
- Use the ``/data/custom-expense-vendors/`` endpoint to fetch available vendors with logos and websites.
- Use the ``/data/custom-expense/`` endpoint to list, create, or update user expenses.
- In UI grids or dropdowns, display vendor logos and names from the vendor API.

