# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-Today OpenERP SA (<http://www.openerp.com>)
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from osv import osv
from osv import fields
import tools

email_model = [
        'crm.lead',
    ]

class email_compose_message(osv.osv_memory):
    _inherit = 'email.compose.message'

    def get_value(self, cr, uid, model, resource_id, context=None):
        if context is None:
            context = {}
        result = super(email_compose_message, self).get_value(cr, uid,  model, resource_id, context=context)
        if model in email_model and resource_id:
            model_obj = self.pool.get(model)
            data = model_obj.browse(cr, uid , resource_id, context)
            result.update({
                    'subject' : data.name or False,
                    'email_to' : data.email_from or False,
                    'email_from' : data.user_id and data.user_id.address_id and data.user_id.address_id.email or tools.config.get('email_from', False),
                    'body' : '\n' + (tools.ustr(data.user_id.signature or '')),
                    'email_cc' : tools.ustr(data.email_cc or ''),
                    'model': model  or False,
                    'res_id': resource_id  or False,
                })
            if hasattr(data, 'section_id'):
                result.update({'reply_to' : data.section_id and data.section_id.reply_to or False})
        return result

email_compose_message()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
