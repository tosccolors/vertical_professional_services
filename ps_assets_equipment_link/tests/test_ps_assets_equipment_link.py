from odoo.tests.common import TransactionCase


class TestPsAssetsEquipmentLink(TransactionCase):
    def setUp(self):
        super().setUp()
        self.invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.env["res.partner"].search([], limit=1).id,
                "invoice_date": "2024-03-01",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "line with asset",
                            "asset_profile_id": self.env.ref(
                                "ps_assets_equipment_link.demo_asset_profile"
                            ).id,
                        },
                    )
                ],
            }
        )

    def test_asset_creation(self):
        last_asset = self.env["account.asset"].search([], order="id desc", limit=1)
        self.invoice.action_post()
        new_asset = self.env["account.asset"].search([("id", ">", last_asset.id or 0)])
        self.assertTrue(new_asset.equipment_ids)
        equipment_action = new_asset.button_open_equipment()
        equipment = self.env[equipment_action["res_model"]].search(
            equipment_action["domain"]
        )
        self.assertEqual(new_asset.equipment_ids, equipment)
