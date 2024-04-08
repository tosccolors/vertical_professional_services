# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class Project(models.Model):
    _inherit = "project.project"

    @api.depends("task_ids.standard")
    def _compute_standard(self):
        for this in self:
            this.standard_task_id = this.task_ids.filtered("standard")

    overtime = fields.Boolean(string="Overtime Taken")
    overtime_hrs = fields.Boolean(string="Overtime Hours")
    invoice_principle = fields.Selection(
        [
            ("ff", "Fixed Fee"),
            ("tm", "Time and Material"),
            ("ctm", "Capped Time and Material"),
        ],
    )
    invoice_schedule_ids = fields.One2many(
        "invoice.schedule.lines", "project_id", string="Invoice Schedule"
    )
    standard_task_id = fields.Many2one(
        "project.task", compute=_compute_standard, string="Standard Task", store=True
    )
    invoice_properties_invoice_mileage = fields.Boolean(
        related="invoice_properties.invoice_mileage"
    )
    ps_mileage_product_id = fields.Many2one(
        "product.product",
        string="Mileage product",
        domain=lambda self: [
            (
                "categ_id",
                "=",
                self.env.ref("ps_timesheet_invoicing.product_category_mileage").id,
            ),
            ("uom_id", "=", self.env.ref("uom.product_uom_km").id),
        ],
        context=lambda env: {
            "default_categ_id": env.ref(
                "ps_timesheet_invoicing.product_category_mileage"
            ).id,
            "default_uom_id": env.ref("uom.product_uom_km").id,
        },
    )

    @api.constrains("overtime", "overtime_hrs")
    def _check_project_overtime(self):
        company_id = self.company_id.id if self.company_id else False

        overtime_taken_project = self.search(
            [("company_id", "=", company_id), ("overtime", "=", True)]
        )
        if len(overtime_taken_project) > 1:
            raise ValidationError(
                _("You can have only one project with 'Overtime Taken' per company!")
            )

        overtime_project = self.search(
            [("company_id", "=", company_id), ("overtime_hrs", "=", True)]
        )
        if len(overtime_project) > 1:
            raise ValidationError(
                _("You can have only one project with 'Overtime Hours' per company!")
            )

    def action_view_invoice(self):
        invoice_lines = self.env["account.move.line"]
        invoices = invoice_lines.search(
            [("account_analytic_id", "=", self.analytic_account_id.id)]
        ).mapped("invoice_id")
        action = self.env.ref("account.action_invoice_tree1").read()[0]
        if len(invoices) > 1:
            action["domain"] = [("id", "in", invoices.ids)]
        elif len(invoices) == 1:
            action["views"] = [(self.env.ref("account.view_move_form").id, "form")]
            action["res_id"] = invoices.ids[0]
        else:
            action = {"type": "ir.actions.act_window_close"}
        return action


class InvoiceScheduleLine(models.Model):
    _name = "invoice.schedule.lines"
    _description = "Invoice schedule"

    project_id = fields.Many2one(
        "project.project",
    )
