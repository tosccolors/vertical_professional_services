# Copyright 2014-2023 The Open Source Company (www.tosc.nl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from collections import OrderedDict

from odoo import api, fields, models
from odoo.tools import frozendict, is_html_empty


class AccountMove(models.Model):
    _inherit = "account.move"

    invoice_description = fields.Html("Description")
    ps_custom_layout = fields.Boolean("Add Custom Header/Footer")
    ps_custom_header = fields.Text("Custom Header")
    ps_custom_footer = fields.Text("Custom Footer")

    def group_by_analytic_acc(self, data_type, uom_hrs=False):
        self.ensure_one()
        result = {}
        if data_type == "sale_order":
            for line in self.invoice_line_ids.sorted("sequence"):
                for analytic_account_id in (line.analytic_distribution or {}).keys():
                    analytic_account = self.env["account.analytic.account"].browse(
                        int(analytic_account_id)
                    )
                    if analytic_account in result:
                        result[analytic_account].append(line)
                    else:
                        result[analytic_account] = [line]
        if data_type == "project":
            UOMHrs = self.env.ref("uom.product_uom_hour").id
            invoice_line_ids = self.invoice_line_ids.sorted("sequence")
            # TODO what are ic_lines?
            # if self.ic_lines or (self.refund_invoice_id and self.refund_invoice_id.ic_lines):
            #    invoice_line_ids = self.invoice_line_ids.filtered(lambda l: l.revenue_line)
            if uom_hrs:
                for line in invoice_line_ids.filtered(
                    lambda l: l.product_uom_id.id == UOMHrs
                ):
                    quantity = line.product_uom_id._compute_quantity(
                        line.quantity, line.product_uom_id
                    )
                    price_subtotal = line.product_uom_id._compute_price(
                        line.price_subtotal, line.product_uom_id
                    )
                    for analytic_account_id in (
                        line.analytic_distribution or {}
                    ).keys():
                        analytic_account = self.env["account.analytic.account"].browse(
                            int(analytic_account_id)
                        )
                        if analytic_account in result:
                            result[analytic_account]["tot_hrs"] += quantity
                            result[analytic_account]["sub_total"] += price_subtotal
                        else:
                            result[analytic_account] = {
                                "tot_hrs": quantity,
                                "sub_total": price_subtotal,
                                "name": line.name,
                            }
            else:
                for line in invoice_line_ids.filtered(
                    lambda l: not l.product_uom_id or l.product_uom_id.id != UOMHrs
                ):
                    for analytic_account_id in (
                        line.analytic_distribution or {}
                    ).keys():
                        analytic_account = self.env["account.analytic.account"].browse(
                            int(analytic_account_id)
                        )
                        result.setdefault(analytic_account, []).append(line)
        return result

    def group_by_project_product_unit_price(self):
        """
        Return synthesized account.move.line records implementing grouping required for
        ps invoices
        """
        grouped = OrderedDict()

        def key_func(line):
            return (
                frozendict(line.analytic_distribution),
                line.product_id,
                line.price_unit,
            )

        for line in self.mapped("invoice_line_ids").sorted(key=key_func):
            key = key_func(line)
            if key not in grouped:
                grouped[key] = line.new(line._cache)
                grouped[key]["name"] = "%s%s" % (
                    line.ps_invoice_id.project_id.name
                    and (line.ps_invoice_id.project_id.name + " - ")
                    or "",
                    line.product_id.name,
                )
            else:
                grouped[key].quantity += line.quantity

        return grouped.values()

    def parse_invoice_description(self):
        res = not is_html_empty(self.invoice_description)
        return res

    def value_conversion(self, value, monetary=False, digits=2, currency_obj=False):
        lang_objs = self.env["res.lang"].search([("code", "=", self.partner_id.lang)])
        if not lang_objs:
            lang_objs = self.env["res.lang"].search([], limit=1)
        lang_obj = lang_objs[0]

        res = lang_obj.format(
            "%." + str(digits) + "f", value, grouping=True, monetary=monetary
        )
        if currency_obj and currency_obj.symbol:
            if currency_obj.position == "after":
                res = "%s\N{NO-BREAK SPACE}%s" % (res, currency_obj.symbol)
            elif currency_obj and currency_obj.position == "before":
                res = "%s\N{NO-BREAK SPACE}%s" % (currency_obj.symbol, res)
        return res

    def get_invoice_project(self):
        project = self.env["project.project"]
        analytic_invoice_id = self.invoice_line_ids.mapped("ps_invoice_id")

        if analytic_invoice_id:
            project = analytic_invoice_id.project_id
        else:
            account_analytic_id = (
                self.invoice_line_ids.mapped("analytic_distribution") or {}
            ).keys()
            if len(account_analytic_id) == 1:
                if (
                    len(
                        self.env["account.analytic.account"]
                        .browse(int(account_analytic_id[0]))
                        .project_ids
                    )
                    == 1
                ):
                    project = account_analytic_id.project_ids
        return project

    def get_bank_details(self):
        self.ensure_one()
        bank_ids = self.operating_unit_id.partner_id.bank_ids.mapped("bank_id")
        bank_accs = self.env["account.journal"].search(
            [
                ("operating_unit_id", "=", self.operating_unit_id.id),
                ("company_id", "=", self.company_id.id),
                ("bank_id", "in", bank_ids.ids),
                ("type", "=", "bank"),
            ]
        )
        return bank_accs

    @api.model
    def _get_first_invoice_fields(self, invoice):
        result = super()._get_first_invoice_fields(invoice)
        for field in (
            "invoice_description",
            "ps_custom_layout",
            "ps_custom_header",
            "ps_custom_footer",
        ):
            result[field] = invoice[field]
        return result

    def _get_name_invoice_report(self):
        self.ensure_one()
        ps_invoice = self.invoice_line_ids.mapped("ps_invoice_id")
        if not self.company_id.use_standard_layout and ps_invoice:
            return "ps_account.report_invoice_document_ps_account"
        return super()._get_name_invoice_report()
