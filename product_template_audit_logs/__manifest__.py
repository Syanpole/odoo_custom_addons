# -*- coding: utf-8 -*-
{
    "name": "Product Template Audit Logs",
    "summary": "Generate Product Template audit PDF from immutable audit logs",
    "description": """
Generate a PDF audit trail for Product Templates using immutable
audit logs captured on create/write operations.
    """,
    "version": "1.0",
    "category": "Inventory",
    "author": "Sean Paul C. Feliciano",
    "depends": ["base", "mail", "product"],
    "data": [
        "security/ir.model.access.csv",
        "views/product_template_audit_views.xml",
        "report/report_product_template.xml",
    ],
    "installable": True,
    "application": False,
}
