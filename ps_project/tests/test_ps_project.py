from odoo.tests.common import Form, TransactionCase


class TestPsProject(TransactionCase):
    def test_project_flow(self):
        tag = self.env.ref("project.project_tags_00")
        with Form(self.env["project.project"]) as project_form:
            project_form.name = "test project"
            project_form.tag_ids.add(tag)
            project = project_form.save()
        with Form(
            self.env["project.task"].with_context(
                active_model=project._name, active_id=project.id, active_ids=project.ids
            )
        ) as task_form:
            self.assertEqual(len(task_form.tag_ids), 1)
            task_form.name = "test task"
            task_form.description = "<p>hello <span>world</span></p>"
            task_form.project_id = project.copy(
                {"tag_ids": self.env.ref("project.project_tags_01")}
            )
            self.assertEqual(len(task_form.tag_ids), 2)
            task = task_form.save()
        self.assertEqual(task.parsed_description, "hello world")
        task.description = False
        self.assertFalse(task.parsed_description)

    def test_name_search(self):
        result = self.env["project.project"].name_search("4")
        self.assertIn(
            self.env.ref("project.project_project_2").id, map(lambda x: x[0], result)
        )
        result = self.env["project.project"].name_search("4", limit=None)
        self.assertIn(
            self.env.ref("project.project_project_2").id, map(lambda x: x[0], result)
        )
        result = self.env["project.project"].name_search(
            "4", limit=None, args=[("name", "=", "nonexistent")]
        )
        self.assertFalse(result)

    def test_project_invoicing_properties(self):
        with Form(self.env["project.invoicing.properties"]) as form:
            form.name = "test"
            form.actual_time_spent = True
            with self.assertRaises(AssertionError):
                form.fixed_amount = True
            form.actual_time_spent = False
            form.fixed_amount = True
            self.assertFalse(form.actual_time_spent)
            form.fixed_amount = None
            form.actual_time_spent = True
            self.assertFalse(form.fixed_amount)

    def test_partner_sync(self):
        partner = self.env.ref("base.res_partner_1")
        project = self.env["project.project"].create(
            {"name": "project", "allow_timesheets": True, "partner_id": partner.id}
        )
        self.assertEqual(project.analytic_account_id.partner_id, partner)
        project.partner_id = False
        self.assertFalse(project.analytic_account_id.partner_id)
        project.analytic_account_id.partner_id = partner
        self.assertEqual(project.partner_id, partner)
        project.analytic_account_id.partner_id = False
        self.assertFalse(project.partner_id)
