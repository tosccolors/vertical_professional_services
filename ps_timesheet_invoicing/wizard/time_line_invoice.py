import logging
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.queue_job.exception import FailedJobError

_logger = logging.getLogger(__name__)


class TimeLineStatus(models.TransientModel):
    _name = "time.line.status"
    _description = "Timeline Status"

    name = fields.Selection(
        [
            ("invoiceable", "To be invoiced"),
            ("delayed", "Delayed"),
            ("write-off", "Write-Off"),
            ("open", "Confirmed"),
        ],
        string="Lines to be",
    )
    wip = fields.Boolean("WIP")
    wip_percentage = fields.Float(
        "WIP Percentage",
        default=100,
    )
    description = fields.Char("Description")
    wip_month_ids = fields.Many2many(
        "date.range", string="Month of Timeline or last Wip Posting"
    )

    def ps_invoice_lines(self):
        context = self.env.context.copy()
        ptl_ids = context.get("active_ids", [])
        ptl_lines = self.env["ps.time.line"].browse(ptl_ids)
        status = str(self.name)
        not_lookup_states = [
            "draft",
            "progress",
            "invoiced",
            "delayed",
            "write-off",
            "change-chargecode",
        ]
        entries = ptl_lines.filtered(lambda a: a.state not in not_lookup_states)
        no_invoicing_property_entries = entries.filtered(
            lambda al: not al.project_id.invoice_properties
        )
        if no_invoicing_property_entries and status == "invoiceable":
            project_names = ",".join(
                [al.project_id.name for al in no_invoicing_property_entries]
            )
            raise UserError(
                _("Project(s) %s doesn't have invoicing properties.") % project_names
            )
        # TODO: field doesn't exist on ps.time.line?
        # entries.write({'wip_percentage': self.wip_percentage})
        if entries:
            self.env.cr.execute(
                "UPDATE ps_time_line SET state=%s WHERE id IN %s",
                (status, tuple(entries.ids)),
            )
            self.env.cache.invalidate()
            if status == "delayed" and self.wip:
                notupdatestate = {line.id: line.state for line in ptl_lines}
                self.with_delay(
                    eta=datetime.now(), description="WIP Posting"
                ).prepare_account_move(ptl_ids, notupdatestate)
            if status == "invoiceable":
                self.with_context(active_ids=entries.ids).prepare_ps_invoice()
        return True

    def prepare_ps_invoice(self):
        def ps_invoice_create(result, link_project):
            for res in result:
                project_id = False
                analytic_account_ids = res[0]
                partner_id = res[1]
                partner = self.env["res.partner"].browse(partner_id)
                period_id = res[2]
                project_operating_unit_id = res[3]

                if link_project:
                    project_id = res[4]
                    partner_id = (
                        self.env["project.project"]
                        .browse(project_id)
                        .invoice_address.id
                    )

                search_domain = [
                    ("partner_id", "=", partner_id),
                    ("account_analytic_ids", "in", analytic_account_ids),
                    ("project_operating_unit_id", "=", project_operating_unit_id),
                    ("state", "not in", ("invoiced", "re_confirmed")),
                    ("period_id", "=", period_id),
                ]
                if link_project:
                    search_domain += [("project_id", "=", project_id)]
                    search_domain += [("link_project", "=", True)]
                else:
                    search_domain += [("link_project", "=", False)]

                ps_invobj = ps_invoice.search(search_domain, limit=1)
                if ps_invobj:
                    ctx = self.env.context.copy()
                    ctx.update({"active_invoice_id": ps_invobj.id})
                    ps_invobj.with_context(ctx)._compute_objects()
                else:
                    data = {
                        "partner_id": partner_id,
                        "move_type": "out_invoice",
                        "period_id": period_id,
                        "project_operating_unit_id": project_operating_unit_id,
                        "operating_unit_id": project_operating_unit_id,
                        "link_project": False,
                        "invoice_payment_term_id": partner.property_payment_term_id.id
                        or False,
                        "journal_id": self.env["account.move"]
                        .with_context(default_move_type="out_invoice")
                        ._get_default_journal()
                        .id,
                        "fiscal_position_id": partner.property_account_position_id.id
                        or False,
                        "user_id": self.env.user.id,
                        "company_id": self.env.user.company_id.id,
                        "invoice_date": datetime.now().date(),
                    }
                    if link_project:
                        data.update({"project_id": project_id, "link_project": True})
                    ps_invoice.create(data)

        context = self.env.context.copy()
        entries_ids = context.get("active_ids", [])
        if (
            len(
                self.env["ps.time.line"]
                .browse(entries_ids)
                .filtered(lambda a: a.state != "invoiceable")
            )
            > 0
        ):
            raise UserError(
                _('Please select only TimeLines with state "To Be Invoiced".')
            )

        ps_invoice = self.env["ps.invoice"]

        sep_entries = self.env["ps.time.line"].search(
            [
                ("id", "in", entries_ids),
                "|",
                ("project_id.invoice_properties.group_invoice", "=", False),
                ("task_id.project_id.invoice_properties.group_invoice", "=", False),
            ]
        )

        entries_ids = set(entries_ids) - set(sep_entries.ids)

        if entries_ids:
            self.env.cr.execute(
                """
                SELECT
                array_agg(account_id), partner_id, period_id, project_operating_unit_id
                FROM ps_time_line
                WHERE id IN %s AND date_of_last_wip IS NULL
                GROUP BY partner_id, period_id, project_operating_unit_id
                """,
                (tuple(entries_ids),),
            )

            result = self.env.cr.fetchall()
            ps_invoice_create(result, False)

            # reconfirmed seperate entries
            self.env.cr.execute(
                """
                SELECT
                    array_agg(account_id), partner_id, month_of_last_wip,
                    project_operating_unit_id
                FROM ps_time_line
                WHERE
                    id IN %s AND date_of_last_wip IS NOT NULL AND
                    month_of_last_wip IS NOT NULL
                GROUP BY partner_id, month_of_last_wip, project_operating_unit_id
                """,
                (tuple(entries_ids),),
            )

            reconfirm_res = self.env.cr.fetchall()
            ps_invoice_create(reconfirm_res, False)

        if sep_entries:
            self.env.cr.execute(
                """
                SELECT
                    array_agg(account_id), partner_id, period_id, project_operating_unit_id,
                    project_id
                FROM ps_time_line
                WHERE id IN %s AND date_of_last_wip IS NULL
                GROUP BY partner_id, period_id, project_operating_unit_id, project_id
                """,
                (tuple(sep_entries.ids),),
            )

            result1 = self.env.cr.fetchall()
            ps_invoice_create(result1, True)

            # reconfirmed grouping entries
            self.env.cr.execute(
                """
                SELECT
                    array_agg(account_id), partner_id, month_of_last_wip,
                    project_operating_unit_id, project_id
                FROM ps_time_line
                WHERE
                    id IN %s AND date_of_last_wip IS NOT NULL AND
                    month_of_last_wip IS NOT NULL
                GROUP BY
                partner_id, month_of_last_wip, project_operating_unit_id, project_id""",
                (tuple(sep_entries.ids),),
            )

            reconfirm_res1 = self.env.cr.fetchall()
            ps_invoice_create(reconfirm_res1, True)

    @api.onchange("wip_percentage")
    def onchange_wip_percentage(self):
        if self.wip and self.wip_percentage < 0:
            warning = {
                "title": _("Warning"),
                "message": _("Percentage can't be negative!"),
            }
            return {"warning": warning, "value": {"wip_percentage": 0}}

    @api.onchange("name")
    def onchange_name(self):
        if self.name == "delayed":
            self.wip = True
            context = self.env.context.copy()
            entries_ids = context.get("active_ids", [])
            wip_months = (
                self.env["ps.time.line"].browse(entries_ids).mapped("wip_month_id")
            )
            self.wip_month_ids = [(6, 0, wip_months.ids)]
        else:
            self.wip = False

    @api.model
    def _calculate_fee_rate(self, line):
        amount = line.get_fee_rate_amount(False, False)
        if self.wip:
            amount = amount * (self.wip_percentage / 100)
        return amount

    @api.model
    def _prepare_move_line(self, line):
        res = []
        if line.unit_amount == 0:
            return res

        default_analytic_account = self.env["account.analytic.default"].search(
            [("analytic_id", "=", line.account_id.id)], limit=1
        )
        analytic_tag_ids = []
        if default_analytic_account:
            analytic_tag_ids = [
                (4, analytic_tag.id, None)
                for analytic_tag in default_analytic_account.analytic_tag_ids
            ]
        amount = abs(self._calculate_fee_rate(line))

        move_line_debit = {
            "date_maturity": line.date,
            "partner_id": line.partner_id.id,
            "name": line.name,
            "debit": amount,
            "credit": 0.0,
            # todo also the category properties
            "account_id": line.product_id.property_account_wip_id.id,
            "currency_id": line.currency_id.id,
            "quantity": line.unit_amount,
            "product_id": line.product_id.id,
            "product_uom_id": line.product_uom_id.id,
            "analytic_account_id": line.account_id.id,
            "analytic_tag_ids": analytic_tag_ids,
            "operating_unit_id": line.operating_unit_id
            and line.operating_unit_id.id
            or False,
            "user_id": line.user_id and line.user_id.id or False,
        }

        res.append(move_line_debit)

        move_line_credit = move_line_debit.copy()
        move_line_credit.update(
            {
                "debit": 0.0,
                "credit": amount,
                # todo also the category properties
                "account_id": line.product_id.property_account_income_id.id,
            }
        )
        res.append(move_line_credit)
        return res

    def prepare_account_move(self, time_lines_ids, notupdatestate):  # noqa: C901
        """Creates analytics related financial move lines"""
        acc_time_line = self.env["ps.time.line"]
        done_time_line = self.env["ps.time.line"]
        account_move = self.env["account.move"]
        fields_grouped = [
            "id",
            "partner_id",
            "operating_unit_id",
            "wip_month_id",
            "company_id",
        ]
        grouped_by = [
            "partner_id",
            "operating_unit_id",
            "wip_month_id",
            "company_id",
        ]
        result = acc_time_line.read_group(
            [("id", "in", time_lines_ids)],
            fields_grouped,
            grouped_by,
            offset=0,
            limit=None,
            orderby=False,
            lazy=False,
        )
        narration = self.description if self.wip else ""
        try:
            if len(result) > 0:
                # wip_journal = self.env.ref('ps_timesheet_invoicing.wip_journal')
                # if not wip_journal.sequence_id:
                #     raise UserError(_('Please define sequence on the type WIP journal.'))
                for item in result:
                    if not item["partner_id"]:
                        raise UserError(_("Please define partner."))
                    partner_id = item["partner_id"][0]
                    if not item["operating_unit_id"]:
                        raise UserError(_("Please define operating_unit_id."))
                    operating_unit_id = item["operating_unit_id"][0]
                    if not item["wip_month_id"]:
                        raise UserError(_("Please define WIP Month."))
                    month_id = item["wip_month_id"][0]
                    if not item["company_id"]:
                        raise UserError(_("Please define Company."))
                    company_id = item["company_id"][0]

                    company = self.env["res.company"].browse(company_id)
                    if not company.wip_journal_id:
                        raise UserError(_("Please define WIP journal on company."))
                    if not company.wip_journal_id.sequence_id:
                        raise UserError(
                            _("Please define sequence on the type WIP journal.")
                        )
                    wip_journal = company.wip_journal_id

                    date_end = self.env["date.range"].browse(month_id).date_end

                    partner = self.env["res.partner"].browse(partner_id)
                    if not partner.property_account_receivable_id:
                        raise UserError(
                            _("Please define receivable account for partner %s.")
                            % (partner.name)
                        )

                    aml = []
                    time_line_obj = acc_time_line.search(
                        [
                            ("id", "in", time_lines_ids),
                            ("partner_id", "=", partner_id),
                            ("operating_unit_id", "=", operating_unit_id),
                            ("wip_month_id", "=", month_id),
                        ]
                    )
                    time_line_obj -= done_time_line
                    # if self.wip_percentage > 0.0:
                    # Skip wip move creation when percantage is 0
                    # creates wip moves for all percentages
                    for aal in time_line_obj:
                        if not aal.product_id.property_account_wip_id:
                            raise UserError(
                                _("Please define WIP account for product %s.")
                                % (aal.product_id.name)
                            )
                        for ml in self._prepare_move_line(aal):
                            aml.append(ml)

                    line = [(0, 0, line) for line in aml]

                    move_vals = {
                        "move_type": "entry",
                        "ref": narration,
                        "line_ids": line,
                        "journal_id": wip_journal.id,
                        "date": date_end,
                        "narration": "WIP move",
                        # 'to_be_reversed': True,
                    }

                    ctx = dict(self._context, lang=partner.lang)
                    ctx["company_id"] = company_id
                    ctx_nolang = ctx.copy()
                    ctx_nolang.pop("lang", None)
                    move = account_move.with_context(ctx_nolang).create(move_vals)
                    # move.is_wip_move = True
                    # move.wip_percentage = self.wip_percentage
                    # for line in move.line_ids:
                    #    line.wip_percentage = self.wip_percentage
                    move.action_post()

                    account_move |= move

                    first_of_next_month_date = date_end + timedelta(days=1)
                    wip_month_id = time_line_obj[0]._find_daterange_month(
                        first_of_next_month_date
                    )

                    line_query = """
                        UPDATE
                           ps_time_line
                        SET
                        date_of_last_wip = %s, date_of_next_reconfirmation = %s,
                        month_of_last_wip = %s, wip_month_id = %s
                        WHERE id IN %s
                    """
                    parameters = (
                        date_end,
                        first_of_next_month_date,
                        wip_month_id.id,
                        wip_month_id.id,
                        tuple(time_line_obj.ids),
                    )
                    self.env.cr.execute(line_query, parameters)
                    done_time_line |= time_line_obj

        except Exception as e:
            # update the time line record into there previous state when job get failed in delay
            for line_id, state in notupdatestate.items():
                self.env.cr.execute(
                    "UPDATE ps_time_line SET state = %s WHERE id=%s", (state, line_id)
                )
                self.env.cr.commit()  # pylint: disable=invalid-commit
                self.env.cache.invalidate()
            raise FailedJobError(_("The details of the error:'%s'") % e)
        vals = [account_move.id]
        # if self.wip_percentage > 0.0 or True:
        # Skip wip reversal creation when percantage is 0
        # creates wip reversal moves for all percentages
        reverse_move = self.wip_reversal(account_move)
        if reverse_move:
            vals.append(reverse_move.id)
        # Adding moves to each record
        # self.env['account.analytic.line'].add_move_line(analytic_lines_ids, vals)

        return "WIP moves and Reversals successfully created. \n "

    # @job
    def wip_reversal(self, moves):
        reverse_move = self.env["account.move"]
        for move in moves:
            try:
                date = move.date + timedelta(days=1)
                reverse_move = move._reverse_moves(
                    default_values_list=[
                        dict(date=date, journal_id=move.journal_id.id, auto_post=False)
                    ],
                )
            except Exception as e:
                raise FailedJobError(_("The details of the error:'%s'") % e)
        return reverse_move
