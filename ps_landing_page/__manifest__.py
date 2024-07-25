{
    "name": "Employee Landing Page",
    "summary": "Employee Landing Page",
    "author": "The Open Source Company",
    "website": "http://www.tosc.nl",
    "category": "Report",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "depends": ["ps_timesheet_invoicing", "ps_holidays", "ps_expense"],
    "data": [
        "security/ps_security.xml",
        "security/ir.model.access.csv",
        "views/hr_employee_landing_page_views.xml",
    ],
    "demo": [
        "demo/res_groups.xml",
    ],
    "installable": True,
}
