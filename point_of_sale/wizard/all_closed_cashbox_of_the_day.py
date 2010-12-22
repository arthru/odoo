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

from osv import osv

class all_closed_cashbox_of_the_day(osv.osv_memory):
    _name = 'all.closed.cashbox.of.the.day'
    _description = 'All closed cashbox of the day'

    def print_report(self, cr, uid, ids, context=None):
        """
             To get the date and print the report
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary
             @return : retrun report
        """
        if context is None:
            context = {}
        datas = {'ids': context.get('active_ids', [])}
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'all.closed.cashbox.of.the.day',
            'datas': datas,
        }

all_closed_cashbox_of_the_day()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: