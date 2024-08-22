# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Professional Services customization to the asset equipment link",
    "summary": "Create equipment when validating an invoice with assets",
    "version": "14.0.1.0.0",
    "website": "http://www.tosc.nl",
    "author": "The Open Source Company",
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "ps_equipment",
        "account_asset_operating_unit",
    ],
    "data": [
        "views/account_asset_views.xml",
        "views/maintenance_equipment_view.xml",
        "views/account_asset_profile_views.xml",
        "views/account_move.xml",
    ],
    "demo": [
        "demo/maintenance_equipment_category.xml",
        "demo/account_asset_profile.xml",
    ],
}
