from odoo.tests.common import Form, TransactionCase


class TestPsLandingPage(TransactionCase):
    def test_ps_landing_page_flow(self):
        with Form(
            self.env["hr.employee.landing_page"]
            .with_user(self.env.ref("base.user_demo"))
            .create({})
        ) as page_form:
            page = page_form.save()
        page.action_view_timesheet()
        page.action_view_leaves_dashboard()
        page.action_view_timesheet_tree()
        page.action_view_analytic_tree()
