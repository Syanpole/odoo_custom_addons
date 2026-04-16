# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def action_print_product_audit_pdf(self):
        self.ensure_one()
        self.flush()
        self.invalidate_cache()
        cache_buster = str(fields.Datetime.now())
        return self.env.ref(
            "product_audit_logs.report_product_audit_pdf"
        ).with_context(
            report_cache_buster=cache_buster
        ).report_action(
            self,
            data={"report_cache_buster": cache_buster},
        )
