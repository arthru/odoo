#!/usr/bin/python
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
import time
from osv import fields, osv

class purchase_double_validation_installer(osv.osv_memory):
    _name = 'purchase.double.validation.installer'
    _inherit = 'res.config'

    _columns = {
        'limit_amount': fields.integer('Limit Amount', required=True, help="Minimum amount after which validation of purchase is required"),
    }

    _defaults = {
        'limit_amount': 1000,
    }

    def execute(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, context=context)
        amt = data[0]['limit_amount']
        data_pool = self.pool.get('ir.model.data')
        transition_obj = self.pool.get('workflow.transition')
        waiting = data_pool._get_id(cr, uid, 'purchase_double_validation', 'trans_router1_waiting')
        waiting_id = data_pool.browse(cr, uid, waiting, context=context).res_id
        confirm = data_pool._get_id(cr, uid, 'purchase', 'trans_draft_confirmed')
        confirm_id = data_pool.browse(cr, uid, confirm, context=context).res_id
        transition_obj.write(cr, uid, waiting_id, {'condition': 'amount_total>%s' % (amt), 'signal': False})
        transition_obj.write(cr, uid, confirm_id, {'condition': 'amount_total<=%s' % (amt), 'signal': False})
        return {}

purchase_double_validation_installer()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

