# -*- coding: utf-8 -*-
{
    "name": "Production Audit Logs",
    "summary": "Generate Production Order audit PDF from immutable audit logs",
    "description": """
Generate a PDF audit trail for Manufacturing Orders using immutable
field-level logs captured on create/write operations.
    """,
    "version": "1.0",
    "category": "Manufacturing",
    "author": "Sean Paul C. Feliciano",
    "depends": ["base", "mail", "mrp"],
    "data": [
        "security/ir.model.access.csv",
        "views/production_audit_views.xml",
        "report/report_production.xml",
    ],
    "installable": True,
    "application": False,
}
