# -*- coding: utf-8 -*-
#
#  bvr_import.py
#  l10n_ch
#
#  Created by Nicolas Bessi based on Credric Krier contribution
#
#  Copyright (c) 2009 CamptoCamp. All rights reserved.
##############################################################################
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import base64
import time
import re

from tools.translate import _
from osv import osv, fields
from tools import mod10r
import pooler

def _reconstruct_invoice_ref(cursor, user, reference, context=None):
    ###
    id_invoice = False
    # On fait d'abord une recherche sur toutes les factures
    # we now searhc for company
    user_obj = pooler.get_pool(cursor.dbname).get('res.users')
    user_current=user_obj.browse(cursor, user, user)

    ##
    cursor.execute("SELECT inv.id,inv.number from account_invoice AS inv where inv.company_id = %s" ,(user_current.company_id.id,))
    result_invoice = cursor.fetchall()

    for inv_id,inv_name in result_invoice:
        inv_name =  re.sub('[^0-9]', '0', str(inv_name))
        if inv_name == reference:
            id_invoice = inv_id
            break
    if  id_invoice:
        cursor.execute('SELECT l.id ' \
                    'FROM account_move_line l, account_invoice i ' \
                    'WHERE l.move_id = i.move_id AND l.reconcile_id is NULL  ' \
                        'AND i.id IN %s',(tuple([id_invoice]),))
        inv_line = []
        for id_line in cursor.fetchall():
            inv_line.append(id_line[0])
        return inv_line
    else:
        return []
    return True

def _import(self, cursor, user, data, context=None):

    statement_line_obj = self.pool.get('account.bank.statement.line')
    statement_obj = self.pool.get('account.bank.statement')
    voucher_obj = self.pool.get('account.voucher')
    voucher_line_obj = self.pool.get('account.voucher.line')
    move_line_obj = self.pool.get('account.move.line')
    attachment_obj = self.pool.get('ir.attachment')
    file = data['form']['file']
    statement_id = data['id']
    records = []
    total_amount = 0
    total_cost = 0
    find_total = False

    if context is None:
        context = {}
    for lines in base64.decodestring(file).split("\n"):
        # Manage files without carriage return
        while lines:
            (line, lines) = (lines[:128], lines[128:])
            record = {}

            if line[0:3] in ('999', '995'):
                if find_total:
                    raise osv.except_osv(_('Error'),
                            _('Too much total record found!'))
                find_total = True
                if lines:
                    raise osv.except_osv(_('Error'),
                            _('Record found after total record!'))
                amount = float(line[39:49]) + (float(line[49:51]) / 100)
                cost = float(line[69:76]) + (float(line[76:78]) / 100)
                if line[2] == '5':
                    amount *= -1
                    cost *= -1

                if round(amount - total_amount, 2) >= 0.01 \
                        or round(cost - total_cost, 2) >= 0.01:
                    raise osv.except_osv(_('Error'),
                            _('Total record different from the computed!'))
                if int(line[51:63]) != len(records):
                    raise osv.except_osv(_('Error'),
                            _('Number record different from the computed!'))
            else:
                record = {
                    'reference': line[12:39],
                    'amount': float(line[39:47]) + (float(line[47:49]) / 100),
                    'date': time.strftime('%Y-%m-%d',
                        time.strptime(line[65:71], '%y%m%d')),
                    'cost': float(line[96:98]) + (float(line[98:100]) / 100),
                }

                if record['reference'] != mod10r(record['reference'][:-1]):
                    raise osv.except_osv(_('Error'),
                            _('Recursive mod10 is invalid for reference: %s') % \
                                    record['reference'])

                if line[2] == '5':
                    record['amount'] *= -1
                    record['cost'] *= -1
                total_amount += record['amount']
                total_cost += record['cost']
                records.append(record)

#    model_fields_ids = model_fields_obj.search(cursor, user, [
#        ('name', 'in', ['property_account_receivable', 'property_account_payable']),
#        ('model', '=', 'res.partner'),
#        ], context=context)
#    property_ids = property_obj.search(cursor, user, [
#        ('fields_id', 'in', model_fields_ids),
#        ('res_id', '=', False),
#        ], context=context)
    account_receivable = False
    account_payable = False
    statement = statement_obj.browse(cursor, user, statement_id, context=context)

    for record in records:
        # Remove the 11 first char because it can be adherent number
        # TODO check if 11 is the right number
        reference = record['reference'][11:-1].lstrip('0')
        values = {
            'name': 'IN '+ reference,
            'date': record['date'],
            'amount': record['amount'],
            'ref': reference,
            'type': (record['amount'] >= 0 and 'customer') or 'supplier',
            'statement_id': statement_id,
        }

        line_ids = move_line_obj.search(cursor, user, [
            ('ref', 'like', reference),
            ('reconcile_id', '=', False),
            ('account_id.type', 'in', ['receivable', 'payable']),
            ], order='date desc', context=context)
        if not line_ids:
            line_ids = _reconstruct_invoice_ref(cursor, user, reference, None)

        partner_id = False
        account_id = False
        for line in move_line_obj.browse(cursor, user, line_ids, context=context):
            account_receivable = line.partner_id.property_account_receivable.id
            account_payable = line.partner_id.property_account_payable.id
            partner_id = line.partner_id.id
            move_id = line.move_id.id
            if record['amount'] >= 0:
                if round(record['amount'] - line.debit, 2) < 0.01:
#                    line2reconcile = line.id
                    account_id = line.account_id.id
                    break
            else:
                if round(line.credit + record['amount'], 2) < 0.01:
#                    line2reconcile = line.id
                    account_id = line.account_id.id
                    break
        result = voucher_obj.onchange_partner_id(cursor, user, [], partner_id=partner_id, journal_id=statement.journal_id.id, price=abs(record['amount']), currency_id= statement.currency.id, ttype='payment', context=context)
        voucher_res = { 'type': 'payment' ,

             'name': values['name'],
             'partner_id': partner_id,
             'journal_id': statement.journal_id.id,
             'account_id': result.get('account_id', statement.journal_id.default_credit_account_id.id),
             'company_id': statement.company_id.id,
             'currency_id': statement.currency.id,
             'date': record['date'] or time.strftime('%Y-%m-%d'),
             'amount': abs(record['amount']),
            'period_id': statement.period_id.id
             }
        voucher_id = voucher_obj.create(cursor, user, voucher_res, context=context)
        context.update({'move_line_ids': line_ids})
        values['voucher_id'] = voucher_id
        voucher_line_dict =  False
        if result['value']['line_ids']:
            for line_dict in result['value']['line_ids']:
                move_line = move_line_obj.browse(cursor, user, line_dict['move_line_id'], context)
                if move_id == move_line.move_id.id:
                    voucher_line_dict = line_dict
        if voucher_line_dict:
            voucher_line_dict.update({'voucher_id':voucher_id})
            voucher_line_obj.create(cursor, user, voucher_line_dict, context=context)                
             
        if not account_id:
            if record['amount'] >= 0:
                account_id = account_receivable
            else:
                account_id = account_payable
        if not account_id :
            raise osv.except_osv(_('Error'),
                _('The properties account payable account receivable'))
        values['account_id'] = account_id
        values['partner_id'] = partner_id

#            values['reconcile_id'] = statement_reconcile_obj.create(cursor, user, {
#                'line_ids': [(6, 0, [line2reconcile])],
#                }, context=context)

        statement_line_obj.create(cursor, user, values, context=context)
    attachment_obj.create(cursor, user, {
        'name': 'BVR',
        'datas': file,
        'datas_fname': 'BVR.txt',
        'res_model': 'account.bank.statement',
        'res_id': statement_id,
        }, context=context)

    return {}

class bvr_import_wizard(osv.osv_memory):
    _name = 'bvr.import.wizard'
    _columns = {
        'file':fields.binary('BVR File', required=True)
    }

    def import_bvr(self, cr, uid, ids, context=None):
        data = {}
        if context is None:
            context = {}
        active_ids = context.get('active_ids', [])
        active_id = context.get('active_id', False)
        data['form'] = {}
        data['ids'] = active_ids
        data['id'] = active_id
        data['form']['file'] = ''
        res = self.read(cr, uid, ids[0], ['file'])
        if res:
            data['form']['file'] = res['file']
        _import(self, cr, uid, data, context=context)
        return {}

bvr_import_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
