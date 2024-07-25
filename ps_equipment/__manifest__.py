{
    "name": "Professional Services - Equipments addon",
    "version": "14.0.1.0.0",
    "author": "The Open Source Company",
    "website": "http://www.tosc.nl",
    "category": "Maintenance",
    "depends": ["hr_maintenance"],
    "summary": "Equipments, Assets, Internal Hardware, Allocation Tracking",
    "data": [
        "security/security.xml",
        "views/maintenance_equipment.xml",
        "views/maintenance_equipment_warranty_category.xml",
        "views/menu.xml",
        "security/ir.model.access.csv",
    ],
    "license": "AGPL-3",
    'installable': False,
    'application': True,
}
