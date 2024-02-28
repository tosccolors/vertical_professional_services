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
