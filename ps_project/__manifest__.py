# Copyright 2018 Willem Hulshof The Open Source Company (www.tosc.nl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "PS Projects",
    "summary": "Projects - extended",
    "author": "The Open Source Company",
    "website": "http://www.tosc.nl",
    "category": "Project",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "depends": [
        "project",
        "operating_unit",
        "analytic",
        "hr_timesheet_sheet",
        # TODO: migrate the OU==analytic account part of this
        # "invoice_line_revenue_distribution_operating_unit",
        "account_operating_unit",
        "account_fiscal_month",
    ],
    "data": [
        "security/ps_security.xml",
        "security/ir.model.access.csv",
        "views/project_invoicing_properties.xml",
        "views/project_project.xml",
        "views/project_task.xml",
        "views/menuitem.xml",
    ],
    "demo": [
        "demo/project_project.xml",
    ],
}
