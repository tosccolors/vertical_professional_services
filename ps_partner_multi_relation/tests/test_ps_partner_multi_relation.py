from odoo.tests.common import TransactionCase


class TestPsPartnerMultiRelation(TransactionCase):
    def test_ps_partner_multi_relation(self):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.env.ref(
                    "ps_partner_multi_relation.partner_consortium"
                ).id,
                "invoice_line_ids": [
                    (0, 0, {"name": "/", "price_unit": 42, "quantity": 42}),
                ],
                "invoice_description": "<p>hello world</p>",
                "ps_custom_header": "custom header",
                "ps_custom_footer": "custom footer",
                "ps_custom_layout": True,
            }
        )
        invoice.action_post()
        view_action = invoice.action_view_member_invoice()
        child_invoices = self.env["account.move"].search(view_action["domain"])
        self.assertItemsEqual(
            child_invoices.mapped("partner_id"),
            self.env.ref("base.res_partner_2")
            + self.env.ref("base.res_partner_12")
            + self.env.ref("base.res_partner_18"),
        )
        self.assertEqual(invoice.member_invoice_count, 3)
        partner18_invoice = child_invoices.filtered(
            lambda x: x.partner_id == self.env.ref("base.res_partner_18")
        )
        partner12_invoice = child_invoices.filtered(
            lambda x: x.partner_id == self.env.ref("base.res_partner_12")
        )
        self.assertEqual(
            partner18_invoice.amount_total, partner12_invoice.amount_total * 2
        )
        self.assertEqual(invoice.state, "cancel")
        self.assertEqual(
            partner18_invoice.invoice_description,
            "<p>hello world</p>",
        )
        self.assertEqual(
            partner18_invoice.ps_custom_layout,
            True,
        )
        self.assertEqual(
            partner18_invoice.ps_custom_footer,
            "custom footer",
        )
        self.assertEqual(
            partner18_invoice.ps_custom_header,
            "custom header",
        )

        to_merge_invoices = child_invoices
        for invoice in child_invoices:
            to_merge_invoices += invoice.copy()
        action = (
            self.env["invoice.merge"]
            .with_context(
                active_model="account.move",
                active_ids=to_merge_invoices.ids,
            )
            .create({})
            .merge_invoices()
        )
        all_invoices = self.env["account.move"].browse(action["domain"][0][2])
        merged_invoices = all_invoices - to_merge_invoices
        self.assertEqual(set(to_merge_invoices.mapped("state")), {"cancel"})
        self.assertItemsEqual(
            merged_invoices.mapped("partner_id"),
            self.env.ref("base.res_partner_2")
            + self.env.ref("base.res_partner_12")
            + self.env.ref("base.res_partner_18"),
        )
