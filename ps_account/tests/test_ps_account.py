from odoo.addons.ps_timesheet_invoicing.tests import test_ps_timesheet_invoicing


class TestPsAccount(test_ps_timesheet_invoicing.TestPsTimesheetInvoicing):
    # squelch all tests but the invoicing one
    def test_00_timesheet(self):
        pass

    def test_01_invoicing2(self):
        pass

    def test_02_change_chargecode(self):
        pass

    def test_03_invoicing_properties(self):
        pass
