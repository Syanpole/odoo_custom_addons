# -*- coding: utf-8 -*-

import json

from odoo import api, fields, models
from odoo.tools import html_escape


class RoutingAuditMixin(models.AbstractModel):

    _name = "routing.audit.mixin"
    _description = "Reusable Audit Logging Mixin"

    routing_log_ids = fields.Many2many(
        "routing.log",
        compute="_compute_routing_log_ids",
        string="Audit Logs",
        readonly=True,
    )

    def _compute_routing_log_ids(self):
        log_model = self.env["routing.log"]
        empty_logs = log_model.browse()
        model = self.env["ir.model"]._get(self._name)

        records = self.filtered("id")
        logs_by_res_id = {}

        if model and records:
            logs = log_model.search(
                [("model_id", "=", model.id), ("res_id", "in", records.ids)],
                order="changed_date desc, id desc",
            )
            for log in logs:
                logs_by_res_id.setdefault(log.res_id, empty_logs)
                logs_by_res_id[log.res_id] |= log

        for record in self:
            if not record.id:
                record.routing_log_ids = empty_logs
                continue
            record.routing_log_ids = logs_by_res_id.get(record.id, empty_logs)

    @api.model
    def _routing_log_excluded_fields(self):

        return {
            "__last_update",
            "create_date",
            "create_uid",
            "write_date",
            "write_uid",
            "display_name",
            "routing_log_ids",
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
    def _routing_log_raw_value(self, record, field):
        value = record[field.name]
        if field.type == "many2one":
            return value.id or False
        if field.type in ("many2many", "one2many"):
            return tuple(value.ids)
        return value

    @api.model
    def _routing_log_has_changed(self, field, old_value, new_value):
        if field.type in ("many2many", "one2many"):
            return tuple(old_value or ()) != tuple(new_value or ())
        return old_value != new_value

    @api.model
    def _routing_log_format_value(self, field, value):
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

    def _routing_log_snapshot(self, tracked_fields):

        snapshot = {}
        for record in self:
            snapshot[record.id] = {}
            for field_name in tracked_fields:
                field = record._fields.get(field_name)
                if field:
                    snapshot[record.id][field_name] = self._routing_log_raw_value(record, field)
        return snapshot

    def _routing_log_prepare_values(self, tracked_fields, old_snapshot):

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
                new_raw = self._routing_log_raw_value(record, field)
                if not self._routing_log_has_changed(field, old_raw, new_raw):
                    continue

                values.append(
                    {
                        "model_id": model.id,
                        "res_id": record.id,
                        "field_name": field_name,
                        "old_value": self._routing_log_format_value(field, old_raw),
                        "new_value": self._routing_log_format_value(field, new_raw),
                        "changed_by": self.env.user.id,
                        "changed_date": fields.Datetime.now(),
                    }
                )
        return values

    def _routing_log_message_body(self, model_record, field_name, old_value, new_value):

        field = model_record._fields.get(field_name)
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

    def _routing_log_after_create(self, log_values):
        """Extra step ito kung may gagawin pa pagkatapos gumawa ng logs."""
        return

    def _routing_log_create_note(self, routing, body):

        note_subtype = self.env.ref("mail.mt_note", raise_if_not_found=False)
        author_id = self.env.user.partner_id.id
        if not author_id:
            author_id = self.env.ref("base.partner_root").id
        email_from = self.env.user.partner_id.email_formatted or "noreply@localhost"

        self.env["mail.message"].sudo().create(
            {
                "model": "mrp.routing",
                "res_id": routing.id,
                "message_type": "comment",
                "subtype_id": note_subtype.id if note_subtype else False,
                "body": body,
                "author_id": author_id,
                "email_from": email_from,
            }
        )

    def write(self, vals):

        if not self or self.env.context.get("skip_routing_audit_log"):
            return super(RoutingAuditMixin, self).write(vals)

        excluded = self._routing_log_excluded_fields()
        tracked_fields = [
            field_name
            for field_name in vals.keys()
            if field_name in self._fields and field_name not in excluded
        ]

        old_snapshot = {}
        if tracked_fields:
            old_snapshot = self._routing_log_snapshot(tracked_fields)

        result = super(RoutingAuditMixin, self).write(vals)

        if tracked_fields and old_snapshot:
            log_values = self._routing_log_prepare_values(tracked_fields, old_snapshot)
            if log_values:
                self.env["routing.log"].sudo().with_context(
                    routing_log_internal_create=True
                ).create(log_values)
                self._routing_log_after_create(log_values)

        return result


class MrpRouting(models.Model):

    _name = "mrp.routing"
    _inherit = ["routing.audit.mixin", "mrp.routing", "mail.thread", "mail.activity.mixin"]

    routing_log_timeline_html = fields.Html(
        compute="_compute_routing_log_timeline_html",
        string="Audit Trail",
        sanitize=True,
        readonly=True,
    )

    def _compute_routing_log_ids(self):

        log_model = self.env["routing.log"]
        empty_logs = log_model.browse()

        routing_model = self.env["ir.model"]._get("mrp.routing")
        operation_model = self.env["ir.model"]._get("mrp.routing.workcenter")

        routings = self.filtered("id")
        logs_by_routing_id = {routing_id: empty_logs for routing_id in routings.ids}

        if not routings or not routing_model:
            for record in self:
                record.routing_log_ids = logs_by_routing_id.get(record.id, empty_logs)
            return

        routing_to_operation_ids = {
            routing.id: routing.operation_ids.ids for routing in routings
        }
        all_operation_ids = set()
        for operation_ids in routing_to_operation_ids.values():
            all_operation_ids.update(operation_ids)

        operation_to_routing_id = {}
        if all_operation_ids:
            operations = self.env["mrp.routing.workcenter"].browse(list(all_operation_ids)).exists()
            operation_to_routing_id = {
                operation.id: operation.routing_id.id for operation in operations
            }

        domain = [
            "|",
            "&",
            ("model_id", "=", routing_model.id),
            ("res_id", "in", routings.ids),
            "&",
            ("model_id", "=", operation_model.id if operation_model else 0),
            ("res_id", "in", list(all_operation_ids) or [0]),
        ]
        logs = log_model.search(domain, order="changed_date desc, id desc")

        for log in logs:
            model_name = log.model_id.model
            routing_id = False
            if model_name == "mrp.routing":
                routing_id = log.res_id
            elif model_name == "mrp.routing.workcenter":
                routing_id = operation_to_routing_id.get(log.res_id)

            if routing_id in logs_by_routing_id:
                logs_by_routing_id[routing_id] |= log

        for record in self:
            record.routing_log_ids = logs_by_routing_id.get(record.id, empty_logs)

    def _compute_routing_log_timeline_html(self):
        for record in self:
            logs = record.routing_log_ids.sorted(lambda x: (x.changed_date or fields.Datetime.now(), x.id), reverse=True)
            if not logs:
                record.routing_log_timeline_html = '<p class="text-muted">No audit trail logs yet.</p>'
                continue

            items = ['<div class="o_routing_audit_feed">']
            for log in logs:
                changed_by = html_escape(log.changed_by.display_name or "System")
                changed_date = html_escape(
                    fields.Datetime.to_string(log.changed_date) if log.changed_date else ""
                )
                field_name = html_escape(log.field_name or "")
                old_value = html_escape(log.old_value or "None")
                new_value = html_escape(log.new_value or "None")

                items.append(
                    '<div class="mb-2" style="padding: 6px 0; border-bottom: 1px solid #ececec;">'
                    '<div><strong>%s</strong> <span class="text-muted">%s</span></div>'
                    '<div>&bull; %s &#8594; <span class="text-primary">%s</span> '
                    '<em class="text-muted">(%s)</em></div>'
                    '</div>'
                    % (changed_by, changed_date, old_value, new_value, field_name)
                )

            items.append("</div>")
            record.routing_log_timeline_html = "".join(items)

    def _routing_log_after_create(self, log_values):

        routing_model_id = self.env["ir.model"]._get("mrp.routing").id

        for values in log_values:
            if values.get("model_id") != routing_model_id:
                continue

            routing = self.browse(values.get("res_id"))
            if not routing.exists():
                continue

            body = self._routing_log_message_body(
                routing,
                values.get("field_name"),
                values.get("old_value"),
                values.get("new_value"),
            )
            self._routing_log_create_note(routing, body)


class MrpRoutingWorkcenter(models.Model):

    _name = "mrp.routing.workcenter"
    _inherit = ["routing.audit.mixin", "mrp.routing.workcenter"]

    def _routing_log_after_create(self, log_values):

        op_ids = [values.get("res_id") for values in log_values if values.get("res_id")]
        operations = self.browse(op_ids).exists()
        op_map = {operation.id: operation for operation in operations}
    
        for values in log_values:
            operation = op_map.get(values.get("res_id"))
            routing = operation.routing_id if operation else False
            if not routing:
                continue

            body = self._routing_log_message_body(
                operation,
                values.get("field_name"),
                values.get("old_value"),
                values.get("new_value"),
            )
            self._routing_log_create_note(routing, body)


class MrpOperations(models.Model):

    _name = "mrp.operations"
    _inherit = ["routing.audit.mixin", "mrp.operations"]

    routing_log_timeline_html = fields.Html(
        compute="_compute_routing_log_timeline_html",
        string="Audit Trail",
        sanitize=True,
        readonly=True,
    )

    def _compute_routing_log_timeline_html(self):
        for record in self:
            logs = record.routing_log_ids.sorted(lambda x: (x.changed_date or fields.Datetime.now(), x.id), reverse=True)
            if not logs:
                record.routing_log_timeline_html = '<p class="text-muted">No audit trail logs yet.</p>'
                continue

            items = ['<div class="o_routing_audit_feed">']
            for log in logs:
                changed_by = html_escape(log.changed_by.display_name or "System")
                changed_date = html_escape(
                    fields.Datetime.to_string(log.changed_date) if log.changed_date else ""
                )
                field_name = html_escape(log.field_name or "")
                old_value = html_escape(log.old_value or "None")
                new_value = html_escape(log.new_value or "None")

                items.append(
                    '<div class="mb-2" style="padding: 6px 0; border-bottom: 1px solid #ececec;">'
                    '<div><strong>%s</strong> <span class="text-muted">%s</span></div>'
                    '<div>&bull; %s &#8594; <span class="text-primary">%s</span> '
                    '<em class="text-muted">(%s)</em></div>'
                    '</div>'
                    % (changed_by, changed_date, old_value, new_value, field_name)
                )

            items.append("</div>")
            record.routing_log_timeline_html = "".join(items)