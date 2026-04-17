# -*- coding: utf-8 -*-

import base64
from datetime import datetime
import os

from odoo import api, models


class WorkorderAuditReport(models.AbstractModel):
    _name = "report.workorder_audit_logs.workorder_audit_report"
    _description = "Work Order Audit Report"

    @api.model
    def _get_audit_logs(self, workorder):
        return self.env["mrp.workorder.audit.log"].sudo().search(
            [
                ("model_id.model", "=", "mrp.workorder"),
                ("res_id", "=", workorder.id),
            ],
            order="changed_date desc, id desc",
        )

    @api.model
    def _get_report_values(self, docids, data=None):
        workorders = self.env["mrp.workorder"].browse(docids)

        base_dir = os.path.dirname(__file__)
        logo_candidates = [
            os.path.join(base_dir, "..", "static", "src", "img", "logo.png"),
            os.path.join(base_dir, "..", "..", "routing_logs", "static", "src", "img", "logo.png"),
            os.path.join(base_dir, "..", "..", "mrp_extension", "static", "src", "img", "dpt_logo.png"),
            os.path.join(base_dir, "..", "..", "mrp_extension", "static", "src", "img", "tpc_icon.png"),
        ]

        logo_path = ""
        for candidate in logo_candidates:
            if os.path.exists(candidate):
                logo_path = candidate
                break

        logo_base64 = ""
        if logo_path and os.path.exists(logo_path):
            with open(logo_path, "rb") as image_file:
                logo_base64 = base64.b64encode(image_file.read()).decode("utf-8")

        docs = []
        for workorder in workorders:
            docs.append(
                {
                    "workorder": workorder,
                    "audit_logs": self._get_audit_logs(workorder),
                    "logo_base64": logo_base64,
                }
            )

        return {
            "doc_ids": docids,
            "doc_model": "mrp.workorder",
            "docs": docs,
            "workorder_list": workorders,
            "printed_date": datetime.now().strftime("%m/%d/%Y"),
        }
