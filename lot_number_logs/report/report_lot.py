# -*- coding: utf-8 -*-

import base64
from datetime import datetime
import os

from odoo import api, models
from odoo.tools import html2plaintext


class LotAuditReport(models.AbstractModel):
    _name = "report.lot_number_logs.lot_audit"
    _description = "Lot Number Audit Report"

    _MODULE_RELEVANT_AUDIT_FIELDS = (
        "name",
        "product_id",
        "ref",
        "company_id",
        "product_qty",
        "product_uom_id",
        "note",
        "active",
    )

    @api.model
    def _format_module_relevant_field_value(self, lot, field):
        value = lot[field.name]

        if field.type == "boolean":
            return "Yes" if value else "No"

        if field.type == "selection":
            selection = field.selection
            if callable(selection):
                selection = selection(lot)
            elif isinstance(selection, str):
                selection = getattr(lot, selection)()
            return str(dict(selection or []).get(value, value)) if value else "N/A"

        if field.type == "many2one":
            return value.display_name if value else "N/A"

        if field.type in ("many2many", "one2many"):
            names = value.mapped("display_name")
            return ", ".join(names) if names else "N/A"

        if field.type == "html":
            return html2plaintext(value or "") or "N/A"

        if value in (None, ""):
            return "N/A"

        return str(value)

    @api.model
    def _get_module_relevant_field_rows(self, lot, row_size=3):
        excluded_fields = set(lot._lot_audit_excluded_fields())
        fields_with_values = []

        for field_name in self._MODULE_RELEVANT_AUDIT_FIELDS:
            if field_name in excluded_fields:
                continue
            field = lot._fields.get(field_name)
            if not field:
                continue
            fields_with_values.append(
                {
                    "label": field.string or field_name,
                    "value": self._format_module_relevant_field_value(lot, field),
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
    def _get_audit_logs(self, lot):
        return self.env["stock.production.lot.audit.log"].sudo().search(
            [
                ("model_id.model", "=", "stock.production.lot"),
                ("res_id", "=", lot.id),
            ],
            order="changed_date desc, id desc",
        )

    @api.model
    def _get_report_values(self, docids, data=None):
        lots = self.env["stock.production.lot"].browse(docids)

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

        lot_data = []
        for lot in lots:
            company = lot.company_id or self.env.company
            lot_data.append(
                {
                    "lot": lot,
                    "audit_logs": self._get_audit_logs(lot),
                    "module_field_rows": self._get_module_relevant_field_rows(lot),
                    "logo_base64": module_logo_base64,
                    "company_name": company.display_name or "N/A",
                }
            )

        return {
            "doc_ids": docids,
            "doc_model": "stock.production.lot",
            "docs": lot_data,
            "lot_list": lots,
            "printed_date": datetime.now().strftime("%m/%d/%Y"),
        }
