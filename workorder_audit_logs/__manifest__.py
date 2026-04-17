# -*- coding: utf-8 -*-
{
    "name": "Work Order Audit Logs",
    "summary": "Generate Work Order audit PDF from immutable audit logs",
    "description": """
Generate a PDF audit trail for Work Orders using immutable
field-level logs captured on create/write operations.
    """,
    "version": "1.0",
    "category": "Manufacturing",
    "author": "Sean Paul C. Feiciano",
    "depends": ["base", "mail", "mrp", "mrp_extension"],
    "data": [
        "security/ir.model.access.csv",
        "views/workorder_audit_views.xml",
        "report/report_workorder.xml",
    ],
    "installable": True,
    "application": False,
}
