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
from tools.translate import _


class pos_payment_report(osv.osv_memory):
    _name = 'pos.payment.report'
    _description = 'Payment Report'

    def print_report(self, cr, uid, ids, context={}):
        """
         To get the date and print the report
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary
         @return : retrun report
        """

        datas = {'ids': context.get('active_ids', [])}
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'pos.payment.report',
            'datas': datas,
       }

pos_payment_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

