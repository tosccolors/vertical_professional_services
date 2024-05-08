def migrate(cr, version=None):
    cr.execute("update hr_expense set state='approved' where state = 'revise'")
    cr.execute(
        "update hr_expense_sheet set state='approve' "
        "where state in ('revise', 'approve_partner')"
    )
