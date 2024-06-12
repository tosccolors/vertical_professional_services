# Copyright 2014-2023 The Open Source Company (www.tosc.nl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    invoice_description = fields.Html("Description")

    def group_by_analytic_acc(self, data_type, uom_hrs=False):
        self.ensure_one()
        result = {}
        if data_type == "sale_order":
            for line in self.invoice_line_ids.sorted("sequence"):
                if line.analytic_account_id in result:
                    result[line.analytic_account_id].append(line)
                else:
                    result[line.analytic_account_id] = [line]
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
                    if line.analytic_account_id in result:
                        result[line.analytic_account_id]["tot_hrs"] += quantity
                        result[line.analytic_account_id]["sub_total"] += price_subtotal
                        result[line.analytic_account_id]["name"] += " "+line.name
                    else:
                        result[line.analytic_account_id] = {
                            "tot_hrs": quantity,
                            "sub_total": price_subtotal,
                            "name": line.name,
                        }
            else:
                for line in invoice_line_ids.filtered(
                    lambda l: not l.product_uom_id or l.product_uom_id.id != UOMHrs
                ):
                    result.setdefault(line.analytic_account_id, []).append(line)
        return result

    def parse_invoice_description(self):
        res = False
        desc = self.invoice_description
        if desc and desc != "<p><br></p>":
            res = True
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
            account_analytic_id = self.invoice_line_ids.mapped("analytic_account_id")
            if (
                len(account_analytic_id) == 1
                and len(account_analytic_id.project_ids) == 1
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
