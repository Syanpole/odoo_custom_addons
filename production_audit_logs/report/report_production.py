# -*- coding: utf-8 -*-

import base64
from datetime import datetime
import os

from odoo import api, models


class ProductionAuditReport(models.AbstractModel):
    _name = "report.production_audit_logs.production_audit_report"
    _description = "Production Audit Report"

    @api.model
    def _get_audit_logs(self, production):
        return self.env["mrp.production.audit.log"].sudo().search(
            [
                ("model_id.model", "=", "mrp.production"),
                ("res_id", "=", production.id),
            ],
            order="changed_date desc, id desc",
        )

    @api.model
    def _get_report_values(self, docids, data=None):
        productions = self.env["mrp.production"].browse(docids)

        base_dir = os.path.dirname(__file__)
        logo_candidates = [
            os.path.join(base_dir, "..", "static", "src", "img", "logo.png"),
            os.path.join(base_dir, "..", "..", "workorder_audit_logs", "static", "src", "img", "logo.png"),
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
        for production in productions:
            docs.append(
                {
                    "production": production,
                    "audit_logs": self._get_audit_logs(production),
                    "logo_base64": logo_base64,
                }
            )

        return {
            "doc_ids": docids,
            "doc_model": "mrp.production",
            "docs": docs,
            "production_list": productions,
            "printed_date": datetime.now().strftime("%m/%d/%Y"),
        }
