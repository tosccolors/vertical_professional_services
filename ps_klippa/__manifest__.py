# Copyright 2018 Willem Hulshof The Open Source Company (www.tosc.nl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "PS Klippa",
    "summary": "This module creates a cron job to update expenses.",
    "author": "The Open Source Company",
    "license": "AGPL-3",
    "website": "http://www.tosc.nl",
    "category": "Human Resources",
    "version": "16.0.1.0.0",
    "depends": ["ps_expense"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "data/res_users.xml",
    ],
    "demo": [
        "demo/hr_expense.xml",
    ],
    "pre_init_hook": "pre_init_hook",
}
