from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _compute_member_invoice(self):
        member_invoice = self.read_group(
            [("parent_id", "in", self.ids)], ["parent_id"], ["parent_id"]
        )
        res = {data["parent_id"][0]: data["parent_id_count"] for data in member_invoice}
        for line in self:
            line.member_invoice_count = res.get(line.id, 0)

    parent_id = fields.Many2one(
        comodel_name="account.move", string="Parent Invoice", index=True
    )

    member_invoice_count = fields.Integer(
        "Member Invoices", compute="_compute_member_invoice"
    )

    @api.model
    def get_members_sharing_key(self, left_partner_id, relation_type):
        members_data = {}
        relations = self.env["res.partner.relation"].search(
            [
                ("left_partner_id", "=", left_partner_id.id),
                ("type_id", "=", relation_type),
            ]
        )
        total_share = sum([r.distribution_key for r in relations])
        for rel in relations:
            members_data.update(
                {rel.right_partner_id: (rel.distribution_key / total_share)}
            )
        return members_data

    @api.model
    def _prepare_member_invoice_line(self, line, invoice, share_key):
        invoice_line = self.env["account.move.line"].new(
            {
                "move_id": invoice.id,
                "product_id": line.product_id.id,
                "quantity": line.quantity,
                "product_uom_id": line.product_uom_id.id,
                "discount": line.discount,
                "account_id": line.account_id.id,
            }
        )

        # Add analytic tags to invoice line
        invoice_line.analytic_tag_ids |= line.analytic_tag_ids

        # Get other invoice line values from product onchange
        invoice_line._onchange_product_id()
        invoice_line_vals = invoice_line._convert_to_write(invoice_line._cache)

        # Analytic Invoice invoicing period is doesn't lies in same month update with
        # property_account_wip_id
        if line.ps_invoice_id.period_id:
            period_date = line.ps_invoice_id.period_id.date_start.strftime("%Y-%m")
            invoice_date = (
                line.ps_invoice_id.date or line.ps_invoice_id.invoice_id.invoice_date
            )
            inv_date = invoice_date.strftime("%Y-%m")
            if inv_date != period_date:
                fpos = invoice.fiscal_position_id
                account = self.env["analytic.move"].get_product_wip_account(
                    line.product_id, fpos
                )
                invoice_line_vals.update({"account_id": account.id})

        invoice_line_vals.update(
            {
                "name": line.name,
                "analytic_account_id": line.analytic_account_id.id,
                "price_unit": line.price_unit * share_key,
            }
        )
        return invoice_line_vals

    def _prepare_member_invoice(self, partner):
        self.ensure_one()
        company_id = partner.company_id if partner.company_id else self.company_id
        journal = self.journal_id or self.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", company_id.id)], limit=1
        )
        if not journal:
            raise ValidationError(
                _("Please define a sale journal for the company '%s'.")
                % (company_id.name or "",)
            )
        currency = (
            partner.property_product_pricelist.currency_id or company_id.currency_id
        )
        invoice = self.env["account.move"].new(
            {
                "ref": self.name,
                "move_type": "out_invoice",
                "partner_id": partner.address_get(["invoice"])["invoice"],
                "currency_id": currency.id,
                "journal_id": journal.id,
                "invoice_date": self.invoice_date,
                # TODO: restore origin field?
                # 'origin': self.name,
                "company_id": company_id.id,
                "parent_id": self.id,
                "user_id": partner.user_id.id,
            }
        )
        # Get other invoice values from partner onchange
        invoice._onchange_partner_id()
        return invoice._convert_to_write(invoice._cache)

    def _create_member_invoice(self, partner, share_key):
        self.ensure_one()
        invoice_vals = self._prepare_member_invoice(partner)
        invoice = self.env["account.move"].create(invoice_vals)
        invoice.write(
            {
                "invoice_line_ids": [
                    (0, 0, self._prepare_member_invoice_line(line, invoice, share_key))
                    for line in self.invoice_line_ids
                ],
            }
        )
        return invoice

    def _post(self, soft=True):
        """
            If partner has members split invoice by distribution keys,
            & Validate same invoice without creating moves
            Otherwise, call super()
        :return:
        """

        relation_type = self.env.ref("ps_partner_multi_relation.rel_type_consortium").id
        members_data = self.get_members_sharing_key(self.partner_id, relation_type)
        if not members_data:
            return super()._post(soft=soft)

        # lots of duplicate calls to action_invoice_open, so we remove those already open
        to_open_invoices = self.filtered(lambda inv: inv.state != "open")
        if to_open_invoices.filtered(lambda inv: inv.state != "draft"):
            raise UserError(
                _("Invoice must be in draft state in order to validate it.")
            )

        for invoice in to_open_invoices:
            for partner, share_key in members_data.items():
                invoice._create_member_invoice(partner, share_key)

        to_open_invoices.button_cancel()

        return to_open_invoices

    def action_view_member_invoice(self):
        self.ensure_one()
        action = self.env.ref("account.action_move_out_invoice_type").read()[0]
        invoice = self.search([("parent_id", "in", self._ids)])
        if not invoice or len(invoice) > 1:
            action["domain"] = [("id", "in", invoice.ids)]
        elif invoice:
            action["views"] = [(self.env.ref("account.view_move_form").id, "form")]
            action["res_id"] = invoice.id
        action["context"] = {}
        return action
