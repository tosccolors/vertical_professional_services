from odoo.tests.common import Form, TransactionCase


class TestPsHr(TransactionCase):
    def test_hr_employee_wizard(self):
        wizard = (
            self.env["hr.employee.wizard"]
            .with_context(lang="en_US")
            .create(
                {
                    "firstname": "first",
                    "lastname": "last",
                    "login": "ps_hr_test_login",
                    "street": "street",
                    "city": "city",
                    "zip": "zip",
                    "klippa_user": "klippa_user",
                }
            )
        )
        with Form(wizard) as wizard_form:
            wizard_form.default_operating_unit_id = self.env.ref(
                "operating_unit.main_operating_unit"
            )
        action = wizard.create_all()
        employee = self.env["hr.employee"].browse(action["res_id"])
        self.assertTrue(employee)
