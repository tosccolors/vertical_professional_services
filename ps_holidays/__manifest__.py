# Copyright 2018 Willem Hulshof The Open Source Company (www.tosc.nl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Professional Services Leave Management",
    "summary": "Leave Management - extended",
    "author": "The Open Source Company",
    "website": "http://www.tosc.nl",
    "category": "Human Resources",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "depends": [
        "base",
        "project",
        "hr_timesheet",
        "hr_timesheet_sheet",
        "hr_holidays",
        "ps_timesheet_invoicing",
    ],
    "data": [
        "views/project_holiday_views.xml",
        "views/hr_holiday_status_view.xml",
    ],
    "demo": [
        "demo/project_project.xml",
        "demo/project_task.xml",
        "demo/hr_leave_type.xml",
    ],
    "installable": True,
}
