# Copyright 2018 - 2023 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CRMRevenueSplit(models.Model):
    _name = "crm.revenue.split"

    lead_id = fields.Many2one("crm.lead", string="Opportunity", ondelete="cascade")

    department_id = fields.Many2one(
        "hr.department", related="lead_id.department_id", string="Practice", store=True
    )
    partner_id = fields.Many2one(
        "res.partner", related="lead_id.partner_id", string="Customer", store=True
    )
    project_id = fields.Many2one(
        "project.project", related="lead_id.project_id", string="Project", store=True
    )
    user_id = fields.Many2one(
        "res.users", related="lead_id.user_id", string="Salesperson", store=True
    )
    name = fields.Char(related="lead_id.name", string="Opportunity Name", store=True)
    operating_unit_id = fields.Many2one(
        "operating.unit",
        related="lead_id.operating_unit_id",
        string="Operating Unit",
        store=True,
    )
    month = fields.Many2one("date.range", string="Month")
    total_revenue = fields.Float("Total Revenue")
    total_revenue_per = fields.Float("Total Revenue %")
    ps_blue_bv_amount = fields.Float(
        oldname="mangnus_blue_bv_amount", string="Magnus Blue B.V."
    )
    ps_blue_bv_per = fields.Float(
        oldname="mangnus_blue_bv_per", string="Magnus Blue B.V. %"
    )
    ps_red_bv_amount = fields.Float(
        oldname="mangnus_red_bv_amount", string="Magnus Red B.V."
    )
    ps_red_bv_per = fields.Float(
        oldname="mangnus_red_bv_per", string="Magnus Red B.V. %"
    )
    ps_green_bv_amount = fields.Float(
        oldname="mangnus_green_bv_amount", string="Magnus Green B.V."
    )
    ps_green_bv_per = fields.Float(
        oldname="mangnus_green_bv_per", string="Magnus Green B.V. %"
    )
    ps_black_bv_amount = fields.Float(
        oldname="mangnus_black_bv_amount", string="Magnus Black B.V."
    )
    ps_black_bv_per = fields.Float(
        oldname="mangnus_black_bv_per", string="Magnus Black B.V. %"
    )

    @api.constrains(
        "ps_blue_bv_per", "ps_red_bv_per", "ps_green_bv_per", "ps_black_bv_per"
    )
    def _check_dates(self):
        total_per = (
            self.ps_blue_bv_per
            + self.ps_red_bv_per
            + self.ps_green_bv_per
            + self.ps_black_bv_per
        )
        if int(total_per) > 100:
            raise ValidationError(_("Total Percentage should be equal to 100"))

    @api.onchange("ps_black_bv_per")
    def onchange_ps_black_perc(self):
        """Magnus Green B.V."""
        total_per = (
            self.ps_blue_bv_per
            + self.ps_red_bv_per
            + self.ps_green_bv_per
            + self.ps_black_bv_per
        )
        if int(total_per) > 100:
            self.ps_black_bv_per = 0.0
            raise ValidationError(_("Total Percentage should be equal to 100"))
        # if self.ps_black_bv_per > 0.0:
        self.ps_black_bv_amount = self.total_revenue * (self.ps_black_bv_per / 100)

    @api.onchange("ps_black_bv_amount")
    def onchange_ps_black_amount(self):
        """Magnus Green B.V."""
        self.ps_black_bv_per = self.ps_black_bv_amount * (100 / self.total_revenue)

    @api.onchange("ps_blue_bv_per")
    def onchange_ps_blue_per(self):
        """for Magnus Blue B.V"""
        total_per = (
            self.ps_blue_bv_per
            + self.ps_red_bv_per
            + self.ps_green_bv_per
            + self.ps_black_bv_per
        )
        if int(total_per) > 100:
            self.ps_blue_bv_per = 0.0
            raise ValidationError(_("Total Percentage should be equal to 100"))
        # if self.ps_blue_bv_per > 0:
        self.ps_blue_bv_amount = self.total_revenue * (self.ps_blue_bv_per / 100)

    @api.onchange("ps_blue_bv_amount")
    def onchange_ps_blue_amount(self):
        """for Magnus Blue B.V"""
        if self.ps_blue_bv_amount > 0.0:
            self.ps_blue_bv_per = self.ps_blue_bv_amount * (100 / self.total_revenue)

    @api.onchange("ps_red_bv_per")
    def onchange_ps_red_per(self):
        total_per = (
            self.ps_blue_bv_per
            + self.ps_red_bv_per
            + self.ps_green_bv_per
            + self.ps_black_bv_per
        )
        if int(total_per) > 100:
            self.ps_red_bv_per = 0.0
            raise ValidationError(_("Total Percentage should be equal to 100"))
        self.ps_red_bv_amount = self.total_revenue * (self.ps_red_bv_per / 100)

    @api.onchange("ps_red_bv_amount")
    def onchange_ps_red_amount(self):
        """for Magnus Red B.V"""
        if self.ps_red_bv_amount > 0:
            self.ps_red_bv_per = self.ps_red_bv_amount * (100 / self.total_revenue)

    @api.onchange("ps_green_bv_per")
    def onchange_ps_green_per(self):
        """Magnus Green B.V."""
        total_per = (
            self.ps_blue_bv_per
            + self.ps_red_bv_per
            + self.ps_green_bv_per
            + self.ps_black_bv_per
        )
        if int(total_per) > 100:
            self.ps_green_bv_per = 0.0
            raise ValidationError(_("Total Percentage should be equal to 100"))

        # if self.ps_green_bv_per > 0.0:
        self.ps_green_bv_amount = self.total_revenue * (self.ps_green_bv_per / 100)

    @api.onchange("ps_green_bv_amount")
    def onchange_ps_green_amount(self):
        """Magnus Green B.V."""
        if self.ps_green_bv_amount > 0:
            self.ps_green_bv_per = self.ps_green_bv_amount * (100 / self.total_revenue)
