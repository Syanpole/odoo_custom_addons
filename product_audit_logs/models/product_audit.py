# -*- coding: utf-8 -*-

import json
from collections import defaultdict

from odoo import api, fields, models
from odoo.tools import html_escape


class ProductProductAudit(models.Model):
    _inherit = "product.product"

    @api.model
    def _product_audit_display_field_name(self, field_name):
        field = self._fields.get(field_name)
        return field.string if field and field.string else field_name

    @api.model
    def _product_audit_message_item(self, field_name, old_value, new_value):
        return (
            "<li>%s <b>&rarr;</b> <span style='color:#159588;'>%s</span> <i>(%s)</i></li>"
            % (
                html_escape(old_value or "None"),
                html_escape(new_value or "None"),
                html_escape(field_name or "Field"),
            )
        )

    def _product_audit_post_to_chatter(self, log_values):
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
                self._product_audit_message_item(
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
    def _product_audit_excluded_fields(self):
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
    def _product_audit_raw_value(self, record, field):
        value = record[field.name]
        if field.type == "many2one":
            return value.id or False
        if field.type in ("many2many", "one2many"):
            return tuple(value.ids)
        return value

    @api.model
    def _product_audit_has_changed(self, field, old_value, new_value):
        if field.type in ("many2many", "one2many"):
            return tuple(old_value or ()) != tuple(new_value or ())
        return old_value != new_value

    @api.model
    def _product_audit_format_value(self, field, value):
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

    def _product_audit_snapshot(self, tracked_fields):
        snapshot = {}
        for record in self:
            snapshot[record.id] = {}
            for field_name in tracked_fields:
                field = record._fields.get(field_name)
                if field:
                    snapshot[record.id][field_name] = self._product_audit_raw_value(record, field)
        return snapshot

    def _product_audit_prepare_values(self, tracked_fields, old_snapshot):
        values = []
        model = self.env["ir.model"]._get("product.product")
        if not model:
            return values

        for record in self:
            old_values = old_snapshot.get(record.id, {})
            for field_name in tracked_fields:
                field = record._fields.get(field_name)
                if not field:
                    continue

                old_raw = old_values.get(field_name)
                new_raw = self._product_audit_raw_value(record, field)
                if not self._product_audit_has_changed(field, old_raw, new_raw):
                    continue

                values.append(
                    {
                        "model_id": model.id,
                        "res_id": record.id,
                        "field_name": self._product_audit_display_field_name(field_name),
                        "old_value": self._product_audit_format_value(field, old_raw),
                        "new_value": self._product_audit_format_value(field, new_raw),
                        "changed_by": self.env.user.id,
                        "changed_date": fields.Datetime.now(),
                    }
                )
        return values

    @api.model_create_multi
    def create(self, vals_list):
        records = super(ProductProductAudit, self).create(vals_list)

        if self.env.context.get("skip_product_audit_log"):
            return records

        excluded = records._product_audit_excluded_fields()
        model = self.env["ir.model"]._get("product.product")
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

                new_raw = self._product_audit_raw_value(record, field)
                log_values.append(
                    {
                        "model_id": model.id,
                        "res_id": record.id,
                        "field_name": self._product_audit_display_field_name(field_name),
                        "old_value": "",
                        "new_value": self._product_audit_format_value(field, new_raw),
                        "changed_by": self.env.user.id,
                        "changed_date": fields.Datetime.now(),
                    }
                )

        if log_values:
            self.env["product.audit.log"].sudo().with_context(
                product_audit_log_internal_create=True
            ).create(log_values)
            records._product_audit_post_to_chatter(log_values)

        return records

    def write(self, vals):
        if self.env.context.get("skip_product_audit_log"):
            return super(ProductProductAudit, self).write(vals)

        excluded = self._product_audit_excluded_fields()
        tracked_fields = [
            field_name
            for field_name in vals.keys()
            if field_name in self._fields and field_name not in excluded
        ]

        old_snapshot = {}
        if tracked_fields:
            old_snapshot = self._product_audit_snapshot(tracked_fields)

        result = super(ProductProductAudit, self).write(vals)

        if tracked_fields and old_snapshot:
            log_values = self._product_audit_prepare_values(tracked_fields, old_snapshot)
            if log_values:
                self.env["product.audit.log"].sudo().with_context(
                    product_audit_log_internal_create=True
                ).create(log_values)
                self._product_audit_post_to_chatter(log_values)

        return result
