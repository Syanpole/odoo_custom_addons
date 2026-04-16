# -*- coding: utf-8 -*-

import json
from collections import defaultdict

from odoo import api, fields, models
from odoo.tools import html_escape


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    def action_print_bom_audit_pdf(self):
        self.ensure_one()
        self.flush()
        self.invalidate_cache()
        cache_buster = fields.Datetime.now().strftime("%Y%m%d%H%M%S%f")
        return self.env.ref(
            "bom_audit_logs.report_bom_audit_pdf"
        ).with_context(
            report_cache_buster=cache_buster
        ).report_action(
            self,
            data={"report_cache_buster": cache_buster},
        )

    @api.model
    def _bom_audit_display_field_name(self, field_name):
        field = self._fields.get(field_name)
        return field.string if field and field.string else field_name

    @api.model
    def _bom_audit_message_item(self, field_name, old_value, new_value):
        return (
            "<li>%s <b>&rarr;</b> <span style='color:#159588;'>%s</span> <i>(%s)</i></li>"
            % (
                html_escape(old_value or "None"),
                html_escape(new_value or "None"),
                html_escape(field_name or "Field"),
            )
        )

    def _bom_audit_post_to_chatter(self, log_values):
        if not log_values:
            return

        grouped_logs = defaultdict(list)
        for values in log_values:
            res_id = values.get("res_id")
            if res_id:
                grouped_logs[res_id].append(values)

        note_subtype = self.env.ref("mail.mt_note", raise_if_not_found=False)
        subtype_id = note_subtype.id if note_subtype else False

        for res_id, values_list in grouped_logs.items():
            record = self.browse(res_id)
            if not record.exists():
                continue

            body_items = [
                self._bom_audit_message_item(
                    values.get("field_name"),
                    values.get("old_value"),
                    values.get("new_value"),
                )
                for values in values_list
            ]
            body = "<ul>%s</ul>" % "".join(body_items)

            try:
                record.sudo().message_post(
                    body=body,
                    subtype_id=subtype_id,
                    message_type="comment",
                )
            except Exception:
                pass

    @api.model
    def _bom_audit_excluded_fields(self):
        return {
            "__last_update",
            "create_date",
            "create_uid",
            "write_date",
            "write_uid",
            "display_name",
            "message_ids",
            "message_follower_ids",
            "message_partner_ids",
            "message_attachment_count",
            "message_is_follower",
            "message_needaction",
            "message_needaction_counter",
            "message_unread",
            "message_unread_counter",
            "activity_ids",
            "activity_state",
            "activity_exception_icon",
            "activity_type_icon",
        }

    @api.model
    def _bom_audit_raw_value(self, record, field):
        value = record[field.name]
        if field.type == "many2one":
            return value.id or False
        if field.type in ("many2many", "one2many"):
            return tuple(value.ids)
        return value

    @api.model
    def _bom_audit_has_changed(self, field, old_value, new_value):
        if field.type in ("many2many", "one2many"):
            return tuple(old_value or ()) != tuple(new_value or ())
        return old_value != new_value

    @api.model
    def _bom_audit_format_value(self, field, value):
        if value in (False, None, ""):
            return ""

        if field.type == "selection":
            selection = field.selection
            if callable(selection):
                selection = selection(self)
            elif isinstance(selection, str):
                selection = getattr(self, selection)()
            return str(dict(selection or []).get(value, value))

        if field.type == "many2one":
            record = self.env[field.comodel_name].browse(value)
            if record.exists():
                return record.display_name
            return str(value)

        if field.type in ("many2many", "one2many"):
            values = []
            records = self.env[field.comodel_name].browse(list(value or ())).exists()
            name_map = dict(records.name_get()) if records else {}
            for rec_id in list(value or ()):
                values.append(name_map.get(rec_id, str(rec_id)))
            return ", ".join(values)

        if isinstance(value, (list, tuple, dict)):
            return json.dumps(value, ensure_ascii=True, sort_keys=True)

        return str(value)

    def _bom_audit_snapshot(self, tracked_fields):
        snapshot = {}
        for record in self:
            snapshot[record.id] = {}
            for field_name in tracked_fields:
                field = record._fields.get(field_name)
                if field:
                    snapshot[record.id][field_name] = self._bom_audit_raw_value(record, field)
        return snapshot

    def _bom_audit_prepare_values(self, tracked_fields, old_snapshot):
        values = []
        model = self.env["ir.model"]._get("mrp.bom")
        if not model:
            return values

        for record in self:
            old_values = old_snapshot.get(record.id, {})
            for field_name in tracked_fields:
                field = record._fields.get(field_name)
                if not field:
                    continue

                old_raw = old_values.get(field_name)
                new_raw = self._bom_audit_raw_value(record, field)
                if not self._bom_audit_has_changed(field, old_raw, new_raw):
                    continue

                values.append(
                    {
                        "model_id": model.id,
                        "res_id": record.id,
                        "field_name": self._bom_audit_display_field_name(field_name),
                        "old_value": self._bom_audit_format_value(field, old_raw),
                        "new_value": self._bom_audit_format_value(field, new_raw),
                        "changed_by": self.env.user.id,
                        "changed_date": fields.Datetime.now(),
                    }
                )
        return values

    def _bom_audit_create_logs(self, rows):
        if not rows:
            return

        model = self.env["ir.model"]._get("mrp.bom")
        if not model:
            return

        log_values = []
        for row in rows:
            bom_id = row.get("res_id")
            if not bom_id:
                continue
            log_values.append(
                {
                    "model_id": model.id,
                    "res_id": bom_id,
                    "field_name": row.get("field_name") or "BoM Change",
                    "old_value": row.get("old_value") or "",
                    "new_value": row.get("new_value") or "",
                    "changed_by": self.env.user.id,
                    "changed_date": fields.Datetime.now(),
                }
            )

        if log_values:
            self.env["mrp.bom.audit.log"].sudo().with_context(
                bom_audit_log_internal_create=True
            ).create(log_values)
            self.browse(list({v["res_id"] for v in log_values}))._bom_audit_post_to_chatter(log_values)

    @api.model_create_multi
    def create(self, vals_list):
        records = super(MrpBom, self).create(vals_list)

        if self.env.context.get("skip_bom_audit_log"):
            return records

        excluded = records._bom_audit_excluded_fields()
        model = self.env["ir.model"]._get("mrp.bom")
        if not model:
            return records

        log_values = []
        for record, vals in zip(records, vals_list):
            tracked_fields = [
                field_name
                for field_name in vals.keys()
                if field_name in record._fields and field_name not in excluded
            ]
            for field_name in tracked_fields:
                field = record._fields.get(field_name)
                if not field:
                    continue

                new_raw = self._bom_audit_raw_value(record, field)
                log_values.append(
                    {
                        "model_id": model.id,
                        "res_id": record.id,
                        "field_name": self._bom_audit_display_field_name(field_name),
                        "old_value": "",
                        "new_value": self._bom_audit_format_value(field, new_raw),
                        "changed_by": self.env.user.id,
                        "changed_date": fields.Datetime.now(),
                    }
                )

        if log_values:
            self.env["mrp.bom.audit.log"].sudo().with_context(
                bom_audit_log_internal_create=True
            ).create(log_values)
            records._bom_audit_post_to_chatter(log_values)

        return records

    def write(self, vals):
        if self.env.context.get("skip_bom_audit_log"):
            return super(MrpBom, self).write(vals)

        excluded = self._bom_audit_excluded_fields()
        tracked_fields = [
            field_name
            for field_name in vals.keys()
            if field_name in self._fields and field_name not in excluded
        ]

        old_snapshot = {}
        if tracked_fields:
            old_snapshot = self._bom_audit_snapshot(tracked_fields)

        result = super(MrpBom, self).write(vals)

        if tracked_fields and old_snapshot:
            log_values = self._bom_audit_prepare_values(tracked_fields, old_snapshot)
            if log_values:
                self.env["mrp.bom.audit.log"].sudo().with_context(
                    bom_audit_log_internal_create=True
                ).create(log_values)
                self._bom_audit_post_to_chatter(log_values)

        return result


class MrpBomLineAudit(models.Model):
    _inherit = "mrp.bom.line"

    @api.model
    def _line_summary(self, line):
        product = line.product_id.display_name if line.product_id else "N/A"
        qty = line.product_qty if line.product_qty is not None else 0.0
        uom = line.product_uom_id.display_name if line.product_uom_id else "N/A"
        return "%s | Qty: %s | UoM: %s" % (product, qty, uom)

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(MrpBomLineAudit, self).create(vals_list)

        rows = []
        for line in lines:
            if not line.bom_id:
                continue
            rows.append(
                {
                    "res_id": line.bom_id.id,
                    "field_name": "Component Line",
                    "old_value": "",
                    "new_value": self._line_summary(line),
                }
            )

        if rows:
            self.env["mrp.bom"]._bom_audit_create_logs(rows)

        return lines

    def write(self, vals):
        old_values = {line.id: self._line_summary(line) for line in self}
        result = super(MrpBomLineAudit, self).write(vals)

        rows = []
        for line in self:
            if not line.bom_id:
                continue
            old_value = old_values.get(line.id, "")
            new_value = self._line_summary(line)
            if old_value == new_value:
                continue
            rows.append(
                {
                    "res_id": line.bom_id.id,
                    "field_name": "Component Line",
                    "old_value": old_value,
                    "new_value": new_value,
                }
            )

        if rows:
            self.env["mrp.bom"]._bom_audit_create_logs(rows)

        return result

    def unlink(self):
        rows = []
        for line in self:
            if not line.bom_id:
                continue
            rows.append(
                {
                    "res_id": line.bom_id.id,
                    "field_name": "Component Line",
                    "old_value": self._line_summary(line),
                    "new_value": "",
                }
            )

        result = super(MrpBomLineAudit, self).unlink()

        if rows:
            self.env["mrp.bom"]._bom_audit_create_logs(rows)

        return result


class MrpSubproductAudit(models.Model):
    _inherit = "mrp.bom.byproduct"

    @api.model
    def _byproduct_summary(self, byproduct):
        product = byproduct.product_id.display_name if byproduct.product_id else "N/A"
        qty = byproduct.product_qty if byproduct.product_qty is not None else 0.0
        uom = byproduct.product_uom_id.display_name if byproduct.product_uom_id else "N/A"
        return "%s | Qty: %s | UoM: %s" % (product, qty, uom)

    @api.model_create_multi
    def create(self, vals_list):
        records = super(MrpSubproductAudit, self).create(vals_list)

        rows = []
        for rec in records:
            if not rec.bom_id:
                continue
            rows.append(
                {
                    "res_id": rec.bom_id.id,
                    "field_name": "By-product Line",
                    "old_value": "",
                    "new_value": self._byproduct_summary(rec),
                }
            )

        if rows:
            self.env["mrp.bom"]._bom_audit_create_logs(rows)

        return records

    def write(self, vals):
        old_values = {rec.id: self._byproduct_summary(rec) for rec in self}
        result = super(MrpSubproductAudit, self).write(vals)

        rows = []
        for rec in self:
            if not rec.bom_id:
                continue
            old_value = old_values.get(rec.id, "")
            new_value = self._byproduct_summary(rec)
            if old_value == new_value:
                continue
            rows.append(
                {
                    "res_id": rec.bom_id.id,
                    "field_name": "By-product Line",
                    "old_value": old_value,
                    "new_value": new_value,
                }
            )

        if rows:
            self.env["mrp.bom"]._bom_audit_create_logs(rows)

        return result

    def unlink(self):
        rows = []
        for rec in self:
            if not rec.bom_id:
                continue
            rows.append(
                {
                    "res_id": rec.bom_id.id,
                    "field_name": "By-product Line",
                    "old_value": self._byproduct_summary(rec),
                    "new_value": "",
                }
            )

        result = super(MrpSubproductAudit, self).unlink()

        if rows:
            self.env["mrp.bom"]._bom_audit_create_logs(rows)

        return result
