# Copyright 2018 Willem Hulshof The Open Source Company (www.tosc.nl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "PS Projects",
    "summary": "Projects - extended",
    "author": "The Open Source Company",
    "website": "http://www.tosc.nl",
    "category": "Project",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "depends": [
        "project",
        "operating_unit",
        "analytic",
        "hr_timesheet_sheet",
        "invoice_line_revenue_distribution_operating_unit",
    ],
    "data": [
        "security/ps_security.xml",
        "security/ir.model.access.csv",
        "views/project_views.xml",
        "views/menuitem.xml",
    ],
    "demo": [
        "demo/project_project.xml",
    ],
}
