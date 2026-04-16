# -*- coding: utf-8 -*-
{
    "name": "BoM Audit Logs",
    "summary": "Generate BoM audit PDF from immutable audit logs",
    "description": """
Generate a PDF audit trail for Bill of Materials using immutable
audit logs captured on create/write operations.
    """,
    "version": "1.0",
    "category": "Manufacturing",
    "author": "Sean Paul C. Feiciano",
    "depends": ["base", "mail", "mrp", "mrp_extension"],
    "data": [
        "security/ir.model.access.csv",
        "views/bom_audit_views.xml",
        "report/report_bom.xml",
    ],
    "installable": True,
    "application": False,
}
