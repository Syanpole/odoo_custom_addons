# -*- coding: utf-8 -*-
{
    "name": "Product Audit Logs",
    "summary": "Generate Product Variant audit PDF from immutable audit logs",
    "description": """
Generate a PDF audit trail for Product Variants using immutable
audit logs captured on create/write operations.
    """,
    "version": "1.0",
    "category": "Inventory",
    "author": "Sean Paul C. Feliciano",
    "depends": ["base", "mail", "product"],
    "data": [
        "security/ir.model.access.csv",
        "views/product_audit_views.xml",
        "report/report_product.xml",
    ],
    "installable": True,
    "application": False,
}
