# -*- coding: utf-8 -*-

from datetime import datetime
import base64
import os

from odoo import api, models


class BomAuditReport(models.AbstractModel):
    _name = "report.bom_audit_logs.bom_audit_report"
    _description = "BoM Audit Report"

    @api.model
    def _get_audit_logs(self, bom):
        return self.env["mrp.bom.audit.log"].sudo().search(
            [
                ("model_id.model", "=", "mrp.bom"),
                ("res_id", "=", bom.id),
            ],
            order="changed_date desc, id desc",
        )

    @api.model
    def _get_report_values(self, docids, data=None):
        boms = self.env["mrp.bom"].browse(docids)

        bom_data = []
        for bom in boms:
            bom_data.append(
                {
                    "bom": bom,
                    "audit_logs": self._get_audit_logs(bom),
                }
            )

        logo_path = os.path.join(
            os.path.dirname(__file__),
            "..", "static", "src", "img", "logo.png"
        )
        logo_base64 = ""
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as image_file:
                logo_base64 = base64.b64encode(image_file.read()).decode("utf-8")

        return {
            "doc_ids": docids,
            "doc_model": "mrp.bom",
            "docs": bom_data,
            "bom_list": boms,
            "printed_date": datetime.now().strftime("%m/%d/%Y"),
            "logo_base64": logo_base64,
        }
