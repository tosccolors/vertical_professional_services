from odoo import exceptions
from odoo.tests.common import Form, TransactionCase
from odoo.tools.misc import mute_logger

from odoo.addons.ps_timesheet_invoicing.hooks import _init_fleet_vehicle_driver


class TestHrTimesheet(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project = self.env.ref("project.project_project_2")
        self.ps_line = self.env.ref(
            "ps_timesheet_invoicing.time_line_demo_user_2023_12_18"
        )
        self.env.company.timesheet_sheet_review_policy = "timesheet_manager"
        self.user = self.env.ref("base.user_demo")
        # demo user by default has too much permissions for this test to be sensible
        self.user.write(
            {
                "groups_id": [
                    (3, self.env.ref("hr_timesheet.group_hr_timesheet_approver").id),
                    (3, self.env.ref("project.group_project_manager").id),
                    (3, self.env.ref("hr.group_hr_user").id),
                    (3, self.env.ref("hr_contract.group_hr_contract_manager").id),
                    (4, self.env.ref("project.group_project_user").id),
                ]
            }
        )
        _init_fleet_vehicle_driver(self.env.cr)
        self.env["fleet.vehicle"].search([]).fleet_vehicle_driver_ids.unlink()
        self.env["fleet.vehicle"].search([], limit=1).write(
            {
                "fleet_vehicle_driver_ids": [
                    (
                        0,
                        0,
                        {
                            "driver_id": self.user.partner_id.id,
                            "date_start": "2020-01-06",
                        },
                    ),
                ],
            }
        )

    def test_timesheet(self):
        """Test creating and submitting timesheets"""
        task = self.project.task_ids[:1]
        task.standard = True
        # demo user by default has too much permissions for this test to be sensible
        self.env.ref("fleet.vehicle_1").driver_id = self.user.partner_id
        self.project.message_partner_ids += self.user.partner_id
        sheet = self.env["hr_timesheet.sheet"].with_user(self.user).create({})
        sheet.add_line_project_id = self.project
        sheet.onchange_add_project_id()
        self.assertEqual(sheet.add_line_task_id, task)
        sheet.button_add_line()
        sheet.with_context(sheet_write=True)._compute_line_ids()
        with Form(sheet) as sheet_form:
            for i in range(7):
                with sheet_form.line_ids.edit(i) as day_line:
                    day_line.unit_amount = 8
            with sheet_form.line_ids.edit(3) as day_line:
                day_line.unit_amount = 10
            sheet_form.end_mileage = 42
        self.assertEqual(sheet.employee_id, self.user.employee_id)
        self.assertEqual(sheet.mapped("timesheet_ids.employee_id"), self.user.employee_id)
        action = self.env["hr.timesheet.current.open"].with_user(self.user).open_timesheet()
        self.assertEqual(action["res_id"], sheet.id)
        sheet.action_timesheet_confirm()
        with self.assertRaises(exceptions.UserError):
            sheet.action_timesheet_done()
        self.user.groups_id += self.env.ref("hr_timesheet.group_hr_timesheet_approver")
        with self.assertRaises(exceptions.UserError):
            sheet.action_timesheet_done()
        self.user.groups_id += self.env.ref(
            "ps_timesheet_invoicing.group_timesheet_manager"
        )
        sheet.action_timesheet_done()
        sheet.action_timesheet_draft()
        sheet.action_timesheet_confirm()
        sheet_as_admin = sheet.with_user(self.env.ref("base.user_admin"))
        sheet_as_admin.action_timesheet_refuse()
        sheet.action_timesheet_confirm()
        sheet_as_admin.action_timesheet_done()
        sheet_as_admin.action_timesheet_draft()
        sheet.action_timesheet_confirm()
        sheet_as_admin.action_timesheet_done()
        self.assertEqual(sheet.overtime_hours, 18)
        self.assertEqual(sheet.overtime_hours_delta, 18)
        self.env.flush_all()
        next_sheet = sheet.create({})
        next_sheet.duplicate_last_week()
        self.assertEqual(next_sheet.employee_id, self.user.employee_id)
        self.assertEqual(
            next_sheet.mapped("timesheet_ids.employee_id"), self.user.employee_id
        )
        with Form(next_sheet) as sheet_form:
            for i in range(7):
                with sheet_form.line_ids.edit(i) as day_line:
                    day_line.unit_amount = 8
        with self.assertRaisesRegex(
            exceptions.ValidationError, "End Mileage cannot be lower"
        ):
            next_sheet.action_timesheet_confirm()
        next_sheet.end_mileage = 100
        next_sheet.timesheet_ids[:1].kilometers = 16
        next_sheet.action_timesheet_confirm()
        self.assertEqual(next_sheet.overtime_hours, 16)
        self.assertEqual(next_sheet.overtime_hours_delta, 16)
        next_sheet.action_timesheet_done()

    def test_02_change_chargecode(self):
        wizard = (
            self.env["change.chargecode"]
            .with_context(
                active_id=self.ps_line.id,
                active_ids=self.ps_line.ids,
                active_model=self.ps_line._name,
            )
            .create({})
        )
        with Form(wizard) as wizard_form:
            project = self.env["project.project"].search(
                [("id", "!=", self.ps_line.project_id.id)],
                limit=1,
            )
            wizard_form.project_id = project
            wizard_form.task_id = project.task_ids[:1]

        line_max = self.env["ps.time.line"].search([], limit=1, order="id desc")
        wizard.post()

        reverse_line, new_line = self.env["ps.time.line"].search(
            [("id", ">", line_max.id)], order="id asc"
        )
        self.assertEqual(self.ps_line.unit_amount, -reverse_line.unit_amount)

    def test_03_invoicing_properties(self):
        """Test invoicing properties form"""
        km_line = self.ps_line.copy(
            {
                "product_uom_id": self.env.ref("uom.product_uom_km").id,
                "non_invoiceable_mileage": True,
            }
        )
        with Form(self.project.invoice_properties) as properties_form:
            properties_form.invoice_mileage = True
        self.assertFalse(km_line.non_invoiceable_mileage)

    def test_99_delay(self):
        """Test delaying time lines"""
        wizard = (
            self.env["time.line.status"].with_context(
                active_id=self.ps_line[:1].id,
                active_ids=self.ps_line[:1].ids,
                active_model=self.ps_line._name,
            )
        ).create({})

        with Form(wizard) as wizard_form:
            wizard_form.name = "delayed"
            wizard_form.description = "hello world"

        move_max = self.env["account.move"].search([], limit=1, order="id desc")
        with mute_logger("odoo.addons.queue_job.delay"):
            wizard.with_context(queue_job__no_delay=True).ps_invoice_lines()

        self.assertEqual(self.ps_line.state, "delayed")
        reversed_move, move = self.env["account.move"].search(
            [("id", ">", move_max.id)]
        )
        self.assertEqual(reversed_move.reversed_entry_id, move)
        self.assertEqual(move.reversal_move_id, reversed_move)
