# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class MrpBomAuditLog(models.Model):
    _name = "mrp.bom.audit.log"
    _description = "Mrp BoM Audit Log"
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
            "mrp_bom_audit_log_res_id_positive",
            "CHECK(res_id > 0)",
            "Related record id must be a positive integer.",
        )
    ]

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("bom_audit_log_internal_create") and not self.env.user.has_group(
            "base.group_system"
        ):
            raise UserError("Audit logs are immutable and can only be created internally.")
        return super(MrpBomAuditLog, self).create(vals_list)

    def write(self, vals):
        raise UserError("Audit logs are immutable and cannot be modified or deleted.")

    def unlink(self):
        raise UserError("Audit logs are immutable and cannot be modified or deleted.")
