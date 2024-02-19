# Copyright 2018 Willem Hulshof The Open Source Company (www.tosc.nl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Professional Services CRM",
    "summary": "Opportunities - Extended",
    "license": "AGPL-3",
    "author": "The Open Source Company",
    "website": "http://www.tosc.nl",
    "category": "Sales",
    "version": "14.0.1.0.0",
    "depends": [
        "base",
        "uom",
        "crm",
        "crm_industry",
        "project",
        "operating_unit",
        "hr",
        "utm",
        "date_range",
        "web_notify",
        "sale",
    ],
    "data": [
        "security/crm_security.xml",
        "security/ir.model.access.csv",
        "views/crm_lead_views.xml",
        "views/hr_department.xml",
    ],
    "demo": [
        "demo/hr_department.xml",
        "demo/res_partner.xml",
    ],
    "installable": True,
}
