from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    state = fields.Selection(
        selection_add=[
            ("approve_partner", "Approved By Partner"),
            ("revise", "To Be Revised"),
            ("post",),
        ],
        default="submit",
        ondelete={"approve_partner": "set default", "revise": "set default"},
    )
    journal_id = fields.Many2one(
        default=lambda self: self.env.user.company_id.decl_journal_id
    )

    def revise_expense(self):
        expenses = self.mapped("expense_line_ids").filtered(
            lambda x: x.state == "reported"
        )
        self.write({"state": "revise"})
        expenses.write({"state": "revise"})

    def expense_revised(self):
        expenses = self.mapped("expense_line_ids").filtered(
            lambda x: x.state == "revise"
        )
        expenses.write({"state": "reported"})
        self.write({"state": "approve"})

    @api.onchange("expense_line_ids")
    def onchange_expense_line_ids(self):
        if self.expense_line_ids and self.expense_line_ids[0].operating_unit_id:
            if not self.operating_unit_id or (
                self.operating_unit_id and len(self.expense_line_ids) == 1
            ):
                self.operating_unit_id = self.expense_line_ids[0].operating_unit_id.id
        else:
            self.operating_unit_id = False

    # updated by expense sheets are approved by partner group will goto status
    # Approved By Partner

    def approve_partner_expense_sheets(self):
        if not self.env.user.has_group("ps_expense.group_hr_expense_partner"):
            raise UserError(_("Only Partner can approve expenses"))
        self.write({"state": "approve_partner", "user_id": self.env.user.id})

    # updated by expense sheets move create which are in  status Approved By Partner

    def action_partner_sheet_move_create(self):
        if any(sheet.state != "approve_partner" for sheet in self):
            raise UserError(
                _("You can only generate accounting entry for approved expense(s).")
            )

        if any(not sheet.journal_id for sheet in self):
            raise UserError(
                _(
                    "Expenses must have an expense journal specified to generate "
                    "accounting entries."
                )
            )

        expense_line_ids = self.mapped("expense_line_ids").filtered(
            lambda r: not float_is_zero(
                r.total_amount,
                precision_rounding=(
                    r.currency_id or self.env.user.company_id.currency_id
                ).rounding,
            )
        )
        res = expense_line_ids.action_move_create()

        if not self.accounting_date:
            self.accounting_date = self.account_move_id.date

        if self.payment_mode == "own_account" and expense_line_ids:
            self.write({"state": "post"})
        else:
            self.write({"state": "done"})
        return res

    @api.constrains("expense_line_ids", "employee_id")
    def _check_employee(self):
        employee_ids = self.expense_line_ids.mapped("employee_id")
        # checking the state revised and group Manager
        if self.state == "revise":
            if self.env.user.has_group("hr_expense.group_hr_expense_manager"):
                # Updating the expense_line_ids with employee_id
                for emp in self.expense_line_ids:
                    emp.employee_id = self.employee_id
                return True
        if len(employee_ids) > 1 or (
            len(employee_ids) == 1 and employee_ids != self.employee_id
        ):
            raise ValidationError(
                _("You cannot add expense lines of another employee.")
            )
