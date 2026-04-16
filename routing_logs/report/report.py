# -*- coding: utf-8 -*-

from odoo import models, api
from datetime import datetime
import base64
import os


class RoutingAuditReport(models.AbstractModel):
    _name = "report.routing_logs.routing_report"
    _description = "Routing Audit Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        """Generate report data for routing audit"""
        routings = self.env['mrp.routing'].browse(docids)

        routing_data = []
        for routing in routings:
            # Get audit logs for routing AND its operations (like the timeline does)
            routing_model = self.env["ir.model"]._get("mrp.routing")
            operation_model = self.env["ir.model"]._get("mrp.routing.workcenter")

            # Build domain: routing logs OR operation logs for this routing's operations
            domain = [
                "|",
                "&",
                ("model_id", "=", routing_model.id if routing_model else 0),
                ("res_id", "=", routing.id),
                "&",
                ("model_id", "=", operation_model.id if operation_model else 0),
                ("res_id", "in", routing.operation_ids.ids or [0]),
            ]

            audit_logs = self.env['routing.log'].search(
                domain,
                order='changed_date desc'
            )

            routing_data.append({
                'routing': routing,
                'audit_logs': audit_logs,
            })

        # Load logo as base64
        logo_path = os.path.join(
            os.path.dirname(__file__),
            '..', 'static', 'src', 'img', 'logo.png'
        )
        logo_base64 = ''
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as img_file:
                logo_base64 = base64.b64encode(img_file.read()).decode('utf-8')

        # Create SVG watermark as data URI
        watermark_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1600" viewBox="0 0 1200 1600">
            <g transform="rotate(45 600 800)">
                <text x="600" y="800" 
                      text-anchor="middle" 
                      dominant-baseline="middle"
                      font-family="Arial, sans-serif" 
                      font-size="120" 
                      font-weight="bold" 
                      fill="#333333" 
                      opacity="0.5">
                    TEAM PACIFIC CORPORATION
                </text>
            </g>
        </svg>'''
        watermark_base64 = base64.b64encode(watermark_svg.encode('utf-8')).decode('utf-8')
        watermark_uri = f'data:image/svg+xml;base64,{watermark_base64}'

        return {
            'doc_ids': docids,
            'doc_model': 'mrp.routing',
            'docs': routing_data,
            'routing_list': routings,
            'printed_date': datetime.now().strftime('%m/%d/%Y'),
            'logo_base64': logo_base64,
            'watermark_uri': watermark_uri,
        }







