# Copyright 2018 - 2023 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class CrmMonthlyRevenue(models.Model):
    _name = "crm.monthly.revenue"
    _description = "Monthly revenue"
    _rec_name = "month"

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        ctx = self.env.context.copy()
        if "default_lead_id" in ctx:
            crm_obj = self.env["crm.lead"].browse(ctx["default_lead_id"])
            latest_revenue_date = (
                crm_obj.latest_revenue_date
                or crm_obj.start_date
                or datetime.now().strftime("%Y-%m-%d")
            )
            if latest_revenue_date:
                latest_revenue_date = datetime.strptime(
                    latest_revenue_date, "%Y-%m-%d"
                ).date()
                upcoming_month_end_date = (
                    latest_revenue_date + relativedelta(months=2)
                ).replace(day=1) - timedelta(days=1)
                res["date"] = upcoming_month_end_date.strftime("%Y-%m-%d")
                res["latest_revenue_date"] = latest_revenue_date.strftime("%Y-%m-%d")
        return res

    date = fields.Date("Date", required=True)
    year = fields.Many2one("date.range", string="Year")
    month = fields.Many2one("date.range", string="Month")
    no_of_days = fields.Char(string="Duration")
    latest_revenue_date = fields.Date("Latest Revenue Date")
    weighted_revenue = fields.Float("Weighted Revenue", required=True)
    expected_revenue = fields.Float("Expected Revenue", required=True)
    percentage = fields.Float(string="Probability")
    lead_id = fields.Many2one(
        "crm.lead", string="Opportunity", ondelete="cascade", required=True
    )
    company_currency = fields.Many2one(
        string="Currency",
        related="lead_id.company_id.currency_id",
        readonly=True,
        comodel_name="res.currency",
        store=True,
    )
    user_id = fields.Many2one(
        related="lead_id.user_id",
        comodel_name="res.users",
        string="Salesperson",
        index=True,
        store=True,
    )
    computed_line = fields.Boolean(string="Computed line")
    project_id = fields.Many2one(
        "project.project", related="lead_id.project_id", string="Project", store=True
    )
    partner_id = fields.Many2one(
        "res.partner", related="lead_id.partner_id", string="Customer", store=True
    )
    industry_id = fields.Many2one(
        "res.partner.industry",
        related="lead_id.industry_id",
        string="Main Sector",
        store=True,
    )
    department_id = fields.Many2one(
        "hr.department", related="lead_id.department_id", string="Practice", store=True
    )
    operating_unit_id = fields.Many2one(
        "operating.unit",
        related="lead_id.operating_unit_id",
        string="Operating Unit",
        store=True,
    )

    def calculate_weighted_revenue(self, percentage):
        self.ensure_one()
        weighted_revenue = 0
        if self.expected_revenue:
            weighted_revenue = self.expected_revenue * percentage / 100
        return weighted_revenue

    @api.onchange("expected_revenue", "percentage", "lead_id")
    def onchagne_expected_revenue(self):
        self.percentage = self.lead_id.probability
        self.weighted_revenue = self.calculate_weighted_revenue(self.percentage)

    @api.onchange("date")
    def onchange_date(self):
        ctx = self.env.context.copy()
        lead_id = ctx.get("default_lead_id")
        date = datetime.strptime(self.date, "%Y-%m-%d").date()
        date_range = self.env["date.range"]

        if date and self.latest_revenue_date:
            lrd = datetime.strptime(self.latest_revenue_date, "%Y-%m-%d").date()
            if date < lrd or (date.month == lrd.month and date.year == lrd.year):
                date = self.date = (lrd + relativedelta(months=2)).replace(
                    day=1
                ) - timedelta(days=1)

        if date:
            days = " days (" if date.day > 1 else " day ("
            self.no_of_days = (
                str(date.day)
                + days
                + str(1)
                + "-"
                + str(date.day)
                + " "
                + str(date.strftime("%B"))
                + ")"
            )
            company = self.lead_id.company_id.id or self.env.user.company_id.id
            common_domian = [
                ("date_start", "<=", self.date),
                ("date_end", ">=", self.date),
                ("company_id", "=", company),
            ]
            month = date_range.search(
                common_domian + [("type_id.fiscal_month", "=", True)]
            )
            self.month = month.id
            year = date_range.search(
                common_domian + [("type_id.fiscal_year", "=", True)]
            )
            self.year = year.id

        if lead_id and date:
            lead = self.env["crm.lead"].browse([lead_id])
            self.env.cr.execute(
                """
                            UPDATE %s SET latest_revenue_date = %s
                            WHERE id = %s
                  """,
                (lead._table, date, lead_id),
            )
