# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Partner Professional Services Relations",
    "version": "14.0.1.0.0",
    "author": "The Open Source Company",
    "complexity": "normal",
    "category": "Customer Relationship Management",
    "license": "AGPL-3",
    "depends": [
        "partner_multi_relation",
        "ps_account",
        "ps_timesheet_invoicing",
        "account_invoice_merge",
    ],
    "data": [
        "data/res_partner_relation_type.xml",
        "data/res_partner_category.xml",
        "views/res_partner_relation_all.xml",
        "views/project_view.xml",
        "views/account_invoice_view.xml",
    ],
    "demo": [
        "demo/res_partner.xml",
        "demo/res_partner_relation.xml",
    ],
    "installable": True,
}
