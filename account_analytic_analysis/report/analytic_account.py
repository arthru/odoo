# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from report import report_sxw

class analytic_account(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(analytic_account, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_lines': self.get_lines,
        })
    def get_lines(self, analytic_account):
        res = []
        res.append(('Fix Price Invoices',analytic_account.amount_max,analytic_account.ca_invoiced,analytic_account.remaining_ca,analytic_account.ca_to_invoice))
        res.append(('Invoice On Timesheets',analytic_account.hours_qtt_est,analytic_account.hours_qtt_invoiced,analytic_account.remaining_hours,analytic_account.hours_qtt_non_invoiced))
        res.append(('Total',analytic_account.est_total,analytic_account.invoiced_total,analytic_account.remaining_total,analytic_account.toinvoice_total))
        return res

report_sxw.report_sxw(
    'report.analytic.account',
    'account.analytic.account',
    'addons/account_analytic_analysis/report/analytic_account.rml',
    parser=analytic_account
)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
