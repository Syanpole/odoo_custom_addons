# -*- coding: utf-8 -*-

import base64
from datetime import datetime
import os

from odoo import api, models


class ProductTemplateAuditReport(models.AbstractModel):
    _name = "report.product_template_audit_logs.pt_audit"
    _description = "Product Template Audit Report"

    _MODULE_RELEVANT_AUDIT_FIELDS = (
        "perishable",
        "non_perishable",
        "sale_ok",
        "purchase_ok",
        "can_be_expensed",
        "type",
        "categ_id",
        "default_code",
        "barcode",
        "package_type",
        "allow_negative_stock",
        "list_price",
        "taxes_id",
        "standard_price",
        "uom_id",
        "uom_po_id",
        "sku",
        "active",
    )

    @api.model
    def _format_module_relevant_field_value(self, product_template, field):
        value = product_template[field.name]

        if field.type == "boolean":
            return "Yes" if value else "No"

        if field.type == "selection":
            selection = field.selection
            if callable(selection):
                selection = selection(product_template)
            elif isinstance(selection, str):
                selection = getattr(product_template, selection)()
            return str(dict(selection or []).get(value, value)) if value else "N/A"

        if field.type == "many2one":
            return value.display_name if value else "N/A"

        if field.type in ("many2many", "one2many"):
            names = value.mapped("display_name")
            return ", ".join(names) if names else "N/A"

        if value in (None, ""):
            return "N/A"

        return str(value)

    @api.model
    def _get_module_relevant_field_rows(self, product_template, row_size=3):
        excluded_fields = set(product_template._template_audit_excluded_fields())
        fields_with_values = []

        for field_name in self._MODULE_RELEVANT_AUDIT_FIELDS:
            if field_name in excluded_fields:
                continue
            field = product_template._fields.get(field_name)
            if not field:
                continue
            fields_with_values.append(
                {
                    "label": field.string or field_name,
                    "value": self._format_module_relevant_field_value(product_template, field),
                }
            )

        rows = []
        for index in range(0, len(fields_with_values), row_size):
            row = fields_with_values[index:index + row_size]
            if len(row) < row_size:
                row.extend([{"label": "", "value": ""} for _ in range(row_size - len(row))])
            rows.append(row)

        return rows

    @api.model
    def _get_audit_logs(self, product_template):
        return self.env["product.template.audit.log"].sudo().search(
            [
                ("model_id.model", "=", "product.template"),
                ("res_id", "=", product_template.id),
            ],
            order="changed_date desc, id desc",
        )

    @api.model
    def _get_report_values(self, docids, data=None):
        templates = self.env["product.template"].browse(docids)

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

        template_data = []
        for template in templates:
            company = template.company_id or self.env.company
            template_data.append(
                {
                    "product_template": template,
                    "audit_logs": self._get_audit_logs(template),
                    "module_field_rows": self._get_module_relevant_field_rows(template),
                    "logo_base64": module_logo_base64,
                    "company_name": company.display_name or "N/A",
                }
            )

        return {
            "doc_ids": docids,
            "doc_model": "product.template",
            "docs": template_data,
            "template_list": templates,
            "printed_date": datetime.now().strftime("%m/%d/%Y"),
        }
