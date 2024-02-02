# Copyright 2018 Willem Hulshof The Open Source Company (www.tosc.nl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Professional Services Employee Directory',

    'summary': "HRM - extended",

    'description': """
Human Resources Management - extended
=====================================

This module adds the following fields:\n
In the object hr.employee on the tab 'HR Settings' under the heading 'Duration of Service' creates three new date fields called: 'Official Date of Employment', 'Temporary Contract' and 'End Date of Employment'. These first two date fields do not affect the 'lengt_of_service' field, the end-date-of-employment stops the counting of the length of service from the 'initial_employment_date'.\n
In the object hr.employee on the tab 'Public Information' under the heading 'Position' creates a new boolean called 'External'. If the boolean is set to true a new character field called 'Supplier' becomes visible.\n
In the object hr.employee on the tab 'Public Information' under the heading 'Position' creates a new m2o selection field of hr.employee called 'Mentor' similar to Manager (parent_id) and Coach (coach_id).\n
In the object hr.employee on the tab 'HR Settings' under the heading 'Leaves' creates two new integer fields called 'Parttime' and 'Allocated Leaves'.\n
In the object hr.employee on the tab 'Personal Information' under the heading 'Contact Information' creates a new character field called 'Emergency Contact'.\n
In the object hr.employee creates a new tab called 'Description' and on this tab creates a new text field called 'Description'.\n
In the object hr. employee on the tab 'HR Settings' under the heading 'Status' creates a new character field called 'Pass Number Alarm'.
""",

    'author': "TOSC",
    'website': "http://www.tosc.nl",

    'category': 'Human Resources',
    'version': '14.0.1.0.0',

    'depends': [
        'account_payment_mode',
        'account_payment_partner',
        'base_user_role',
        'hr',
        'hr_contract',
        'hr_employee_firstname',
        'hr_employee_service_contract',
        'hr_holidays',
        'operating_unit',
        'partner_firstname',
    ],

    'data': [
        'views/hr_views.xml',
        'views/templates.xml',
        'wizard/hr_employee_wizard_view.xml',
        'security/ir.model.access.csv',
    ],
}
