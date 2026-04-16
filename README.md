# Custom Addons

This folder contains the custom Odoo 13 modules used for audit logging, PDF report generation, and related custom workflows.

## Shared Pattern

Most of these modules follow the same structure:

- An immutable audit log model stores the actual change history.
- Model `create` and `write` hooks capture field changes.
- A PDF report reads from the immutable log model.
- A form button opens the PDF report from the record being audited.
- Chatter posts are used as a convenience layer in some modules, but the PDF should read from the audit log table.

## Modules

### `bom_audit_logs`
Audit logs and PDF report for `mrp.bom`.

- Tracks BoM header changes.
- Also logs component line and by-product changes.
- Adds an Audit PDF button on the BoM form.

### `lot_number_logs`
Audit logs and PDF report for `stock.production.lot`.

- Tracks lot / serial number field changes.
- Adds an Audit PDF button on the Lot/Serial form.
- Uses an immutable lot audit log table.

### `product_audit_logs`
Audit logs and PDF report for `product.product`.

- Tracks product variant changes.
- Adds an Audit PDF button on the Product form.
- Uses immutable audit logs.

### `product_template_audit_logs`
Audit logs and PDF report for `product.template`.

- Tracks product template changes.
- Adds an Audit PDF button on the Product Template form.
- Uses immutable audit logs.

### `routing_logs`
Audit and PDF support for routing-related records.

- Used for routing change tracking and PDF output.

### `worckcenter_audit_logs`
Audit and PDF support for workcenter-related records.

- Technical module name is intentionally spelled `worckcenter_audit_logs`.
- Includes audit logging and PDF output for workcenter records.

## Installation

1. Make sure `custom_addons` is included in the Odoo `addons_path`.
2. Restart Odoo after adding or renaming modules.
3. Upgrade the module from Apps or with the command line.
4. If a module was renamed, update the database module name and XML ID module namespace before upgrading.

## Notes

- These modules depend on Odoo 13 and are designed around the stock, product, mail, and mrp apps.
- Several PDFs use a static logo stored in the module under `static/src/img/logo.png`.
- Existing unrelated custom modules in this database may still produce warnings during registry load.

## Common Troubleshooting

- If a PDF opens but shows no rows, confirm the record actually changed through the audited model's `create` or `write` path.
- If a report shows stale data, check whether the report action is cached or if the module needs an upgrade.
- If a renamed module stops loading, verify the database entries in `ir_module_module` and `ir_model_data` match the new technical name.
