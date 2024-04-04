from odoo.tests.common import Form, TransactionCase


class TestPsCrm(TransactionCase):
    def setUp(self):
        super().setUp()
        self.lead = self.env.ref("crm.crm_case_10")

    def test_crm_lead_form(self):
        """Run onchanges on crm lead form"""
        partner = self.env.ref("ps_crm.lead_main_partner")
        partner_contact = self.env.ref("ps_crm.lead_main_partner_contact")
        operating_unit = self.env.ref("operating_unit.main_operating_unit")
        with Form(self.lead) as lead_form:
            lead_form.partner_id = partner
            self.assertEqual(lead_form.partner_contact_id, partner_contact)
            self.assertEqual(lead_form.contact_name, partner_contact.name)
            lead_form.partner_id = partner_contact
            self.assertFalse(lead_form.partner_contact_id)
            self.assertFalse(lead_form.contact_name)
            lead_form.operating_unit_id = operating_unit
