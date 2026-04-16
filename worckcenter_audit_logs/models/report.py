# -*- coding: utf-8 -*-

from odoo import models, api
from datetime import datetime
import base64
import os


class WorkcenterAuditReport(models.AbstractModel):
    _name = "report.worckcenter_audit_logs.wc_report"
    _description = "Work Center Audit Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        """Generate report data for work center audit"""
        workcenters = self.env['mrp.workcenter'].browse(docids)

        workcenter_data = []
        for wc in workcenters:
            # Get audit logs for this workcenter
            audit_logs = self.env['workcenter.audit.log'].search([
                ('res_id', '=', wc.id),
                ('model_id.model', '=', 'mrp.workcenter')
            ], order='changed_date desc')

            workcenter_data.append({
                'workcenter': wc,
                'audit_logs': audit_logs,
            })

        # Load module logo as base64 for the report header.
        logo_path = os.path.join(
            os.path.dirname(__file__),
            '..', 'static', 'src', 'img', 'logo.png'
        )
        logo_base64 = ''
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as img_file:
                logo_base64 = base64.b64encode(img_file.read()).decode('utf-8')

        return {
            'doc_ids': docids,
            'doc_model': 'mrp.workcenter',
            'docs': workcenter_data,
            'workcenter_list': workcenters,
            'printed_date': datetime.now().strftime('%m/%d/%Y'),
            'logo_base64': logo_base64,
        }
