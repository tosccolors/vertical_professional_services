# Copyright 2018 Willem Hulshof The Open Source Company (www.tosc.nl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Professional Services Employee Directory",
    "summary": "HRM - extended",
    "author": "The Open Source Company",
    "website": "http://www.tosc.nl",
    "category": "Human Resources",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "depends": [
        "account_payment_mode",
        "web_domain_field",
        "account_payment_partner",
        "base_user_role",
        "hr",
        "hr_contract",
        "hr_employee_firstname",
        "hr_employee_service_contract",
        "hr_holidays",
        "operating_unit",
        "partner_firstname",
    ],
    "data": [
        "views/hr_employee.xml",
        "wizard/hr_employee_wizard_view.xml",
        "security/ir.model.access.csv",
    ],
    "assets": {
        "web.assets_backend": [
            "/ps_hr/static/src/js/employee_wizard.js",
        ],
    },
}
