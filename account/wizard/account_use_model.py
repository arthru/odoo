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
import datetime

from osv import fields, osv
from tools.translate import _

class account_use_model(osv.osv_memory):

    _name = 'account.use.model'
    _description = 'Use model'
    _columns = {
        'model': fields.many2many('account.model', 'account_use_model_relation', 'account_id', 'model_id', 'Account Model'),
    }

    def view_init(self, cr , uid , fields_list, context=None):
        account_model_obj = self.pool.get('account.model')
        if context is None:
            context = {}
        if context.get('active_ids',False):
            data_model = account_model_obj.browse(cr, uid, context['active_ids'])
            for model in data_model:
                for line in model.lines_id:
                    if line.date_maturity == 'partner':
                        if not line.partner_id:
                            raise osv.except_osv(_('Error !'), _("Maturity date of entry line generated by model line '%s' is based on partner payment term! \
                                                    \nPlease define partner on it!"%(line.name)))
        pass

    def create_entries(self, cr, uid, ids, context=None):
        account_model_obj = self.pool.get('account.model')
        account_period_obj = self.pool.get('account.period')
        account_move_obj = self.pool.get('account.move')
        account_move_line_obj = self.pool.get('account.move.line')
        pt_obj = self.pool.get('account.payment.term')
        mod_obj = self.pool.get('ir.model.data')
        if context is None:
            context = {}

        data =  self.read(cr, uid, ids, context=context)[0]
        record_id = context and context.get('model_line', False) or False
        if record_id:
            data_model = account_model_obj.browse(cr, uid, data['model'])
        else:
            data_model = account_model_obj.browse(cr, uid, context['active_ids'])
        move_ids = []
        for model in data_model:
            period_id = account_period_obj.find(cr, uid, context=context)
            if not period_id:
                raise osv.except_osv(_('No period found !'), _('Unable to find a valid period !'))
            period_id = period_id[0]
            move_id = account_move_obj.create(cr, uid, {
                'ref': model.name,
                'period_id': period_id,
                'journal_id': model.journal_id.id,
            })
            move_ids.append(move_id)
            for line in model.lines_id:
                analytic_account_id = False
                if line.analytic_account_id:
                    if not model.journal_id.analytic_journal_id:
                        raise osv.except_osv(_('No Analytic Journal !'),_("You have to define an analytic journal on the '%s' journal!") % (model.journal_id.name,))
                    analytic_account_id = line.analytic_account_id.id
                val = {
                    'move_id': move_id,
                    'journal_id': model.journal_id.id,
                    'period_id': period_id,
                    'analytic_account_id': analytic_account_id
                }
                date_maturity = time.strftime('%Y-%m-%d')
                if line.date_maturity == 'partner' and line.partner_id and line.partner_id.property_payment_term:
                    payment_term_id = line.partner_id.property_payment_term.id
                    pterm_list = pt_obj.compute(cr, uid, payment_term_id, value=1, date_ref=date_maturity)
                    if pterm_list:
                        pterm_list = [l[0] for l in pterm_list]
                        pterm_list.sort()
                        date_maturity = pterm_list[-1]
                val.update({
                    'name': line.name,
                    'quantity': line.quantity,
                    'debit': line.debit,
                    'credit': line.credit,
                    'account_id': line.account_id.id,
                    'move_id': move_id,
                    'partner_id': line.partner_id.id,
                    'date': time.strftime('%Y-%m-%d'),
                    'date_maturity': date_maturity
                })
                c = context.copy()
                c.update({'journal_id': model.journal_id.id,'period_id': period_id})
                id_line = account_move_line_obj.create(cr, uid, val, context=c)

        context.update({'move_ids':move_ids})
        model_data_ids = mod_obj.search(cr, uid,[('model','=','ir.ui.view'),('name','=','view_move_form')], context=context)
        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        return {
            'domain': "[('id','in', ["+','.join(map(str,context['move_ids']))+"])]",
            'name': 'Entries',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'views': [(False,'tree'),(resource_id,'form')],
            'type': 'ir.actions.act_window',
        }

account_use_model()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: