# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tests.common import Form


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends("invoice_line_ids")
    def _compute_period_id(self):
        ps_invoice_id = self.invoice_line_ids.mapped("ps_invoice_id")[:1]
        self.period_id = ps_invoice_id.period_id

    target_invoice_amount = fields.Monetary("Target Invoice Amount")
    period_id = fields.Many2one(
        "date.range", compute="_compute_period_id", string="Invoicing Period"
    )
    wip_move_id = fields.Many2one(
        "account.move",
        string="WIP Journal Entry",
        readonly=True,
        index=True,
        ondelete="restrict",
        copy=False,
    )
    create_wip_entry = fields.Boolean(
        default=True,
        help="If you uncheck this, no accounting entries will be created to move "
        "the amount into the invoicing period",
    )

    def compute_target_invoice_amount(self):
        try:
            if self.amount_untaxed != self.target_invoice_amount:
                self.reset_target_invoice_amount()
                factor = self.target_invoice_amount / (self.amount_untaxed or 1)
                discount = (1.0 - factor) * 100
                with Form(self) as invoice_form:
                    for i in range(len(self.invoice_line_ids)):
                        with invoice_form.invoice_line_ids.edit(i) as line:
                            line.discount = discount
        except ZeroDivisionError:
            raise UserError(
                _("You cannot set a target amount if the invoice line amount is 0")
            )

    def reset_target_invoice_amount(self):
        with Form(self) as invoice_form:
            for i in range(len(self.invoice_line_ids)):
                with invoice_form.invoice_line_ids.edit(i) as line:
                    line.discount = 0

    def _get_timesheet_by_group(self):
        self.ensure_one()
        ptl_ids = []
        ps_invoice_ids = self.invoice_line_ids.mapped("ps_invoice_id")
        for ps_invoice in ps_invoice_ids:
            for grp_line in ps_invoice.user_total_ids:
                ptl_ids += grp_line.detail_ids
        userProject = {}
        for ptl in ptl_ids:
            project_id, user_id = (
                ptl.project_id if ptl.project_id else ptl.task_id.project_id,
                ptl.user_id,
            )
            if (
                project_id.correction_charge
                and project_id.invoice_properties.specs_invoice_report
            ):
                if (project_id, user_id) in userProject:
                    userProject[(project_id, user_id)] = userProject[
                        (project_id, user_id)
                    ] + [ptl]
                else:
                    userProject[(project_id, user_id)] = [ptl]
        return userProject

    def _post(self, soft=True):
        to_process_invoices = self.filtered(
            lambda inv: inv.move_type in ("out_invoice", "out_refund")
        )
        # TODO: migrate ps_external_consolidation
        # if to_process_invoices:
        #    to_process_invoices.action_create_ic_lines()
        # if supplier_invoices:
        #    supplier_invoices.fill_trading_partner_code_supplier_invoice()
        res = super()._post(soft=soft)
        for invoice in to_process_invoices:
            ps_invoice = invoice.invoice_line_ids.mapped("ps_invoice_id")
            if ps_invoice and invoice.move_type != "out_refund":
                # if invoicing period doesn't lie in same month
                period_date = ps_invoice.period_id.date_start
                cur_date = datetime.now().date()
                inv_date = invoice.date or invoice.invoice_date or cur_date
                if (
                    inv_date.timetuple()[:2] != period_date.timetuple()[:2]
                    and invoice.create_wip_entry
                ):
                    invoice.action_wip_move_create()

                if ps_invoice.invoice_properties.fixed_amount:
                    invoice_line = invoice.invoice_line_ids[:1]
                    self.env["account.analytic.line"].create(
                        [
                            {
                                "name": _("Fixed amount value difference"),
                                "date": invoice.date,
                                "move_line_id": invoice_line.id,
                                "tag_ids": [
                                    (
                                        6,
                                        0,
                                        self.env.ref(
                                            "ps_timesheet_invoicing."
                                            "analytic_tag_fixed_amount_value_difference"
                                        ).ids,
                                    )
                                ],
                                "unit_amount": 1,
                                "account_id": ps_invoice.project_id.analytic_account_id.id,
                                "amount": ps_invoice.project_id.ps_fixed_amount
                                - sum(
                                    line.unit_amount * line.effective_fee_rate
                                    for line in invoice.mapped(
                                        "invoice_line_ids.user_task_total_line_ids"
                                    )
                                ),
                            },
                            {
                                "name": _("Fixed amount hour difference"),
                                "date": invoice.date,
                                "move_line_id": invoice_line.id,
                                "tag_ids": [
                                    (
                                        6,
                                        0,
                                        self.env.ref(
                                            "ps_timesheet_invoicing."
                                            "analytic_tag_fixed_amount_hours_difference"
                                        ).ids,
                                    )
                                ],
                                "product_uom_id": self.env.ref(
                                    "uom.product_uom_hour"
                                ).id,
                                "account_id": ps_invoice.project_id.analytic_account_id.id,
                                "unit_amount": ps_invoice.project_id.ps_fixed_hours
                                - sum(
                                    invoice.mapped(
                                        "invoice_line_ids.user_task_total_line_ids.unit_amount"
                                    )
                                ),
                            },
                        ]
                    )
        return res

    def action_wip_move_create(self):
        """Creates invoice related analytics and financial move lines"""
        for inv in self:
            if not inv.company_id.wip_journal_id:
                raise UserError(_("Please define WIP journal on company."))
            if not inv.company_id.wip_journal_id.sequence_id:
                raise UserError(_("Please define sequence on the type WIP journal."))
            wip_journal = inv.company_id.wip_journal_id
            sequence = wip_journal.sequence_id
            if (
                inv.move_type in ["out_refund", "in_invoice", "in_refund"]
                or inv.wip_move_id
            ):
                continue
            date_end = inv.period_id.date_end
            new_name = sequence.with_context(ir_sequence_date=date_end).next_by_id()
            account = inv.line_ids.filtered(
                lambda x: x.account_type in ("receivable", "payable")
            ).account_id
            wip_move = inv.wip_move_create(wip_journal, new_name, account.id, inv.name)
            wip_move._post()
            # make the invoice point to that wip move
            inv.wip_move_id = wip_move
            # wip reverse posting
            reverse_date = wip_move.date + timedelta(days=1)
            # ######### updated reversal code####
            # line_amt = sum(ml.credit + ml.debit for ml in wip_move.line_ids)
            # reconcile = False
            # if line_amt > 0:
            #     reconcile = True
            # reverse_wip_move = wip_move.create_reversals(
            #     date=reverse_date,
            #     journal=wip_journal,
            #     move_prefix='WIP Invoicing Reverse',
            #     line_prefix='WIP Invoicing Reverse',
            #     reconcile=reconcile
            # )
            # #######################################
            reverse_wip_move = wip_move._reverse_moves(
                default_values_list=[
                    dict(date=reverse_date, journal_id=wip_journal.id, auto_post="no")
                ],
            )
            wip_nxt_seq = sequence.with_context(
                ir_sequence_date=reverse_wip_move.date
            ).next_by_id()
            reverse_wip_move.write({"name": wip_nxt_seq})
        return True

    def button_draft(self):
        res = super().button_draft()

        wip_moves = self.mapped("wip_move_id")
        if wip_moves:
            wip_moves += self.search([("reversed_entry_id", "in", wip_moves.ids)])
            wip_moves.button_draft()

        return res

    def button_cancel(self):
        result = super().button_cancel()

        wip_moves = self.mapped("wip_move_id")
        if wip_moves:
            wip_moves += self.search([("reversed_entry_id", "in", wip_moves.ids)])
            wip_moves.button_cancel()

        return result

    def unlink(self):
        wip_moves = self.mapped("wip_move_id")
        self.write({"wip_move_id": False})
        if wip_moves:
            wip_moves += self.search([("reversed_entry_id", "in", wip_moves.ids)])
            wip_moves.with_context(force_delete=True).unlink()

        return super().unlink()

    def wip_move_create(self, wip_journal, name, ar_account_id, ref=None):
        self.ensure_one()
        move_date = self.date
        last_day_month_before = move_date - timedelta(days=move_date.day)
        default = {
            "name": name,
            "ref": ref if ref else _("WIP Invoicing Posting"),
            "journal_id": wip_journal.id,
            "date": last_day_month_before,
            "narration": _("WIP Invoicing Posting"),
            "invoice_line_ids": [],
            "move_type": "entry",
        }
        wip_move_data = self.copy_data(default)[0]
        # we filter all BS lines out of all move lines. And also all "null" lines
        # because of reconcile problem
        # All filtered out lines are unlinked. All will be kept unchanged and copied
        # with reversing debit/credit and replace P/L account by wip-account.
        include_types = (
            "income",
            "income_other",
            "expense",
            "expense_depreciation",
            "expense_direct_cost",
        )
        wip_move_data["line_ids"] = list(
            filter(
                lambda x: x[2]["price_unit"] != 0
                and self.env["account.account"].browse(x[2]["account_id"]).account_type
                in include_types,
                wip_move_data["line_ids"],
            )
        )
        for command1, command2, line_data in list(wip_move_data["line_ids"]):
            wip_line_data = line_data.copy()

            account_id = (
                self.env["product.product"]
                .browse(wip_line_data["product_id"] or [])
                .property_account_wip_id.id
                or wip_journal.default_account_id.id
            )
            if account_id:
                wip_line_data["account_id"] = account_id

            wip_line_data["price_unit"] = -line_data["price_unit"]

            wip_move_data["line_ids"].append((command1, command2, wip_line_data))
        return self.create(wip_move_data)
