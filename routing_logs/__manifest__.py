# -*- coding: utf-8 -*-
{
    "name": "Routing Logs",
    "summary": "Immutable field-level audit logs for routings",
    "description": """
Reusable audit logging for Odoo models with immutable log entries.
Includes production-ready integration for mrp.routing.
    """,
    "version": "1.0",
    "category": "Technical",
    "author": "Sean Paul C. Feiciano",
    "depends": ["base", "mail", "mrp", "mrp_extension"],
    "data": [
        "security/ir.model.access.csv",
        "views/routing_log_views.xml",
        "report/report_routing.xml",
    ],
    "installable": True,
    "application": False,
}
