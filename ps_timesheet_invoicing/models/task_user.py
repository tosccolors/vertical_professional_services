# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, exceptions, fields, models
from odoo.osv.expression import TRUE_LEAF


class TaskUser(models.Model):
    _name = "task.user"
    _description = "Mapping of task and user to fees, products per time"

    @api.depends("fee_rate", "ic_fee_rate")
    def _compute_margin(self):
        for this in self:
            this.margin = this.fee_rate - this.ic_fee_rate

    @api.model
    def _default_product(self):
        if self.user_id.employee_ids.product_id:
            return self.user_id.employee_ids.product_id.id

    @api.model
    def _get_category_domain(self):
        return [
            (
                "categ_id",
                "=",
                self.env.ref("ps_timesheet_invoicing.product_category_fee_rate").id,
            )
        ]

    @api.depends("task_id", "user_id", "from_date")
    def _compute_last_valid_fee_rate(self):
        for this in self:
            task_id = this.task_id.id
            user_id = this.user_id.id
            task_user = self.search(
                [("task_id", "=", task_id), ("user_id", "=", user_id)],
                order="from_date desc",
                limit=1,
            )
            this.last_valid_fee_rate = task_user == this

    project_id = fields.Many2one(
        related="task_id.project_id",
        comodel_name="project.project",
        string="Project",
        store=True,
    )
    task_id = fields.Many2one("project.task", string="Task", required=True)
    user_id = fields.Many2one("res.users", string="Consultant", required=True)
    product_id = fields.Many2one(
        "product.product",
        string="Fee rate Product",
        default=_default_product,
        domain=_get_category_domain,
        context=lambda env: {
            "default_categ_id": env.ref(
                "ps_timesheet_invoicing.product_category_fee_rate", False
            ).id
        },
        required=True,
    )
    fee_rate = fields.Float(
        string="Fee Rate",
        required=True,
    )
    ic_fee_rate = fields.Float(
        string="Intercompany Fee Rate",
    )
    margin = fields.Float(
        compute="_compute_margin",
        string="Margin",
    )
    name = fields.Char(compute="_compute_name")
    from_date = fields.Date(
        string="From Date",
        required=True,
    )
    last_valid_fee_rate = fields.Boolean(
        compute="_compute_last_valid_fee_rate", string="Last Valid Fee Rate", store=True
    )
    cost_rate = fields.Float(
        string="Cost Rate",
    )

    @api.depends("user_id", "product_id")
    def _compute_name(self):
        """x2x tracking code of project in core expects a name field on x2many fields"""
        for this in self:
            this.name = _("%s: %s") % (this.user_id.display_name, this.product_id.name)

    @api.onchange("user_id")
    def onchange_user_id(self):
        self.product_id = False
        self.fee_rate = 0
        if self.user_id:
            emp = self.env["hr.employee"].search([("user_id", "=", self.user_id.id)])
            if emp:
                product = emp.product_id
                self.product_id = product.id
                self.fee_rate = product.lst_price

    @api.constrains("task_id", "from_date", "user_id")
    def _check_task_user_date(self):
        for this in self:
            if (
                self.search_count(
                    [
                        ("task_id", "=", this.task_id.id),
                        ("user_id", "=", this.user_id.id),
                        ("product_id", "=", this.product_id.id),
                        ("from_date", "=", this.from_date),
                    ]
                )
                > 1
            ):
                raise exceptions.ValidationError(
                    _("The combination of task, user and date must be unique")
                )

    def get_task_user_obj(self, task_id, user_id, date=None):
        taskUserObj = self.search(
            [
                ("from_date", "<=", date) if date else TRUE_LEAF,
                ("task_id", "=", task_id),
                ("user_id", "=", user_id),
            ],
            order="from_date Desc",
            limit=1,
        )
        if not taskUserObj:
            task = self.env["project.task"].browse(task_id)
            standard_task = task.project_id.standard_task_id
            if standard_task and task != standard_task:
                taskUserObj = self.get_task_user_obj(standard_task.id, user_id, date)
        return taskUserObj

    def update_ps_time_lines(self):
        next_fee_rate_date = self.search(
            [
                ("from_date", ">", self.from_date),
                ("task_id", "=", self.task_id.id),
                ("user_id", "=", self.user_id.id),
            ],
            order="from_date",
            limit=1,
        )

        ptl_obj = self.env["ps.time.line"]
        ptl_domain = [
            ("task_id", "=", self.task_id.id),
            ("user_id", "=", self.user_id.id),
            (
                "state",
                "not in",
                ["invoiced", "invoiced-by-fixed", "write_off", "expense-invoiced"],
            ),
            ("product_uom_id", "=", self.env.ref("uom.product_uom_hour").id),
            ("date", ">=", self.from_date),
        ]

        if next_fee_rate_date:
            ptl_domain += [("date", "<", next_fee_rate_date.from_date)]
        ptl_query_line = ptl_obj._where_calc(ptl_domain)
        ptl_tables, ptl_where_clause, ptl_where_clause_params = ptl_query_line.get_sql()

        list_query = """
                WITH ptl AS (
                    SELECT
                       id, unit_amount
                    FROM
                       {0}
                    WHERE {1}
                )
                UPDATE {0}
                SET line_fee_rate = {2}, amount = (- ptl.unit_amount * {2}),
                product_id = {3}
                FROM ptl WHERE {0}.id = ptl.id
        """.format(
            ptl_tables, ptl_where_clause, self.fee_rate, self.product_id.id
        )
        self.env.cr.execute(list_query, ptl_where_clause_params)
        return True

    @api.model
    def create(self, vals):
        res = super().create(vals)
        res.update_ps_time_lines()
        return res

    def write(self, vals):
        result = super().write(vals)
        for res in self:
            res.update_ps_time_lines()
        return result
