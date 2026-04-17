# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError


class MrpProductionAuditLog(models.Model):
    _name = "mrp.production.audit.log"
    _description = "MRP Production Audit Log"
    _order = "changed_date desc, id desc"

    model_id = fields.Many2one("ir.model", required=True, readonly=True, index=True)
    res_id = fields.Integer(required=True, readonly=True, index=True)
    field_name = fields.Char(required=True, readonly=True)
    old_value = fields.Char(readonly=True)
    new_value = fields.Char(readonly=True)
    changed_by = fields.Many2one(
        "res.users",
        required=True,
        readonly=True,
        index=True,
        default=lambda self: self.env.user,
    )
    changed_date = fields.Datetime(
        required=True,
        readonly=True,
        index=True,
        default=fields.Datetime.now,
    )

    _sql_constraints = [
        (
            "mrp_production_audit_log_res_id_positive",
            "CHECK(res_id > 0)",
            "Related record id must be a positive integer.",
        )
    ]

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("production_audit_log_internal_create") and not self.env.user.has_group(
            "base.group_system"
        ):
            raise UserError("Audit logs are immutable and can only be created internally.")
        return super(MrpProductionAuditLog, self).create(vals_list)

    def write(self, vals):
        raise UserError("Audit logs are immutable and cannot be modified or deleted.")

    def unlink(self):
        raise UserError("Audit logs are immutable and cannot be modified or deleted.")


class ResUsers(models.Model):
    _inherit = "res.users"

    def _production_audit_log_allowed_ids(self):
        self.ensure_one()
        logs = self.env["mrp.production.audit.log"].sudo().search([])

        if self.has_group("base.group_system"):
            return logs.ids

        allowed_ids = []
        access_cache = {}

        for log in logs:
            model_name = log.model_id.model
            if not model_name or log.res_id <= 0:
                continue

            cache_key = (model_name, log.res_id)
            if cache_key not in access_cache:
                access_cache[cache_key] = self._production_audit_log_can_read_target(model_name, log.res_id)

            if access_cache[cache_key]:
                allowed_ids.append(log.id)

        return allowed_ids

    def _production_audit_log_can_read_target(self, model_name, res_id):
        self.ensure_one()
        try:
            record = self.env[model_name].with_user(self.id).browse(res_id).exists()
            if not record:
                return False
            record.check_access_rights("read")
            record.check_access_rule("read")
            return True
        except (AccessError, KeyError, ValueError):
            return False
