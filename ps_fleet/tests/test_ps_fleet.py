from datetime import date, timedelta

from odoo.tests.common import Form, TransactionCase


class TestPsFleet(TransactionCase):
    def test_ps_fleet_flow(self):
        vehicle = self.env["fleet.vehicle"].create(
            {
                "name": "a vehicle",
                "model_id": self.env.ref("fleet.model_astra").id,
                "log_contracts": [
                    (
                        0,
                        0,
                        {
                            "name": "a contract",
                            "start_date": date.today() - timedelta(days=60),
                            "lease_period": 3,
                        },
                    )
                ],
            }
        )
        self.assertTrue(vehicle.contract_renewal_due_soon)
        self.assertIn(
            vehicle,
            self.env["fleet.vehicle"].search(
                [("contract_renewal_due_soon", "=", True)]
            ),
        )
        with Form(vehicle.log_contracts) as vehicle_form:
            vehicle_form.lease_period = 12
        self.assertFalse(vehicle.contract_renewal_due_soon)
        self.assertNotIn(
            vehicle,
            self.env["fleet.vehicle"].search(
                [("contract_renewal_due_soon", "=", True)]
            ),
        )
