# -*- coding: utf-8 -*-

import base64
from datetime import datetime
import os

from odoo import api, models


class ProductAuditReport(models.AbstractModel):
    _name = "report.product_audit_logs.product_audit_report"
    _description = "Product Audit Report"

    @api.model
    def _get_audit_logs(self, product):
        return self.env["product.audit.log"].sudo().search(
            [
                ("model_id.model", "=", "product.product"),
                ("res_id", "=", product.id),
            ],
            order="changed_date desc, id desc",
        )

    @api.model
    def _get_report_values(self, docids, data=None):
        products = self.env["product.product"].browse(docids)
        module_logo_base64 = ""
        logo_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "static",
            "src",
            "img",
            "logo.png",
        )
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as image_file:
                module_logo_base64 = base64.b64encode(image_file.read()).decode("utf-8")

        product_data = []
        for product in products:
            company = product.company_id or self.env.company
            product_data.append(
                {
                    "product": product,
                    "audit_logs": self._get_audit_logs(product),
                    "logo_base64": module_logo_base64,
                    "company_name": company.display_name or "N/A",
                }
            )

        return {
            "doc_ids": docids,
            "doc_model": "product.product",
            "docs": product_data,
            "product_list": products,
            "printed_date": datetime.now().strftime("%m/%d/%Y"),
        }
