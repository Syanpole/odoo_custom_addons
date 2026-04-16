# -*- coding: utf-8 -*-

import json

from odoo import api, fields, models
from odoo.tools import html_escape


class WorkcenterAuditMixin(models.AbstractModel):
    _name = "workcenter.audit.mixin"
    _description = "Work Center Audit Logging Mixin"

    @api.model
    def _audit_excluded_fields(self):
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
    def _audit_raw_value(self, record, field):
        value = record[field.name]
        if field.type == "many2one":
            return value.id or False
        if field.type in ("many2many", "one2many"):
            return tuple(value.ids)
        return value

    @api.model
    def _audit_has_changed(self, field, old_value, new_value):
        if field.type in ("many2many", "one2many"):
            return tuple(old_value or ()) != tuple(new_value or ())
        return old_value != new_value

    @api.model
    def _audit_format_value(self, field, value):
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

    def _audit_snapshot(self, tracked_fields):
        snapshot = {}
        for record in self:
            snapshot[record.id] = {}
            for field_name in tracked_fields:
                field = record._fields.get(field_name)
                if field:
                    snapshot[record.id][field_name] = self._audit_raw_value(record, field)
        return snapshot

    def _audit_prepare_values(self, tracked_fields, old_snapshot):
        values = []
        model = self.env["ir.model"]._get(self._name)
        if not model:
            return values

        for record in self:
            old_values = old_snapshot.get(record.id, {})
            for field_name in tracked_fields:
                field = record._fields.get(field_name)
                if not field:
                    continue

                old_raw = old_values.get(field_name)
                new_raw = self._audit_raw_value(record, field)
                if not self._audit_has_changed(field, old_raw, new_raw):
                    continue

                values.append(
                    {
                        "model_id": model.id,
                        "res_id": record.id,
                        "field_name": field_name,
                        "old_value": self._audit_format_value(field, old_raw),
                        "new_value": self._audit_format_value(field, new_raw),
                        "changed_by": self.env.user.id,
                        "changed_date": fields.Datetime.now(),
                    }
                )
        return values

    def write(self, vals):
        if self.env.context.get("skip_workcenter_audit_log"):
            return super(WorkcenterAuditMixin, self).write(vals)

        excluded = self._audit_excluded_fields()
        tracked_fields = [
            field_name
            for field_name in vals.keys()
            if field_name in self._fields and field_name not in excluded
        ]

        old_snapshot = {}
        if tracked_fields:
            old_snapshot = self._audit_snapshot(tracked_fields)

        result = super(WorkcenterAuditMixin, self).write(vals)

        if tracked_fields and old_snapshot:
            log_values = self._audit_prepare_values(tracked_fields, old_snapshot)
            if log_values:
                logs = self.env["workcenter.audit.log"].sudo().with_context(
                    workcenter_audit_log_internal_create=True
                ).create(log_values)

                # Create chatter messages for each log
                for log in logs:
                    record = self.browse(log.res_id)
                    if record.exists():
                        body = record._audit_message_body(
                            log.field_name,
                            log.old_value,
                            log.new_value,
                        )
                        # Bypass email requirement by using sudo and no author
                        try:
                            record.sudo().message_post(
                                body=body,
                                subtype_id=self.env.ref('mail.mt_note').id,
                                message_type='comment'
                            )
                        except Exception:
                            # Silently skip if message posting fails
                            pass

        return result


class MrpWorkCenterAudit(models.Model):
    _name = "mrp.workcenter"
    _inherit = ["workcenter.audit.mixin", "mrp.workcenter", "mail.thread", "mail.activity.mixin"]

    def _audit_message_body(self, field_name, old_value, new_value):
        field = self._fields.get(field_name)
        field_label = field.string if field else field_name
        return (
            "<ul><li>%s <b>&rarr;</b> <span style='color:#159588;'>%s</span> "
            "<i>(%s)</i></li></ul>"
            % (
                html_escape(old_value or "None"),
                html_escape(new_value or "None"),
                html_escape(field_label or field_name),
            )
        )

