# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv
from tools.translate import _

class pos_receipt(osv.osv_memory):
    _name = 'pos.receipt'
    _description = 'Point of sale receipt'

    _columns = {

    }

    def view_init(self, cr, uid, fields_list, context=None):
        """ 
         Creates view dynamically and adding fields at runtime.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary 
         @return: New arch of view with new columns.
        """         
        order_lst = self. pool.get('pos.order').browse(cr, uid, context['active_id'])
#        for order in order_lst:
#            if order.state_2 in ('to_verify'):
#                raise osv.except_osv(_('Error!', 'Can not print the receipt because of discount and/or payment '))
#        True

    def print_report(self, cr, uid, ids, context=None):

        """
              To get the date and print the report
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary
             @return : retrun report
        """
        datas = {'ids': context.get('active_ids', [])}
        res = {}
        datas['form'] = res

        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'pos.receipt',
            'datas': datas,
       }

pos_receipt()
