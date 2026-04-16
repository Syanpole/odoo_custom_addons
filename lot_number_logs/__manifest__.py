# -*- coding: utf-8 -*-
{
    "name": "Lot Number Logs",
    "summary": "Generate Lot/Serial Number audit PDF from immutable audit logs",
    "description": """
Generate a PDF audit trail for Lot/Serial Numbers (stock.production.lot)
using immutable audit logs captured on create/write operations.
    """,
    "version": "1.0",
    "category": "Inventory",
    "author": "Sean Paul C. Feliciano",
    "depends": ["base", "mail", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/lot_audit_views.xml",
        "report/report_lot.xml",
    ],
    "installable": True,
    "application": False,
}
