# Copyright 2024 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import _, fields, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    ps_contracted_line_count = fields.Integer(
        compute="_compute_ps_contracted_line_count"
    )
    ps_contracted_line_ids = fields.One2many(
        "ps.contracted.line", "project_id", string="Contracted lines"
    )

    def _compute_ps_contracted_line_count(self):
        for this in self:
            this.ps_contracted_line_count = len(this.ps_contracted_line_ids)

    def open_ps_contracted_lines(self, products=None, date_from=None, date_to=None):
        PsContractedLine = self.env["ps.contracted.line"]
        Product = self.env["product.product"]
        for this in self:
            contracted = this.ps_contracted_line_ids
            if not products and (
                not contracted.check_access_rights("create", False) or contracted
            ):
                continue
            for task in this.task_ids:
                for product in products or Product.search(
                    PsContractedLine._fields["product_id"].get_domain_list(
                        PsContractedLine
                    )
                ):
                    existing = contracted.filtered_domain(
                        [
                            ("project_id", "=", this.id),
                            ("task_id", "=", task.id),
                            ("product_id", "=", product.id),
                            ("date_from", "=", date_from),
                            ("date_to", "=", date_to),
                        ]
                    )
                    if existing:
                        continue
                    PsContractedLine.create(
                        {
                            "project_id": this.id,
                            "task_id": task.id,
                            "product_id": product.id,
                            "date_from": date_from,
                            "date_to": date_to,
                        }
                    )

        return {
            "type": "ir.actions.act_window",
            "name": _("Contract entry"),
            "res_model": PsContractedLine._name,
            "domain": [("project_id", "in", self.ids)]
            + (
                [
                    "|",
                    ("date_from", "=", date_from),
                    ("date_from", "=", False),
                    "|",
                    ("date_to", "=", date_to),
                    ("date_to", "=", False),
                ]
                if date_from and date_to
                else []
            ),
            "views": [
                (self.env.ref("ps_planning.view_ps_contracted_line_tree").id, "list")
            ],
            "context": {
                "default_project_id": self[:1].id,
                "default_date_from": date_from,
                "default_date_to": date_from,
            }
            if len(self) == 1
            else {},
        }
