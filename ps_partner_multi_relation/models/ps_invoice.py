from odoo import models


class PsInvoice(models.Model):
    _inherit = "ps.invoice"

    def _compute_state_updates(self):
        """Adapt state of time lines and self if non-cancelled member invoices exist"""
        state2ps_line, state2user_total = super()._compute_state_updates()
        relation_type = self.env.ref("ps_partner_multi_relation.rel_type_consortium").id

        for this in self:
            invoice = this.invoice_id
            if invoice.state != "cancel":
                continue
            if not invoice.get_members_sharing_key(self.partner_id, relation_type):
                continue
            # if there are non-cancelled member invoices, we consider this ps invoice done
            if set(invoice.child_ids.mapped("state")) != {"cancel"}:
                this.state = "invoiced"
                line_state = "invoiced"
                if this.invoice_properties.fixed_amount:
                    line_state = "invoiced-by-fixed"
                user_totals = this.mapped("invoice_line_ids.user_task_total_line_ids")
                state2ps_line[line_state] += user_totals.mapped("detail_ids")
                state2ps_line["invoiced"] += this.mileage_line_ids
                state2user_total[line_state] += user_totals

        return state2ps_line, state2user_total
