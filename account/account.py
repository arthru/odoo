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
import netsvc

from osv import fields, osv
import decimal_precision as dp

from tools.misc import currency
from tools.translate import _
import pooler
from datetime import datetime
from dateutil.relativedelta import relativedelta

from tools import config

class account_payment_term(osv.osv):
    _name = "account.payment.term"
    _description = "Payment Term"
    _columns = {
        'name': fields.char('Payment Term', size=64, translate=True, required=True),
        'active': fields.boolean('Active', help="If the active field is set to true, it will allow you to hide the payment term without removing it."),
        'note': fields.text('Description', translate=True),
        'line_ids': fields.one2many('account.payment.term.line', 'payment_id', 'Terms'),
    }
    _defaults = {
        'active': lambda *a: 1,
    }
    _order = "name"

    def compute(self, cr, uid, id, value, date_ref=False, context={}):
        if not date_ref:
            date_ref = datetime.now().strftime('%Y-%m-%d')
        pt = self.browse(cr, uid, id, context)
        amount = value
        result = []
        for line in pt.line_ids:
            prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
            if line.value == 'fixed':
                amt = round(line.value_amount, prec)
            elif line.value == 'procent':
                amt = round(value * line.value_amount, prec)
            elif line.value == 'balance':
                amt = round(amount, prec)
            if amt:
                next_date = datetime.strptime(date_ref, '%y-%m-%d') + relativedelta(days=line.days)
                if line.days2 < 0:
                    next_date += relativedelta(day=line.days2)
                if line.days2 > 0:
                    next_date += relativedelta(day=line.days2, months=1)
                result.append( (next_date.strftime('%Y-%m-%d'), amt) )
                amount -= amt
        return result

account_payment_term()

class account_payment_term_line(osv.osv):
    _name = "account.payment.term.line"
    _description = "Payment Term Line"
    _columns = {
        'name': fields.char('Line Name', size=32, required=True),
        'sequence': fields.integer('Sequence', required=True, help="The sequence field is used to order the payment term lines from the lowest sequences to the higher ones"),
        'value': fields.selection([('procent', 'Percent'),
                                   ('balance', 'Balance'),
                                   ('fixed', 'Fixed Amount')], 'Value',
                                   required=True, help="""Example: 14 days 2%, 30 days net
1. Line 1: percent 0.02 14 days
2. Line 2: balance 30 days"""),

        'value_amount': fields.float('Value Amount', help="For Value percent enter % ratio between 0-1."),
        'days': fields.integer('Number of Days', required=True, help="Number of days to add before computation of the day of month." \
            "If Date=15/01, Number of Days=22, Day of Month=-1, then the due date is 28/02."),
        'days2': fields.integer('Day of the Month', required=True, help="Day of the month, set -1 for the last day of the current month. If it's positive, it gives the day of the next month. Set 0 for net days (otherwise it's based on the beginning of the month)."),
        'payment_id': fields.many2one('account.payment.term', 'Payment Term', required=True, select=True),
    }
    _defaults = {
        'value': lambda *a: 'balance',
        'sequence': lambda *a: 5,
        'days2': lambda *a: 0,
    }
    _order = "sequence"

    def _check_percent(self, cr, uid, ids, context={}):
        obj = self.browse(cr, uid, ids[0])
        if obj.value == 'procent' and ( obj.value_amount < 0.0 or obj.value_amount > 1.0):
            return False
        return True

    _constraints = [
        (_check_percent, _('Percentages for Payment Term Line must be between 0 and 1, Example: 0.02 for 2% '), ['value_amount']),
    ]

account_payment_term_line()


class account_account_type(osv.osv):
    _name = "account.account.type"
    _description = "Account Type"
    _columns = {
        'name': fields.char('Acc. Type Name', size=64, required=True, translate=True),
        'code': fields.char('Code', size=32, required=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of account types."),
        'partner_account': fields.boolean('Partner account'),
        'close_method': fields.selection([('none', 'None'), ('balance', 'Balance'), ('detail', 'Detail'), ('unreconciled', 'Unreconciled')], 'Deferral Method', required=True),
        'sign': fields.selection([(-1, 'Negative'), (1, 'Positive')], 'Sign on Reports', required=True, help='Allows you to change the sign of the balance amount displayed in the reports, so that you can see positive figures instead of negative ones in expenses accounts.'),
        'report_type':fields.selection([
            ('none','/'),
            ('income','Profit & Loss (Income Accounts)'),
            ('expense','Profit & Loss (Expense Accounts)'),
            ('asset','Balance Sheet (Assets Accounts)'),
            ('liability','Balance Sheet (Liability Accounts)')
        ],'Type Heads', select=True, readonly=False, help="According value related accounts will be display on respective reports (Balance Sheet Profit & Loss Account)"),
        'parent_id':fields.many2one('account.account.type', 'Parent Type', required=False),
        'child_ids':fields.one2many('account.account.type', 'parent_id', 'Child Types', required=False),
        'note': fields.text('Description'),
    }
    _defaults = {
        'close_method': lambda *a: 'none',
        'sequence': lambda *a: 5,
        'sign': lambda *a: 1,
    }
    _order = "sequence"

    def _check_recursion(self, cr, uid, ids):
        #TODO: Need to check for recusrion
        return True

    _constraints = [
        (_check_recursion, 'Error ! You can not create recursive types.', ['parent_id'])
    ]

account_account_type()

def _code_get(self, cr, uid, context={}):
    acc_type_obj = self.pool.get('account.account.type')
    ids = acc_type_obj.search(cr, uid, [])
    res = acc_type_obj.read(cr, uid, ids, ['code', 'name'], context)
    return [(r['code'], r['name']) for r in res]

#----------------------------------------------------------
# Accounts
#----------------------------------------------------------

class account_tax(osv.osv):
    _name = 'account.tax'
account_tax()

class account_account(osv.osv):
    _order = "parent_left"
    _parent_order = "code"
    _name = "account.account"
    _description = "Account"
    _parent_store = True

    def _get_children_and_consol(self, cr, uid, ids, context={}):
        ids2=[]
        temp=[]
        read_data= self.read(cr, uid, ids,['id','child_id'], context)
        for data in read_data:
            ids2.append(data['id'])
            if data['child_id']:
                temp=[]
                for x in data['child_id']:
                    temp.append(x)
                ids2 += self._get_children_and_consol(cr, uid, temp, context)
        return ids2

    def search(self, cr, uid, args, offset=0, limit=None, order=None,
            context=None, count=False):
        if context is None:
            context = {}
        pos = 0

        while pos < len(args):

            if args[pos][0] == 'code' and args[pos][1] in ('like', 'ilike') and args[pos][2]:
                args[pos] = ('code', '=like', str(args[pos][2].replace('%', ''))+'%')
            if args[pos][0] == 'journal_id':
                if not args[pos][2]:
                    del args[pos]
                    continue
                jour = self.pool.get('account.journal').browse(cr, uid, args[pos][2])
                if (not (jour.account_control_ids or jour.type_control_ids)) or not args[pos][2]:
                    args[pos] = ('type','not in',('consolidation','view'))
                    continue
                ids3 = map(lambda x: x.id, jour.type_control_ids)
                ids1 = super(account_account, self).search(cr, uid, [('user_type', 'in', ids3)])
                ids1 += map(lambda x: x.id, jour.account_control_ids)
                args[pos] = ('id', 'in', ids1)
            pos += 1

        if context and context.has_key('consolidate_childs'): #add consolidated childs of accounts
            ids = super(account_account, self).search(cr, uid, args, offset, limit,
                order, context=context, count=count)
            for consolidate_child in self.browse(cr, uid, context['account_id']).child_consol_ids:
                ids.append(consolidate_child.id)
            return ids

        return super(account_account, self).search(cr, uid, args, offset, limit,
                order, context=context, count=count)

    def _get_children_and_consol(self, cr, uid, ids, context={}):
        #this function search for all the children and all consolidated children (recursively) of the given account ids
        ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)], context=context)
        ids3 = []
        for rec in self.browse(cr, uid, ids2, context=context):
            for child in rec.child_consol_ids:
                ids3.append(child.id)
        if ids3:
            ids3 = self._get_children_and_consol(cr, uid, ids3, context)
        return ids2 + ids3

    def __compute(self, cr, uid, ids, field_names, arg, context={}, query=''):
        #compute the balance/debit/credit accordingly to the value of field_name for the given account ids
        mapping = {
            'balance': "COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance ",
            'debit': "COALESCE(SUM(l.debit), 0) as debit ",
            'credit': "COALESCE(SUM(l.credit), 0) as credit "
        }
        #get all the necessary accounts
        ids2 = self._get_children_and_consol(cr, uid, ids, context)
        #compute for each account the balance/debit/credit from the move lines
        accounts = {}
        if ids2:
            aml_query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)

            wheres = [""]
            if query.strip():
                wheres.append(query.strip())
            if aml_query.strip():
                wheres.append(aml_query.strip())
            query = " AND ".join(wheres)

            cr.execute("SELECT l.account_id as id, " +\
                    ' , '.join(map(lambda x: mapping[x], field_names)) +
                    "FROM " \
                        "account_move_line l " \
                    "WHERE " \
                        "l.account_id =ANY(%s) " \
                        + query +
                    " GROUP BY l.account_id",(ids2,))

            for res in cr.dictfetchall():
                accounts[res['id']] = res


        # consolidate accounts with direct children
        ids2.reverse()
        brs = list(self.browse(cr, uid, ids2, context=context))
        sums = {}
        while brs:
            current = brs[0]
            can_compute = True
            for child in current.child_id:
                if child.id not in sums:
                    can_compute = False
                    try:
                        brs.insert(0, brs.pop(brs.index(child)))
                    except ValueError:
                        brs.insert(0, child)
            if can_compute:
                brs.pop(0)
                for fn in field_names:
                    sums.setdefault(current.id, {})[fn] = accounts.get(current.id, {}).get(fn, 0.0)
                    if current.child_id:
                        sums[current.id][fn] += sum(sums[child.id][fn] for child in current.child_id)
        res = {}
        null_result = dict((fn, 0.0) for fn in field_names)
        for id in ids:
            res[id] = sums.get(id, null_result)
        return res

    def _get_company_currency(self, cr, uid, ids, field_name, arg, context={}):
        result = {}
        for rec in self.browse(cr, uid, ids, context):
            result[rec.id] = (rec.company_id.currency_id.id,rec.company_id.currency_id.code)
        return result

    def _get_child_ids(self, cr, uid, ids, field_name, arg, context={}):
        result = {}
        for record in self.browse(cr, uid, ids, context):
            if record.child_parent_ids:
                result[record.id] = [x.id for x in record.child_parent_ids]
            else:
                result[record.id] = []

            if record.child_consol_ids:
                for acc in record.child_consol_ids:
                    if acc.id not in result[record.id]:
                        result[record.id].append(acc.id)

        return result

    def _get_level(self, cr, uid, ids, field_name, arg, context={}):
        res={}
        accounts = self.browse(cr, uid, ids)
        for account in accounts:
            level = 0
            if account.parent_id :
                obj = self.browse(cr, uid, account.parent_id.id)
                level = obj.level + 1
            res[account.id] = level
        return res

    _columns = {
        'name': fields.char('Name', size=128, required=True, select=True),
        'currency_id': fields.many2one('res.currency', 'Secondary Currency', help="Forces all moves for this account to have this secondary currency."),
        'code': fields.char('Code', size=64, required=True),
        'type': fields.selection([
            ('receivable', 'Receivable'),
            ('payable', 'Payable'),
            ('view', 'View'),
            ('consolidation', 'Consolidation'),
            ('other', 'Others'),
            ('closed', 'Closed'),
        ], 'Internal Type', required=True, help="This type is used to differentiate types with "\
            "special effects in Open ERP: view can not have entries, consolidation are accounts that "\
            "can have children accounts for multi-company consolidations, payable/receivable are for "\
            "partners accounts (for debit/credit computations), closed for depreciated accounts."),
        'user_type': fields.many2one('account.account.type', 'Account Type', required=True,
            help="These types are defined according to your country. The type contains more information "\
            "about the account and its specificities."),
        'parent_id': fields.many2one('account.account', 'Parent', ondelete='cascade', domain=[('type','=','view')]),
        'child_parent_ids': fields.one2many('account.account','parent_id','Children'),
        'child_consol_ids': fields.many2many('account.account', 'account_account_consol_rel', 'child_id', 'parent_id', 'Consolidated Children'),
        'child_id': fields.function(_get_child_ids, method=True, type='many2many', relation="account.account", string="Child Accounts"),
        'balance': fields.function(__compute, digits_compute=dp.get_precision('Account'), method=True, string='Balance', multi='balance'),
        'credit': fields.function(__compute, digits_compute=dp.get_precision('Account'), method=True, string='Credit', multi='balance'),
        'debit': fields.function(__compute, digits_compute=dp.get_precision('Account'), method=True, string='Debit', multi='balance'),
        'reconcile': fields.boolean('Reconcile', help="Check this if the user is allowed to reconcile entries in this account."),
        'shortcut': fields.char('Shortcut', size=12),
        'tax_ids': fields.many2many('account.tax', 'account_account_tax_default_rel',
            'account_id', 'tax_id', 'Default Taxes'),
        'note': fields.text('Note'),
        'company_currency_id': fields.function(_get_company_currency, method=True, type='many2one', relation='res.currency', string='Company Currency'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'active': fields.boolean('Active', select=2, help="If the active field is set to true, it will allow you to hide the account without removing it."),

        'parent_left': fields.integer('Parent Left', select=1),
        'parent_right': fields.integer('Parent Right', select=1),
        'currency_mode': fields.selection([('current', 'At Date'), ('average', 'Average Rate')], 'Outgoing Currencies Rate',
            help=
            'This will select how the current currency rate for outgoing transactions is computed. '\
            'In most countries the legal method is "average" but only a few software systems are able to '\
            'manage this. So if you import from another software system you may have to use the rate at date. ' \
            'Incoming transactions always use the rate at date.', \
            required=True),
        'check_history': fields.boolean('Display History',
            help="Check this box if you want to print all entries when printing the General Ledger, "\
            "otherwise it will only print its balance."),
        'level': fields.function(_get_level, string='Level', method=True, store=True, type='integer'),
    }

    def _default_company(self, cr, uid, context={}):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            return user.company_id.id
        return self.pool.get('res.company').search(cr, uid, [('parent_id', '=', False)])[0]

    _defaults = {
        'type': lambda *a : 'view',
        'reconcile': lambda *a: False,
        'company_id': _default_company,
        'active': lambda *a: True,
        'check_history': lambda *a: True,
        'currency_mode': lambda *a: 'current',
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'account.account', context=c),
    }

    def _check_recursion(self, cr, uid, ids):
        obj_self = self.browse(cr, uid, ids[0])
        p_id = obj_self.parent_id and obj_self.parent_id.id
        if (obj_self in obj_self.child_consol_ids) or (p_id and (p_id is obj_self.id)):
            return False
        while(ids):
            cr.execute('select distinct child_id from account_account_consol_rel where parent_id =ANY(%s)',(ids,))
            child_ids = filter(None, map(lambda x: x[0], cr.fetchall()))
            c_ids = child_ids
            if (p_id and (p_id in c_ids)) or (obj_self.id in c_ids):
                return False
            while len(c_ids):
                s_ids = self.search(cr, uid, [('parent_id', 'in', c_ids)])
                if p_id and (p_id in s_ids):
                    return False
                c_ids = s_ids
            ids = child_ids
        return True

    _constraints = [
        (_check_recursion, 'Error ! You can not create recursive accounts.', ['parent_id'])
    ]
    _sql_constraints = [
        ('code_company_uniq', 'unique (code,company_id)', 'The code of the account must be unique per company !')
    ]
    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if not context:
            context = {}
        args = args[:]
        ids = []
        try:
            if name and str(name).startswith('partner:'):
                part_id = int(name.split(':')[1])
                part = self.pool.get('res.partner').browse(cr, user, part_id, context)
                args += [('id', 'in', (part.property_account_payable.id, part.property_account_receivable.id))]
                name = False
            if name and str(name).startswith('type:'):
                type = name.split(':')[1]
                args += [('type', '=', type)]
                name = False
        except:
            pass
        if name:
            ids = self.search(cr, user, [('code', '=like', name+"%")]+args, limit=limit)
            if not ids:
                ids = self.search(cr, user, [('shortcut', '=', name)]+ args, limit=limit)
            if not ids:
                ids = self.search(cr, user, [('name', operator, name)]+ args, limit=limit)
        else:
            ids = self.search(cr, user, args, context=context, limit=limit)
        return self.name_get(cr, user, ids, context=context)

    def name_get(self, cr, uid, ids, context={}):
        if not len(ids):
            return []
        reads = self.read(cr, uid, ids, ['name', 'code'], context)
        res = []
        for record in reads:
            name = record['name']
            if record['code']:
                name = record['code'] + ' '+name
            res.append((record['id'], name))
        return res

    def copy(self, cr, uid, id, default={}, context={}, done_list=[], local=False):
        account = self.browse(cr, uid, id, context=context)
        new_child_ids = []
        if not default:
            default = {}
        default = default.copy()
        default['code'] = (account['code'] or '') + '(copy)'
        if not local:
            done_list = []
        if account.id in done_list:
            return False
        done_list.append(account.id)
        if account:
            for child in account.child_id:
                child_ids = self.copy(cr, uid, child.id, default, context=context, done_list=done_list, local=True)
                if child_ids:
                    new_child_ids.append(child_ids)
            default['child_parent_ids'] = [(6, 0, new_child_ids)]
        else:
            default['child_parent_ids'] = False
        return super(account_account, self).copy(cr, uid, id, default, context=context)

    def _check_moves(self, cr, uid, ids, method, context):
        line_obj = self.pool.get('account.move.line')
        account_ids = self.search(cr, uid, [('id', 'child_of', ids)])

        if line_obj.search(cr, uid, [('account_id', 'in', account_ids)]):
            if method == 'write':
                raise osv.except_osv(_('Error !'), _('You cannot deactivate an account that contains account moves.'))
            elif method == 'unlink':
                raise osv.except_osv(_('Error !'), _('You cannot remove an account which has account entries!. '))
        #Checking whether the account is set as a property to any Partner or not
        value = 'account.account,' + str(ids[0])
        partner_prop_acc = self.pool.get('ir.property').search(cr, uid, [('value_reference','=',value)], context=context)
        if partner_prop_acc:
            raise osv.except_osv(_('Warning !'), _('You cannot remove/deactivate an account which is set as a property to any Partner.'))
        return True

    def _check_allow_type_change(self, cr, uid, ids, new_type, context):
        group1 = ['payable', 'receivable', 'other']
        group2 = ['consolidation','view']
        line_obj = self.pool.get('account.move.line')
        for account in self.browse(cr, uid, ids, context=context):
            old_type = account.type
            account_ids = self.search(cr, uid, [('id', 'child_of', [account.id])])
            if line_obj.search(cr, uid, [('account_id', 'in', account_ids)]):
                #Check for 'Closed' type
                if old_type == 'closed' and new_type !='closed':
                    raise osv.except_osv(_('Warning !'), _("You cannot change the type of account from 'Closed' to any other type which contains account entries!"))
                #Check for change From group1 to group2 and vice versa
                if (old_type in group1 and new_type in group2) or (old_type in group2 and new_type in group1):
                    raise osv.except_osv(_('Warning !'), _("You cannot change the type of account from '%s' to '%s' type as it contains account entries!") % (old_type,new_type,))
        return True

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        if 'active' in vals and not vals['active']:
            self._check_moves(cr, uid, ids, "write", context)
        if 'type' in vals.keys():
            self._check_allow_type_change(cr, uid, ids, vals['type'], context=context)
        return super(account_account, self).write(cr, uid, ids, vals, context=context)

    def unlink(self, cr, uid, ids, context={}):
        self._check_moves(cr, uid, ids, "unlink", context)
        return super(account_account, self).unlink(cr, uid, ids, context)

account_account()

class account_journal_view(osv.osv):
    _name = "account.journal.view"
    _description = "Journal View"
    _columns = {
        'name': fields.char('Journal View', size=64, required=True),
        'columns_id': fields.one2many('account.journal.column', 'view_id', 'Columns')
    }
    _order = "name"
account_journal_view()


class account_journal_column(osv.osv):
    def _col_get(self, cr, user, context={}):
        result = []
        cols = self.pool.get('account.move.line')._columns
        for col in cols:
            result.append( (col, cols[col].string) )
        result.sort()
        return result
    _name = "account.journal.column"
    _description = "Journal Column"
    _columns = {
        'name': fields.char('Column Name', size=64, required=True),
        'field': fields.selection(_col_get, 'Field Name', method=True, required=True, size=32),
        'view_id': fields.many2one('account.journal.view', 'Journal View', select=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order to journal column."),
        'required': fields.boolean('Required'),
        'readonly': fields.boolean('Readonly'),
    }
    _order = "sequence"
account_journal_column()

class account_journal(osv.osv):
    _name = "account.journal"
    _description = "Journal"
    _columns = {
        'name': fields.char('Journal Name', size=64, required=True, translate=True,help="Name of the journal"),
        'code': fields.char('Code', size=16,required=True,help="Code of the journal"),
        'type': fields.selection([('sale', 'Sale'),('sale_refund','Sale Refund'), ('purchase', 'Purchase'), ('purchase_refund','Purchase Refund'),('expense', 'Expense'), ('cash', 'Cash'), ('bank', 'Bank'), ('general', 'General'), ('situation', 'Situation')], 'Type', size=32, required=True,
                                 help="Select 'Sale' for Sale journal to be used at the time of making invoice."\
                                 " Select 'Purchase' for Purchase Journal to be used at the time of approving purchase order."\
                                 " Select 'Cash' to be used at the time of making payment."\
                                 " Select 'General' to be used at the time of stock input/output."\
                                 " Select 'Situation' to be used at the time of making vouchers."),
        'refund_journal': fields.boolean('Refund Journal', help='Fill this if the journal is to be used for refunds of invoices.'),
        'type_control_ids': fields.many2many('account.account.type', 'account_journal_type_rel', 'journal_id','type_id', 'Type Controls', domain=[('code','<>','view'), ('code', '<>', 'closed')]),
        'account_control_ids': fields.many2many('account.account', 'account_account_type_rel', 'journal_id','account_id', 'Account', domain=[('type','<>','view'), ('type', '<>', 'closed')]),
        'view_id': fields.many2one('account.journal.view', 'Display Mode', required=True, help="Gives the view used when writing or browsing entries in this journal. The view tells Open ERP which fields should be visible, required or readonly and in which order. You can create your own view for a faster encoding in each journal."),
        'default_credit_account_id': fields.many2one('account.account', 'Default Credit Account', domain="[('type','!=','view')]",help="This will act as a default account for credit amount"),
        'default_debit_account_id': fields.many2one('account.account', 'Default Debit Account', domain="[('type','!=','view')]",help="This will act as a default account for debit amount"),
        'centralisation': fields.boolean('Centralised counterpart', help="Check this box to determine that each entry of this journal won't create a new counterpart but will share the same counterpart. This is used in fiscal year closing."),
        'update_posted': fields.boolean('Allow Cancelling Entries',help="Check this box if you want to cancel the entries related to this journal or want to cancel the invoice related to this journal"),
        'group_invoice_lines': fields.boolean('Group invoice lines', help="If this box is checked, the system will try to group the accounting lines when generating them from invoices."),
        'sequence_id': fields.many2one('ir.sequence', 'Entry Sequence', help="The sequence gives the display order for a list of journals", required=True),
        'user_id': fields.many2one('res.users', 'User', help="The user responsible for this journal"),
        'groups_id': fields.many2many('res.groups', 'account_journal_group_rel', 'journal_id', 'group_id', 'Groups'),
        'currency': fields.many2one('res.currency', 'Currency', help='The currency used to enter statement'),
        'entry_posted': fields.boolean('Skip \'Draft\' State for Created Entries', help='Check this box if you don\'t want new account moves to pass through the \'draft\' state and instead goes directly to the \'posted state\' without any manual validation.'),
        'company_id': fields.many2one('res.company', 'Company', required=True,select=1,help="Company related to a journal"),
        'invoice_sequence_id': fields.many2one('ir.sequence', 'Invoice Sequence', \
            help="The sequence used for invoice numbers in this journal."),
        'allow_date':fields.boolean('Check Date not in the Period', help= 'If set to True then do not accept the entry if the entry date is not into the period dates'),
    }

    _defaults = {
        'user_id': lambda self,cr,uid,context: uid,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }
    def create(self, cr, uid, vals, context={}):
        journal_id = super(account_journal, self).create(cr, uid, vals, context)
#       journal_name = self.browse(cr, uid, [journal_id])[0].code
#       periods = self.pool.get('account.period')
#       ids = periods.search(cr, uid, [('date_stop','>=',time.strftime('%Y-%m-%d'))])
#       for period in periods.browse(cr, uid, ids):
#           self.pool.get('account.journal.period').create(cr, uid, {
#               'name': (journal_name or '')+':'+(period.code or ''),
#               'journal_id': journal_id,
#               'period_id': period.id
#           })
        return journal_id

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            ids = self.search(cr, user, [('code','ilike',name)]+ args, limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('name',operator,name)]+ args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context=context)
    
    def onchange_type(self, cr, uid, ids, type):
        res={}
        for line in self.browse(cr, uid, ids):
            if type == 'situation':
                  res= {'value':{'centralisation': True}}
            else:
                  res= {'value':{'centralisation': False}}
        return res
       

account_journal()

class account_fiscalyear(osv.osv):
    _name = "account.fiscalyear"
    _description = "Fiscal Year"
    _columns = {
        'name': fields.char('Fiscal Year', size=64, required=True),
        'code': fields.char('Code', size=6, required=True),
        'company_id': fields.many2one('res.company', 'Company',
            help="Keep empty if the fiscal year belongs to several companies.", required=True),
        'date_start': fields.date('Start Date', required=True),
        'date_stop': fields.date('End Date', required=True),
        'period_ids': fields.one2many('account.period', 'fiscalyear_id', 'Periods'),
        'state': fields.selection([('draft','Draft'), ('done','Done')], 'State', readonly=True,
                                  help='When fiscal year is created. The state is \'Draft\'. At the end of the year it is in \'Done\' state.'),
    }

    _defaults = {
        'state': lambda *a: 'draft',
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }
    _order = "date_start"

    def _check_duration(self,cr,uid,ids):
        obj_fy=self.browse(cr,uid,ids[0])
        if obj_fy.date_stop < obj_fy.date_start:
            return False
        return True

    _constraints = [
        (_check_duration, 'Error ! The duration of the Fiscal Year is invalid. ', ['date_stop'])
    ]

    def create_period3(self,cr, uid, ids, context={}):
        return self.create_period(cr, uid, ids, context, 3)

    def create_period(self,cr, uid, ids, context={}, interval=1):
        for fy in self.browse(cr, uid, ids, context):
            ds = datetime.strptime(fy.date_start, '%Y-%m-%d')
            while ds.strftime('%Y-%m-%d')<fy.date_stop:
                de = ds + relativedelta(months=interval, days=-1)

                if de.strftime('%Y-%m-%d')>fy.date_stop:
                    de = datetime.strptime(fy.date_stop, '%Y-%m-%d')

                self.pool.get('account.period').create(cr, uid, {
                    'name': ds.strftime('%m/%Y'),
                    'code': ds.strftime('%m/%Y'),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d'),
                    'fiscalyear_id': fy.id,
                })
                ds = ds + relativedelta(months=interval)
        return True

    def find(self, cr, uid, dt=None, exception=True, context={}):
        if not dt:
            dt = time.strftime('%Y-%m-%d')
        ids = self.search(cr, uid, [('date_start', '<=', dt), ('date_stop', '>=', dt)])
        if not ids:
            if exception:
                raise osv.except_osv(_('Error !'), _('No fiscal year defined for this date !\nPlease create one.'))
            else:
                return False
        return ids[0]

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=80):
        if args is None:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            ids = self.search(cr, user, [('code','ilike',name)]+ args, limit=limit)
        if not ids:
            ids = self.search(cr, user, [('name',operator,name)]+ args, limit=limit)
        return self.name_get(cr, user, ids, context=context)

account_fiscalyear()

class account_period(osv.osv):
    _name = "account.period"
    _description = "Account period"
    _columns = {
        'name': fields.char('Period Name', size=64, required=True),
        'code': fields.char('Code', size=12),
        'special': fields.boolean('Opening/Closing Period', size=12,
            help="These periods can overlap."),
        'date_start': fields.date('Start of Period', required=True, states={'done':[('readonly',True)]}),
        'date_stop': fields.date('End of Period', required=True, states={'done':[('readonly',True)]}),
        'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year', required=True, states={'done':[('readonly',True)]}, select=True),
        'state': fields.selection([('draft','Draft'), ('done','Done')], 'State', readonly=True,
                                  help='When monthly periods are created. The state is \'Draft\'. At the end of monthly period it is in \'Done\' state.'),
        'company_id': fields.many2one('res.company', 'Company', required=True)
    }
    _defaults = {
        'state': lambda *a: 'draft',
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }
    _order = "date_start"

    def _check_duration(self,cr,uid,ids,context={}):
        obj_period=self.browse(cr,uid,ids[0])
        if obj_period.date_stop < obj_period.date_start:
            return False
        return True

    def _check_year_limit(self,cr,uid,ids,context={}):
        for obj_period in self.browse(cr,uid,ids):
            if obj_period.special:
                continue

            if obj_period.fiscalyear_id.date_stop < obj_period.date_stop or \
               obj_period.fiscalyear_id.date_stop < obj_period.date_start or \
               obj_period.fiscalyear_id.date_start > obj_period.date_start or \
               obj_period.fiscalyear_id.date_start > obj_period.date_stop:
                return False

            pids = self.search(cr, uid, [('date_stop','>=',obj_period.date_start),('date_start','<=',obj_period.date_stop),('special','=',False),('id','<>',obj_period.id)])
            for period in self.browse(cr, uid, pids):
                if period.fiscalyear_id.company_id.id==obj_period.fiscalyear_id.company_id.id:
                    return False
        return True

    _constraints = [
        (_check_duration, 'Error ! The duration of the Period(s) is/are invalid. ', ['date_stop']),
        (_check_year_limit, 'Invalid period ! Some periods overlap or the date period is not in the scope of the fiscal year. ', ['date_stop'])
    ]

    def next(self, cr, uid, period, step, context={}):
        ids = self.search(cr, uid, [('date_start','>',period.date_start)])
        if len(ids)>=step:
            return ids[step-1]
        return False

    def find(self, cr, uid, dt=None, context={}):
        if not dt:
            dt = time.strftime('%Y-%m-%d')
#CHECKME: shouldn't we check the state of the period?
        ids = self.search(cr, uid, [('date_start','<=',dt),('date_stop','>=',dt)])
        if not ids:
            raise osv.except_osv(_('Error !'), _('No period defined for this date: %s !\nPlease create a fiscal year.')%dt)
        return ids

    def action_draft(self, cr, uid, ids, *args):
        users_roles = self.pool.get('res.users').browse(cr, uid, uid).roles_id
        for role in users_roles:
            if role.name=='Period':
                mode = 'draft'
                for id in ids:
                    cr.execute('update account_journal_period set state=%s where period_id=%s', (mode, id))
                    cr.execute('update account_period set state=%s where id=%s', (mode, id))
        return True

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=80):
        if args is None:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            ids = self.search(cr, user, [('code','ilike',name)]+ args, limit=limit)
        if not ids:
            ids = self.search(cr, user, [('name',operator,name)]+ args, limit=limit)
        return self.name_get(cr, user, ids, context=context)

account_period()

class account_journal_period(osv.osv):
    _name = "account.journal.period"
    _description = "Journal Period"

    def _icon_get(self, cr, uid, ids, field_name, arg=None, context={}):
        result = {}.fromkeys(ids, 'STOCK_NEW')
        for r in self.read(cr, uid, ids, ['state']):
            result[r['id']] = {
                'draft': 'STOCK_NEW',
                'printed': 'STOCK_PRINT_PREVIEW',
                'done': 'STOCK_DIALOG_AUTHENTICATION',
            }.get(r['state'], 'STOCK_NEW')
        return result

    _columns = {
        'name': fields.char('Journal-Period Name', size=64, required=True),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True, ondelete="cascade"),
        'period_id': fields.many2one('account.period', 'Period', required=True, ondelete="cascade"),
        'icon': fields.function(_icon_get, method=True, string='Icon', type='char', size=32),
        'active': fields.boolean('Active', required=True, help="If the active field is set to true, it will allow you to hide the journal period without removing it."),
        'state': fields.selection([('draft','Draft'), ('printed','Printed'), ('done','Done')], 'State', required=True, readonly=True,
                                  help='When journal period is created. The state is \'Draft\'. If a report is printed it comes to \'Printed\' state. When all transactions are done, it comes in \'Done\' state.'),
        'fiscalyear_id': fields.related('period_id', 'fiscalyear_id', string='Fiscal Year', type='many2one', relation='account.fiscalyear'),
        'company_id' : fields.many2one('res.company', 'Company')
    }

    def _check(self, cr, uid, ids, context={}):
        for obj in self.browse(cr, uid, ids, context):
            cr.execute('select * from account_move_line where journal_id=%s and period_id=%s limit 1', (obj.journal_id.id, obj.period_id.id))
            res = cr.fetchall()
            if res:
                raise osv.except_osv(_('Error !'), _('You can not modify/delete a journal with entries for this period !'))
        return True

    def write(self, cr, uid, ids, vals, context={}):
        self._check(cr, uid, ids, context)
        return super(account_journal_period, self).write(cr, uid, ids, vals, context)

    def create(self, cr, uid, vals, context={}):
        period_id=vals.get('period_id',False)
        if period_id:
            period = self.pool.get('account.period').browse(cr, uid,period_id)
            vals['state']=period.state
        return super(account_journal_period, self).create(cr, uid, vals, context)

    def unlink(self, cr, uid, ids, context={}):
        self._check(cr, uid, ids, context)
        return super(account_journal_period, self).unlink(cr, uid, ids, context)

    _defaults = {
        'state': lambda *a: 'draft',
        'active': lambda *a: True,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }
    _order = "period_id"

account_journal_period()

class account_fiscalyear(osv.osv):
    _inherit = "account.fiscalyear"
    _description = "Fiscal Year"
    _columns = {
        'end_journal_period_id':fields.many2one('account.journal.period','End of Year Entries Journal', readonly=True),
    }

account_fiscalyear()
#----------------------------------------------------------
# Entries
#----------------------------------------------------------
class account_move(osv.osv):
    _name = "account.move"
    _description = "Account Entry"
    _order = 'id desc'

    def name_get(self, cursor, user, ids, context=None):
        if not len(ids):
            return []
        res=[]
        data_move = self.pool.get('account.move').browse(cursor,user,ids)
        for move in data_move:
            if move.state=='draft':
                name = '*' + str(move.id)
            else:
                name = move.name
            res.append((move.id, name))
        return res


    def _get_period(self, cr, uid, context):
        periods = self.pool.get('account.period').find(cr, uid)
        if periods:
            return periods[0]
        else:
            return False

    def _amount_compute(self, cr, uid, ids, name, args, context, where =''):
        if not ids: return {}
        cr.execute('select move_id,sum(debit) from account_move_line where move_id =ANY(%s) group by move_id',(ids,))
        result = dict(cr.fetchall())
        for id in ids:
            result.setdefault(id, 0.0)
        return result

    def _search_amount(self, cr, uid, obj, name, args, context):
        ids = []
        cr.execute('select move_id,sum(debit) from account_move_line group by move_id')
        result = dict(cr.fetchall())

        for item in args:
            if item[1] == '>=':
                res = [('id', 'in', [k for k,v in result.iteritems() if v >= item[2]])]
            else:
                res = [('id', 'in', [k for k,v in result.iteritems() if v <= item[2]])]
            ids += res

        if not ids:
            return [('id', '>', '0')]

        return ids

    _columns = {
        'name': fields.char('Number', size=64, required=True),
        'ref': fields.char('Reference', size=64),
        'period_id': fields.many2one('account.period', 'Period', required=True, states={'posted':[('readonly',True)]}),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True, states={'posted':[('readonly',True)]}),
        'state': fields.selection([('draft','Draft'), ('posted','Posted')], 'State', required=True, readonly=True,
                                  help='When new account move is created the state will be \'Draft\'. When all the payments are done it will be in \'Posted\' state.'),
        'line_id': fields.one2many('account.move.line', 'move_id', 'Entries', states={'posted':[('readonly',True)]}),
        'to_check': fields.boolean('To Be Verified'),
        'partner_id': fields.related('line_id', 'partner_id', type="many2one", relation="res.partner", string="Partner"),
        'amount': fields.function(_amount_compute, method=True, string='Amount', digits_compute=dp.get_precision('Account'), type='float', fnct_search=_search_amount),
        'date': fields.date('Date', required=True, states={'posted':[('readonly',True)]}),
        'type': fields.selection([
            ('pay_voucher','Cash Payment'),
            ('bank_pay_voucher','Bank Payment'),
            ('rec_voucher','Cash Receipt'),
            ('bank_rec_voucher','Bank Receipt'),
            ('cont_voucher','Contra'),
            ('journal_sale_vou','Journal Sale'),
            ('journal_pur_voucher','Journal Purchase'),
            ('journal_voucher','Journal Voucher'),
            ],'Entry Type', select=True , size=128, readonly=True, states={'draft':[('readonly',False)]}),
        'narration':fields.text('Narration', readonly=True, select=True, states={'draft':[('readonly',False)]}),
        'company_id': fields.related('journal_id','company_id',type='many2one',relation='res.company',string='Company',store=True),
    }
    _defaults = {
        'name': lambda *a: '/',
        'state': lambda *a: 'draft',
        'period_id': _get_period,
        'type' : lambda *a : 'journal_voucher',
        'date': lambda *a:time.strftime('%Y-%m-%d'),
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }

    def _check_centralisation(self, cursor, user, ids):
        for move in self.browse(cursor, user, ids):
            if move.journal_id.centralisation:
                move_ids = self.search(cursor, user, [
                    ('period_id', '=', move.period_id.id),
                    ('journal_id', '=', move.journal_id.id),
                    ])
                if len(move_ids) > 1:
                    return False
        return True

    def _check_period_journal(self, cursor, user, ids):
        for move in self.browse(cursor, user, ids):
            for line in move.line_id:
                if line.period_id.id != move.period_id.id:
                    return False
                if line.journal_id.id != move.journal_id.id:
                    return False
        return True

    _constraints = [
        (_check_centralisation,
            'You cannot create more than one move per period on centralized journal',
            ['journal_id']),
        (_check_period_journal,
            'You cannot create entries on different periods/journals in the same move',
            ['line_id']),
    ]
    def post(self, cr, uid, ids, context=None):
        if self.validate(cr, uid, ids, context) and len(ids):
            for move in self.browse(cr, uid, ids):
                if move.name =='/':
                    new_name = False
                    journal = move.journal_id
                    if journal.sequence_id:
                        c = {'fiscalyear_id': move.period_id.fiscalyear_id.id}
                        new_name = self.pool.get('ir.sequence').get_id(cr, uid, journal.sequence_id.id, context=c)
                    else:
                        raise osv.except_osv(_('Error'), _('No sequence defined in the journal !'))
                    if new_name:
                        self.write(cr, uid, [move.id], {'name':new_name})

            cr.execute('update account_move set state=%s where id =ANY(%s) ',('posted',ids,))
        else:
            raise osv.except_osv(_('Integrity Error !'), _('You can not validate a non-balanced entry !\nMake sure you have configured Payment Term properly !\nIt should contain atleast one Payment Term Line with type "Balance" !'))
        return True

    def button_validate(self, cursor, user, ids, context=None):
        return self.post(cursor, user, ids, context=context)
    
    def button_cancel(self, cr, uid, ids, context={}):
        for line in self.browse(cr, uid, ids, context):
            if not line.journal_id.update_posted:
                raise osv.except_osv(_('Error !'), _('You can not modify a posted entry of this journal !\nYou should set the journal to allow cancelling entries if you want to do that.'))
        if len(ids):
            cr.execute('update account_move set state=%s where id =ANY(%s)',('draft',ids,))
        return True

    def write(self, cr, uid, ids, vals, context={}):
        c = context.copy()
        c['novalidate'] = True
        result = super(osv.osv, self).write(cr, uid, ids, vals, c)
        self.validate(cr, uid, ids, context)
        return result

    #
    # TODO: Check if period is closed !
    #
    def create(self, cr, uid, vals, context={}):
        if 'line_id' in vals:
            if 'journal_id' in vals:
                for l in vals['line_id']:
                    if not l[0]:
                        l[2]['journal_id'] = vals['journal_id']
                context['journal_id'] = vals['journal_id']
            if 'period_id' in vals:
                for l in vals['line_id']:
                    if not l[0]:
                        l[2]['period_id'] = vals['period_id']
                context['period_id'] = vals['period_id']
            else:
                default_period = self._get_period(cr, uid, context)
                for l in vals['line_id']:
                    if not l[0]:
                        l[2]['period_id'] = default_period
                context['period_id'] = default_period

        if 'line_id' in vals:
            c = context.copy()
            c['novalidate'] = True
            result = super(account_move, self).create(cr, uid, vals, c)
            self.validate(cr, uid, [result], context)
        else:
            result = super(account_move, self).create(cr, uid, vals, context)
        return result

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        default.update({'state':'draft', 'name':'/',})
        return super(account_move, self).copy(cr, uid, id, default, context)

    def unlink(self, cr, uid, ids, context={}, check=True):
        toremove = []
        for move in self.browse(cr, uid, ids, context):
            if move['state'] != 'draft':
                raise osv.except_osv(_('UserError'),
                        _('You can not delete posted movement: "%s"!') % \
                                move['name'])
            line_ids = map(lambda x: x.id, move.line_id)
            context['journal_id'] = move.journal_id.id
            context['period_id'] = move.period_id.id
            self.pool.get('account.move.line')._update_check(cr, uid, line_ids, context)
            self.pool.get('account.move.line').unlink(cr, uid, line_ids, context=context)
            toremove.append(move.id)
        result = super(account_move, self).unlink(cr, uid, toremove, context)
        return result

    def _compute_balance(self, cr, uid, id, context={}):
        move = self.browse(cr, uid, [id])[0]
        amount = 0
        for line in move.line_id:
            amount+= (line.debit - line.credit)
        return amount

    def _centralise(self, cr, uid, move, mode, context=None):
        if context is None:
            context = {}

        if mode=='credit':
            account_id = move.journal_id.default_debit_account_id.id
            mode2 = 'debit'
            if not account_id:
                raise osv.except_osv(_('UserError'),
                        _('There is no default default debit account defined \n' \
                                'on journal "%s"') % move.journal_id.name)
        else:
            account_id = move.journal_id.default_credit_account_id.id
            mode2 = 'credit'
            if not account_id:
                raise osv.except_osv(_('UserError'),
                        _('There is no default default credit account defined \n' \
                                'on journal "%s"') % move.journal_id.name)

        # find the first line of this move with the current mode
        # or create it if it doesn't exist
        cr.execute('select id from account_move_line where move_id=%s and centralisation=%s limit 1', (move.id, mode))
        res = cr.fetchone()
        if res:
            line_id = res[0]
        else:
            context.update({'journal_id': move.journal_id.id, 'period_id': move.period_id.id})
            line_id = self.pool.get('account.move.line').create(cr, uid, {
                'name': _(mode.capitalize()+' Centralisation'),
                'centralisation': mode,
                'account_id': account_id,
                'move_id': move.id,
                'journal_id': move.journal_id.id,
                'period_id': move.period_id.id,
                'date': move.period_id.date_stop,
                'debit': 0.0,
                'credit': 0.0,
            }, context)

        # find the first line of this move with the other mode
        # so that we can exclude it from our calculation
        cr.execute('select id from account_move_line where move_id=%s and centralisation=%s limit 1', (move.id, mode2))
        res = cr.fetchone()
        if res:
            line_id2 = res[0]
        else:
            line_id2 = 0

        cr.execute('select sum('+mode+') from account_move_line where move_id=%s and id<>%s', (move.id, line_id2))
        result = cr.fetchone()[0] or 0.0
        cr.execute('update account_move_line set '+mode2+'=%s where id=%s', (result, line_id))
        return True

    #
    # Validate a balanced move. If it is a centralised journal, create a move.
    #
    def validate(self, cr, uid, ids, context={}):
        if context and ('__last_update' in context):
            del context['__last_update']
        ok = True
        for move in self.browse(cr, uid, ids, context):
            #unlink analytic lines on move_lines
            for obj_line in move.line_id:
                for obj in obj_line.analytic_lines:
                    self.pool.get('account.analytic.line').unlink(cr,uid,obj.id)

            journal = move.journal_id
            amount = 0
            line_ids = []
            line_draft_ids = []
            company_id=None
            for line in move.line_id:
                amount += line.debit - line.credit
                line_ids.append(line.id)
                if line.state=='draft':
                    line_draft_ids.append(line.id)

                if not company_id:
                    company_id = line.account_id.company_id.id
                if not company_id == line.account_id.company_id.id:
                    raise osv.except_osv(_('Error'), _("Couldn't create move between different companies"))

                if line.account_id.currency_id:
                    if line.account_id.currency_id.id != line.currency_id.id and (line.account_id.currency_id.id != line.account_id.company_id.currency_id.id or line.currency_id):
                        raise osv.except_osv(_('Error'), _("""Couldn't create move with currency different from the secondary currency of the account "%s - %s". Clear the secondary currency field of the account definition if you want to accept all currencies.""" % (line.account_id.code, line.account_id.name)))

            # Check that the move balances, the tolerance for debit/credit must
            # be smaller than the smallest value according to price accuracy
            # (hence the +1 below)
            # Example:
            #    difference == 0.01 is OK iff price_accuracy <= 1!
            #    difference == 0.0001 is OK iff price_accuracy <= 3!
            if abs(amount) < 10 ** -(int(config['price_accuracy'])+1):
                if not len(line_draft_ids):
                    continue
                self.pool.get('account.move.line').write(cr, uid, line_draft_ids, {
                    'journal_id': move.journal_id.id,
                    'period_id': move.period_id.id,
                    'state': 'valid'
                }, context, check=False)
                todo = []
                account = {}
                account2 = {}
                if journal.type not in ('purchase','sale'):
                    continue

                for line in move.line_id:
                    code = amount = 0
                    key = (line.account_id.id, line.tax_code_id.id)
                    if key in account2:
                        code = account2[key][0]
                        amount = account2[key][1] * (line.debit + line.credit)
                    elif line.account_id.id in account:
                        code = account[line.account_id.id][0]
                        amount = account[line.account_id.id][1] * (line.debit + line.credit)
                    if (code or amount) and not (line.tax_code_id or line.tax_amount):
                        self.pool.get('account.move.line').write(cr, uid, [line.id], {
                            'tax_code_id': code,
                            'tax_amount': amount
                        }, context, check=False)
                #
                # Compute VAT
                #
                continue
            if journal.centralisation:
                self._centralise(cr, uid, move, 'debit', context=context)
                self._centralise(cr, uid, move, 'credit', context=context)
                self.pool.get('account.move.line').write(cr, uid, line_draft_ids, {
                    'state': 'valid'
                }, context, check=False)
                continue
            else:
                self.pool.get('account.move.line').write(cr, uid, line_ids, {
                    'journal_id': move.journal_id.id,
                    'period_id': move.period_id.id,
                    #'tax_code_id': False,
                    #'tax_amount': False,
                    'state': 'draft'
                }, context, check=False)
                ok = False
            if ok:
                list_ids = []
                for tmp in move.line_id:
                    list_ids.append(tmp.id)
                self.pool.get('account.move.line').create_analytic_lines(cr, uid, list_ids, context)
        return ok
account_move()

class account_move_reconcile(osv.osv):
    _name = "account.move.reconcile"
    _description = "Account Reconciliation"
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'type': fields.char('Type', size=16, required=True),
        'line_id': fields.one2many('account.move.line', 'reconcile_id', 'Entry Lines'),
        'line_partial_ids': fields.one2many('account.move.line', 'reconcile_partial_id', 'Partial Entry lines'),
        'create_date': fields.date('Creation date', readonly=True),
    }
    _defaults = {
        'name': lambda self,cr,uid,ctx={}: self.pool.get('ir.sequence').get(cr, uid, 'account.reconcile') or '/',
    }
    def reconcile_partial_check(self, cr, uid, ids, type='auto', context={}):
        total = 0.0
        for rec in self.browse(cr, uid, ids, context):
            for line in rec.line_partial_ids:
                total += (line.debit or 0.0) - (line.credit or 0.0)
        if not total:
            self.pool.get('account.move.line').write(cr, uid,
                map(lambda x: x.id, rec.line_partial_ids),
                {'reconcile_id': rec.id }
            )
        return True

    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        result = []
        for r in self.browse(cr, uid, ids, context):
            total = reduce(lambda y,t: (t.debit or 0.0) - (t.credit or 0.0) + y, r.line_partial_ids, 0.0)
            if total:
                name = '%s (%.2f)' % (r.name, total)
                result.append((r.id,name))
            else:
                result.append((r.id,r.name))
        return result


account_move_reconcile()

#----------------------------------------------------------
# Tax
#----------------------------------------------------------
"""
a documenter
child_depend: la taxe depend des taxes filles
"""
class account_tax_code(osv.osv):
    """
    A code for the tax object.

    This code is used for some tax declarations.
    """
    def _sum(self, cr, uid, ids, name, args, context, where =''):
        ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])
        if context.get('based_on', 'invoices') == 'payments':
            cr.execute('SELECT line.tax_code_id, sum(line.tax_amount) \
                    FROM account_move_line AS line, \
                        account_move AS move \
                        LEFT JOIN account_invoice invoice ON \
                            (invoice.move_id = move.id) \
                    WHERE line.tax_code_id =ANY(%s) '+where+' \
                        AND move.id = line.move_id \
                        AND ((invoice.state = \'paid\') \
                            OR (invoice.id IS NULL)) \
                    GROUP BY line.tax_code_id',(ids2,))
        else:
            cr.execute('SELECT line.tax_code_id, sum(line.tax_amount) \
                    FROM account_move_line AS line \
                    WHERE line.tax_code_id =ANY(%s) '+where+' \
                    GROUP BY line.tax_code_id',(ids2,))
        res=dict(cr.fetchall())
        for record in self.browse(cr, uid, ids, context):
            def _rec_get(record):
                amount = res.get(record.id, 0.0)
                for rec in record.child_ids:
                    amount += _rec_get(rec) * rec.sign
                return amount
            res[record.id] = round(_rec_get(record), self.pool.get('decimal.precision').precision_get(cr, uid, 'Account'))
        return res

    def _sum_year(self, cr, uid, ids, name, args, context):
        if 'fiscalyear_id' in context and context['fiscalyear_id']:
            fiscalyear_id = context['fiscalyear_id']
        else:
            fiscalyear_id = self.pool.get('account.fiscalyear').find(cr, uid, exception=False)
        where = ''
        if fiscalyear_id:
            pids = map(lambda x: str(x.id), self.pool.get('account.fiscalyear').browse(cr, uid, fiscalyear_id).period_ids)
            if pids:
                where = ' and period_id in (' + (','.join(pids))+')'
        return self._sum(cr, uid, ids, name, args, context,
                where=where)

    def _sum_period(self, cr, uid, ids, name, args, context):
        if 'period_id' in context and context['period_id']:
            period_id = context['period_id']
        else:
            period_id = self.pool.get('account.period').find(cr, uid)
            if not len(period_id):
                return dict.fromkeys(ids, 0.0)
            period_id = period_id[0]
        return self._sum(cr, uid, ids, name, args, context,
                where=' and line.period_id='+str(period_id))

    _name = 'account.tax.code'
    _description = 'Tax Code'
    _rec_name = 'code'
    _columns = {
        'name': fields.char('Tax Case Name', size=64, required=True, translate=True),
        'code': fields.char('Case Code', size=64),
        'info': fields.text('Description'),
        'sum': fields.function(_sum_year, method=True, string="Year Sum"),
        'sum_period': fields.function(_sum_period, method=True, string="Period Sum"),
        'parent_id': fields.many2one('account.tax.code', 'Parent Code', select=True),
        'child_ids': fields.one2many('account.tax.code', 'parent_id', 'Child Codes'),
        'line_ids': fields.one2many('account.move.line', 'tax_code_id', 'Lines'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'sign': fields.float('Sign for parent', required=True),
        'notprintable':fields.boolean("Not Printable in Invoice", help="Check this box if you don't want any VAT related to this Tax Code to appear on invoices"),
    }


    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=80):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = self.search(cr, user, ['|',('name',operator,name),('code',operator,name)] + args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context)


    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['name','code'], context, load='_classic_write')
        return [(x['id'], (x['code'] and x['code'] + ' - ' or '') + x['name']) \
                for x in reads]

    def _default_company(self, cr, uid, context={}):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            return user.company_id.id
        return self.pool.get('res.company').search(cr, uid, [('parent_id', '=', False)])[0]
    _defaults = {
        'company_id': _default_company,
        'sign': lambda *args: 1.0,
        'notprintable': lambda *a: False,
    }
    def _check_recursion(self, cr, uid, ids):
        level = 100
        while len(ids):
            cr.execute('select distinct parent_id from account_tax_code where id =ANY(%s)',(ids,))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True


    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        default.update({'line_ids': []})
        return super(account_tax_code, self).copy(cr, uid, id, default, context)

    _constraints = [
        (_check_recursion, 'Error ! You can not create recursive accounts.', ['parent_id'])
    ]
    _order = 'code,name'
account_tax_code()

class account_tax(osv.osv):
    """
    A tax object.

    Type: percent, fixed, none, code
        PERCENT: tax = price * amount
        FIXED: tax = price + amount
        NONE: no tax line
        CODE: execute python code. localcontext = {'price_unit':pu, 'address':address_object}
            return result in the context
            Ex: result=round(price_unit*0.21,4)
    """
    _name = 'account.tax'
    _description = 'Tax'
    _columns = {
        'name': fields.char('Tax Name', size=64, required=True, translate=True, help="This name will be displayed on reports"),
        'sequence': fields.integer('Sequence', required=True, help="The sequence field is used to order the tax lines from the lowest sequences to the higher ones. The order is important if you have a tax with several tax children. In this case, the evaluation order is important."),
        'amount': fields.float('Amount', required=True, digits=(14,4), help="For Tax Type percent enter % ratio between 0-1."),
        'active': fields.boolean('Active', help="If the active field is set to true, it will allow you to hide the tax without removing it."),
        'type': fields.selection( [('percent','Percent'), ('fixed','Fixed'), ('none','None'), ('code','Python Code'),('balance','Balance')], 'Tax Type', required=True,
            help="The computation method for the tax amount."),
        'applicable_type': fields.selection( [('true','True'), ('code','Python Code')], 'Applicable Type', required=True,
            help="If not applicable (computed through a Python code), the tax won't appear on the invoice."),
        'domain':fields.char('Domain', size=32, help="This field is only used if you develop your own module allowing developers to create specific taxes in a custom domain."),
        'account_collected_id':fields.many2one('account.account', 'Invoice Tax Account'),
        'account_paid_id':fields.many2one('account.account', 'Refund Tax Account'),
        'parent_id':fields.many2one('account.tax', 'Parent Tax Account', select=True),
        'child_ids':fields.one2many('account.tax', 'parent_id', 'Child Tax Accounts'),
        'child_depend':fields.boolean('Tax on Children', help="Set if the tax computation is based on the computation of child taxes rather than on the total amount."),
        'python_compute':fields.text('Python Code'),
        'python_compute_inv':fields.text('Python Code (reverse)'),
        'python_applicable':fields.text('Python Code'),
        'tax_group': fields.selection([('vat','VAT'),('other','Other')], 'Tax Group', help="If a default tax is given in the partner it only overrides taxes from accounts (or products) in the same group."),

        #
        # Fields used for the VAT declaration
        #
        'base_code_id': fields.many2one('account.tax.code', 'Base Code', help="Use this code for the VAT declaration."),
        'tax_code_id': fields.many2one('account.tax.code', 'Tax Code', help="Use this code for the VAT declaration."),
        'base_sign': fields.float('Base Code Sign', help="Usually 1 or -1."),
        'tax_sign': fields.float('Tax Code Sign', help="Usually 1 or -1."),

        # Same fields for refund invoices

        'ref_base_code_id': fields.many2one('account.tax.code', 'Refund Base Code', help="Use this code for the VAT declaration."),
        'ref_tax_code_id': fields.many2one('account.tax.code', 'Refund Tax Code', help="Use this code for the VAT declaration."),
        'ref_base_sign': fields.float('Base Code Sign', help="Usually 1 or -1."),
        'ref_tax_sign': fields.float('Tax Code Sign', help="Usually 1 or -1."),
        'include_base_amount': fields.boolean('Included in base amount', help="Indicates if the amount of tax must be included in the base amount for the computation of the next taxes"),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'description': fields.char('Tax Code',size=32),
        'price_include': fields.boolean('Tax Included in Price', help="Check this if the price you use on the product and invoices includes this tax."),
        'type_tax_use': fields.selection([('sale','Sale'),('purchase','Purchase'),('all','All')], 'Tax Application', required=True)

    }
    def search(self, cr, uid, args, offset=0, limit=None, order=None,
            context=None, count=False):
        if context and context.has_key('type'):
            if context['type'] in ('out_invoice','out_refund'):
                args.append(('type_tax_use','in',['sale','all']))
            elif context['type'] in ('in_invoice','in_refund'):
                args.append(('type_tax_use','in',['purchase','all']))
        return super(account_tax, self).search(cr, uid, args, offset, limit, order, context, count)

    def name_get(self, cr, uid, ids, context={}):
        if not len(ids):
            return []
        res = []
        for record in self.read(cr, uid, ids, ['description','name'], context):
            name = record['description'] and record['description'] or record['name']
            res.append((record['id'],name ))
        return res

    def _default_company(self, cr, uid, context={}):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            return user.company_id.id
        return self.pool.get('res.company').search(cr, uid, [('parent_id', '=', False)])[0]
    _defaults = {
        'python_compute': lambda *a: '''# price_unit\n# address : res.partner.address object or False\n# product : product.product object or None\n# partner : res.partner object or None\n\nresult = price_unit * 0.10''',
        'python_compute_inv': lambda *a: '''# price_unit\n# address : res.partner.address object or False\n# product : product.product object or False\n\nresult = price_unit * 0.10''',
        'applicable_type': lambda *a: 'true',
        'type': lambda *a: 'percent',
        'amount': lambda *a: 0,
        'price_include': lambda *a: 0,
        'active': lambda *a: 1,
        'type_tax_use': lambda *a: 'all',
        'sequence': lambda *a: 1,
        'tax_group': lambda *a: 'vat',
        'ref_tax_sign': lambda *a: 1,
        'ref_base_sign': lambda *a: 1,
        'tax_sign': lambda *a: 1,
        'base_sign': lambda *a: 1,
        'include_base_amount': lambda *a: False,
        'company_id': _default_company,
    }
    _order = 'sequence'

    def _applicable(self, cr, uid, taxes, price_unit, address_id=None, product=None, partner=None):
        res = []
        for tax in taxes:
            if tax.applicable_type=='code':
                localdict = {'price_unit':price_unit, 'address':self.pool.get('res.partner.address').browse(cr, uid, address_id), 'product':product, 'partner':partner}
                exec tax.python_applicable in localdict
                if localdict.get('result', False):
                    res.append(tax)
            else:
                res.append(tax)
        return res

    def _unit_compute(self, cr, uid, taxes, price_unit, address_id=None, product=None, partner=None, quantity=0):
        taxes = self._applicable(cr, uid, taxes, price_unit, address_id, product, partner)

        res = []
        cur_price_unit=price_unit
        for tax in taxes:
            # we compute the amount for the current tax object and append it to the result

            data = {'id':tax.id,
                            'name':tax.description and tax.description + " - " + tax.name or tax.name,
                            'account_collected_id':tax.account_collected_id.id,
                            'account_paid_id':tax.account_paid_id.id,
                            'base_code_id': tax.base_code_id.id,
                            'ref_base_code_id': tax.ref_base_code_id.id,
                            'sequence': tax.sequence,
                            'base_sign': tax.base_sign,
                            'tax_sign': tax.tax_sign,
                            'ref_base_sign': tax.ref_base_sign,
                            'ref_tax_sign': tax.ref_tax_sign,
                            'price_unit': cur_price_unit,
                            'tax_code_id': tax.tax_code_id.id,
                            'ref_tax_code_id': tax.ref_tax_code_id.id,
            }
            res.append(data)
            if tax.type=='percent':
                amount = cur_price_unit * tax.amount
                data['amount'] = amount

            elif tax.type=='fixed':
                data['amount'] = tax.amount
                data['tax_amount']=quantity
               # data['amount'] = quantity
            elif tax.type=='code':
                address = address_id and self.pool.get('res.partner.address').browse(cr, uid, address_id) or None
                localdict = {'price_unit':cur_price_unit, 'address':address, 'product':product, 'partner':partner}
                exec tax.python_compute in localdict
                amount = localdict['result']
                data['amount'] = amount
            elif tax.type=='balance':
                data['amount'] = cur_price_unit - reduce(lambda x,y: y.get('amount',0.0)+x, res, 0.0)
                data['balance'] = cur_price_unit

            amount2 = data['amount']
            if len(tax.child_ids):
                if tax.child_depend:
                    latest = res.pop()
                amount = amount2
                child_tax = self._unit_compute(cr, uid, tax.child_ids, amount, address_id, product, partner, quantity)
                res.extend(child_tax)
                if tax.child_depend:
                    for r in res:
                        for name in ('base','ref_base'):
                            if latest[name+'_code_id'] and latest[name+'_sign'] and not r[name+'_code_id']:
                                r[name+'_code_id'] = latest[name+'_code_id']
                                r[name+'_sign'] = latest[name+'_sign']
                                r['price_unit'] = latest['price_unit']
                                latest[name+'_code_id'] = False
                        for name in ('tax','ref_tax'):
                            if latest[name+'_code_id'] and latest[name+'_sign'] and not r[name+'_code_id']:
                                r[name+'_code_id'] = latest[name+'_code_id']
                                r[name+'_sign'] = latest[name+'_sign']
                                r['amount'] = data['amount']
                                latest[name+'_code_id'] = False
            if tax.include_base_amount:
                cur_price_unit+=amount2
        return res

    def compute_all(self, cr, uid, taxes, price_unit, quantity, address_id=None, product=None, partner=None):
        """
        RETURN: {
                'total': 0.0,                # Total without taxes
                'total_included: 0.0,        # Total with taxes
                'taxes': []                  # List of taxes, see compute for the format
            }
        """
        precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        totalin = totalex = round(price_unit * quantity, precision)
        tin = []
        tex = []
        for tax in taxes:
            if tax.price_include:
                tin.append(tax)
            else:
                tex.append(tax)
        tin = self.compute_inv(cr, uid, tin, price_unit, quantity, address_id=address_id, product=product, partner=partner)
        for r in tin:
            totalex -= r['amount']
        tex = self._compute(cr, uid, tex, totalex/quantity, quantity, address_id=address_id, product=product, partner=partner)
        for r in tex:
            totalin += r['amount']
        return {
            'total': totalex,
            'total_included': totalin,
            'taxes': tin + tex
        }

    def compute(self, cr, uid, taxes, price_unit, quantity, address_id=None, product=None, partner=None):
        logger = netsvc.Logger()
        logger.notifyChannel("warning", netsvc.LOG_WARNING,
            "Deprecated, use compute_all(...)['taxes'] instead of compute(...) to manage prices with tax included")
        return self._compute(cr, uid, taxes, price_unit, quantity, address_id, product, partner)

    def _compute(self, cr, uid, taxes, price_unit, quantity, address_id=None, product=None, partner=None):
        """
        Compute tax values for given PRICE_UNIT, QUANTITY and a buyer/seller ADDRESS_ID.

        RETURN:
            [ tax ]
            tax = {'name':'', 'amount':0.0, 'account_collected_id':1, 'account_paid_id':2}
            one tax for each tax id in IDS and their childs
        """
        res = self._unit_compute(cr, uid, taxes, price_unit, address_id, product, partner, quantity)
        total = 0.0
        for r in res:
            if r.get('balance',False):
                r['amount'] = round(r['balance'] * quantity, self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')) - total
            else:
                r['amount'] = round(r['amount'] * quantity, self.pool.get('decimal.precision').precision_get(cr, uid, 'Account'))
                total += r['amount']
        return res

    def _unit_compute_inv(self, cr, uid, taxes, price_unit, address_id=None, product=None, partner=None):
        taxes = self._applicable(cr, uid, taxes, price_unit, address_id, product, partner)

        res = []
        taxes.reverse()
        cur_price_unit = price_unit

        tax_parent_tot = 0.0
        for tax in taxes:
            if (tax.type=='percent') and not tax.include_base_amount:
                tax_parent_tot += tax.amount

        for tax in taxes:
            if (tax.type=='fixed') and not tax.include_base_amount:
                cur_price_unit -= tax.amount

        for tax in taxes:
            if tax.type=='percent':
                if tax.include_base_amount:
                    amount = cur_price_unit - (cur_price_unit / (1 + tax.amount))
                else:
                    amount = (cur_price_unit / (1 + tax_parent_tot)) * tax.amount

            elif tax.type=='fixed':
                amount = tax.amount

            elif tax.type=='code':
                address = address_id and self.pool.get('res.partner.address').browse(cr, uid, address_id) or None
                localdict = {'price_unit':cur_price_unit, 'address':address, 'product':product, 'partner':partner}
                exec tax.python_compute_inv in localdict
                amount = localdict['result']
            elif tax.type=='balance':
                amount = cur_price_unit - reduce(lambda x,y: y.get('amount',0.0)+x, res, 0.0)
#                data['balance'] = cur_price_unit


            if tax.include_base_amount:
                cur_price_unit -= amount
                todo = 0
            else:
                todo = 1
            res.append({
                'id': tax.id,
                'todo': todo,
                'name': tax.name,
                'amount': amount,
                'account_collected_id': tax.account_collected_id.id,
                'account_paid_id': tax.account_paid_id.id,
                'base_code_id': tax.base_code_id.id,
                'ref_base_code_id': tax.ref_base_code_id.id,
                'sequence': tax.sequence,
                'base_sign': tax.base_sign,
                'tax_sign': tax.tax_sign,
                'ref_base_sign': tax.ref_base_sign,
                'ref_tax_sign': tax.ref_tax_sign,
                'price_unit': cur_price_unit,
                'tax_code_id': tax.tax_code_id.id,
                'ref_tax_code_id': tax.ref_tax_code_id.id,
            })
            if len(tax.child_ids):
                if tax.child_depend:
                    del res[-1]
                    amount = price_unit

            parent_tax = self._unit_compute_inv(cr, uid, tax.child_ids, amount, address_id, product, partner)
            res.extend(parent_tax)

        total = 0.0
        for r in res:
            if r['todo']:
                total += r['amount']
        for r in res:
            r['price_unit'] -= total
            r['todo'] = 0
        return res

    def compute_inv(self, cr, uid, taxes, price_unit, quantity, address_id=None, product=None, partner=None):
        """
        Compute tax values for given PRICE_UNIT, QUANTITY and a buyer/seller ADDRESS_ID.
        Price Unit is a VAT included price

        RETURN:
            [ tax ]
            tax = {'name':'', 'amount':0.0, 'account_collected_id':1, 'account_paid_id':2}
            one tax for each tax id in IDS and their childs
        """
        res = self._unit_compute_inv(cr, uid, taxes, price_unit, address_id, product, partner=None)
        total = 0.0
        for r in res:
            prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
            if r.get('balance',False):
                r['amount'] = round(r['balance'] * quantity, prec) - total
            else:
                r['amount'] = round(r['amount'] * quantity, prec)
                total += r['amount']
        return res
account_tax()

# ---------------------------------------------------------
# Account Entries Models
# ---------------------------------------------------------

class account_model(osv.osv):
    _name = "account.model"
    _description = "Account Model"
    _columns = {
        'name': fields.char('Model Name', size=64, required=True, help="This is a model for recurring accounting entries"),
        'ref': fields.char('Reference', size=64),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True),
        'lines_id': fields.one2many('account.model.line', 'model_id', 'Model Entries'),
        'legend' :fields.text('Legend',readonly=True,size=100),
    }

    _defaults = {
        'legend': lambda self, cr, uid, context:_('You can specify year, month and date in the name of the model using the following labels:\n\n%(year)s : To Specify Year \n%(month)s : To Specify Month \n%(date)s : Current Date\n\ne.g. My model on %(date)s'),
    }
    def generate(self, cr, uid, ids, datas={}, context={}):
        move_ids = []
        for model in self.browse(cr, uid, ids, context):
            context.update({'date':datas['date']})
            period_id = self.pool.get('account.period').find(cr, uid, dt=context.get('date',False))
            if not period_id:
                raise osv.except_osv(_('No period found !'), _('Unable to find a valid period !'))
            period_id = period_id[0]
            move_id = self.pool.get('account.move').create(cr, uid, {
                'ref': model.ref,
                'period_id': period_id,
                'journal_id': model.journal_id.id,
                'date': context.get('date',time.strftime('%Y-%m-%d'))
            })
            move_ids.append(move_id)
            for line in model.lines_id:
                val = {
                    'move_id': move_id,
                    'journal_id': model.journal_id.id,
                    'period_id': period_id
                }
                val.update({
                    'name': line.name,
                    'quantity': line.quantity,
                    'debit': line.debit,
                    'credit': line.credit,
                    'account_id': line.account_id.id,
                    'move_id': move_id,
                    'ref': line.ref,
                    'partner_id': line.partner_id.id,
                    'date': context.get('date',time.strftime('%Y-%m-%d')),
                    'date_maturity': time.strftime('%Y-%m-%d')
                })
                c = context.copy()
                c.update({'journal_id': model.journal_id.id,'period_id': period_id})
                self.pool.get('account.move.line').create(cr, uid, val, context=c)
        return move_ids
account_model()

class account_model_line(osv.osv):
    _name = "account.model.line"
    _description = "Account Model Entries"
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'sequence': fields.integer('Sequence', required=True, help="The sequence field is used to order the resources from lower sequences to higher ones"),
        'quantity': fields.float('Quantity', digits_compute=dp.get_precision('Account'), help="The optional quantity on entries"),
        'debit': fields.float('Debit', digits_compute=dp.get_precision('Account')),
        'credit': fields.float('Credit', digits_compute=dp.get_precision('Account')),

        'account_id': fields.many2one('account.account', 'Account', required=True, ondelete="cascade"),

        'model_id': fields.many2one('account.model', 'Model', required=True, ondelete="cascade", select=True),

        'ref': fields.char('Reference', size=16),

        'amount_currency': fields.float('Amount Currency', help="The amount expressed in an optional other currency."),
        'currency_id': fields.many2one('res.currency', 'Currency'),

        'partner_id': fields.many2one('res.partner', 'Partner'),
        'date_maturity': fields.selection([('today','Date of the day'), ('partner','Partner Payment Term')], 'Maturity date', help="The maturity date of the generated entries for this model. You can choose between the creation date or the creation date of the entries plus the partner payment terms."),
        'date': fields.selection([('today','Date of the day'), ('partner','Partner Payment Term')], 'Current Date', required=True, help="The date of the generated entries"),
    }
    _defaults = {
        'date': lambda *a: 'today'
    }
    _order = 'sequence'
    _sql_constraints = [
        ('credit_debit1', 'CHECK (credit*debit=0)',  'Wrong credit or debit value in model (Credit Or Debit Must Be "0")!'),
        ('credit_debit2', 'CHECK (credit+debit>=0)', 'Wrong credit or debit value in model (Credit + Debit Must Be greater "0")!'),
    ]
account_model_line()

# ---------------------------------------------------------
# Account Subscription
# ---------------------------------------------------------


class account_subscription(osv.osv):
    _name = "account.subscription"
    _description = "Account Subscription"
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'ref': fields.char('Reference', size=16),
        'model_id': fields.many2one('account.model', 'Model', required=True),

        'date_start': fields.date('Start Date', required=True),
        'period_total': fields.integer('Number of Periods', required=True),
        'period_nbr': fields.integer('Period', required=True),
        'period_type': fields.selection([('day','days'),('month','month'),('year','year')], 'Period Type', required=True),
        'state': fields.selection([('draft','Draft'),('running','Running'),('done','Done')], 'State', required=True, readonly=True),

        'lines_id': fields.one2many('account.subscription.line', 'subscription_id', 'Subscription Lines')
    }
    _defaults = {
        'date_start': lambda *a: time.strftime('%Y-%m-%d'),
        'period_type': lambda *a: 'month',
        'period_total': lambda *a: 12,
        'period_nbr': lambda *a: 1,
        'state': lambda *a: 'draft',
    }
    def state_draft(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'draft'})
        return False

    def check(self, cr, uid, ids, context={}):
        todone = []
        for sub in self.browse(cr, uid, ids, context):
            ok = True
            for line in sub.lines_id:
                if not line.move_id.id:
                    ok = False
                    break
            if ok:
                todone.append(sub.id)
        if len(todone):
            self.write(cr, uid, todone, {'state':'done'})
        return False

    def remove_line(self, cr, uid, ids, context={}):
        toremove = []
        for sub in self.browse(cr, uid, ids, context):
            for line in sub.lines_id:
                if not line.move_id.id:
                    toremove.append(line.id)
        if len(toremove):
            self.pool.get('account.subscription.line').unlink(cr, uid, toremove)
        self.write(cr, uid, ids, {'state':'draft'})
        return False

    def compute(self, cr, uid, ids, context={}):
        for sub in self.browse(cr, uid, ids, context):
            ds = sub.date_start
            for i in range(sub.period_total):
                self.pool.get('account.subscription.line').create(cr, uid, {
                    'date': ds,
                    'subscription_id': sub.id,
                })
                if sub.period_type=='day':
                    ds = (datetime.strptime(ds, '%Y-%m-%d') + relativedelta(days=sub.period_nbr)).strftime('%Y-%m-%d')
                if sub.period_type=='month':
                    ds = (datetime.strptime(ds, '%Y-%m-%d') + relativedelta(months=sub.period_nbr)).strftime('%Y-%m-%d')
                if sub.period_type=='year':
                    ds = (datetime.strptime(ds, '%Y-%m-%d') + relativedelta(years=sub.period_nbr)).strftime('%Y-%m-%d')
        self.write(cr, uid, ids, {'state':'running'})
        return True
account_subscription()

class account_subscription_line(osv.osv):
    _name = "account.subscription.line"
    _description = "Account Subscription Line"
    _columns = {
        'subscription_id': fields.many2one('account.subscription', 'Subscription', required=True, select=True),
        'date': fields.date('Date', required=True),
        'move_id': fields.many2one('account.move', 'Entry'),
    }
    _defaults = {
    }
    def move_create(self, cr, uid, ids, context={}):
        tocheck = {}
        for line in self.browse(cr, uid, ids, context):
            datas = {
                'date': line.date,
            }
            ids = self.pool.get('account.model').generate(cr, uid, [line.subscription_id.model_id.id], datas, context)
            tocheck[line.subscription_id.id] = True
            self.write(cr, uid, [line.id], {'move_id':ids[0]})
        if tocheck:
            self.pool.get('account.subscription').check(cr, uid, tocheck.keys(), context)
        return True
    _rec_name = 'date'
account_subscription_line()

#  ---------------------------------------------------------------
#   Account Templates : Account, Tax, Tax Code and chart. + Wizard
#  ---------------------------------------------------------------

class account_tax_template(osv.osv):
    _name = 'account.tax.template'
account_tax_template()

class account_account_template(osv.osv):
    _order = "code"
    _name = "account.account.template"
    _description ='Templates for Accounts'

    _columns = {
        'name': fields.char('Name', size=128, required=True, select=True),
        'currency_id': fields.many2one('res.currency', 'Secondary Currency', help="Forces all moves for this account to have this secondary currency."),
        'code': fields.char('Code', size=64),
        'type': fields.selection([
            ('receivable','Receivable'),
            ('payable','Payable'),
            ('view','View'),
            ('consolidation','Consolidation'),
            ('other','Others'),
            ('closed','Closed'),
            ], 'Internal Type', required=True,help="This type is used to differentiate types with "\
            "special effects in Open ERP: view can not have entries, consolidation are accounts that "\
            "can have children accounts for multi-company consolidations, payable/receivable are for "\
            "partners accounts (for debit/credit computations), closed for depreciated accounts."),
        'user_type': fields.many2one('account.account.type', 'Account Type', required=True,
            help="These types are defined according to your country. The type contains more information "\
            "about the account and its specificities."),
        'reconcile': fields.boolean('Allow Reconciliation', help="Check this option if you want the user to reconcile entries in this account."),
        'shortcut': fields.char('Shortcut', size=12),
        'note': fields.text('Note'),
        'parent_id': fields.many2one('account.account.template','Parent Account Template', ondelete='cascade'),
        'child_parent_ids':fields.one2many('account.account.template','parent_id','Children'),
        'tax_ids': fields.many2many('account.tax.template', 'account_account_template_tax_rel','account_id','tax_id', 'Default Taxes'),
        'nocreate': fields.boolean('Optional create', help="If checked, the new chart of accounts will not contain this by default."),
    }

    _defaults = {
        'reconcile': lambda *a: False,
        'type' : lambda *a :'view',
        'nocreate': lambda *a: False,
    }

    def _check_recursion(self, cr, uid, ids):
        level = 100
        while len(ids):
            cr.execute('select parent_id from account_account_template where id =ANY(%s)',(ids,))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

    _constraints = [
        (_check_recursion, 'Error ! You can not create recursive account templates.', ['parent_id'])
    ]


    def name_get(self, cr, uid, ids, context={}):
        if not len(ids):
            return []
        reads = self.read(cr, uid, ids, ['name','code'], context)
        res = []
        for record in reads:
            name = record['name']
            if record['code']:
                name = record['code']+' '+name
            res.append((record['id'],name ))
        return res

account_account_template()

class account_add_tmpl_wizard(osv.osv_memory):
    """Add one more account from the template.

    With the 'nocreate' option, some accounts may not be created. Use this to add them later."""
    _name = 'account.addtmpl.wizard'

    def _get_def_cparent(self, cr, uid, context):
        acc_obj=self.pool.get('account.account')
        tmpl_obj=self.pool.get('account.account.template')
        #print "Searching for ",context
        tids=tmpl_obj.read(cr, uid, [context['tmpl_ids']],['parent_id'])
        if not tids or not tids[0]['parent_id']:
            return False
        ptids = tmpl_obj.read(cr, uid, [tids[0]['parent_id'][0]],['code'])
        res = None
        if not ptids or not ptids[0]['code']:
            raise osv.except_osv(_('Error !'), _('Cannot locate parent code for template account!'))
            res = acc_obj.search(cr,uid,[('code','=',ptids[0]['code'])])

        return res and res[0] or False

    _columns = {
        'cparent_id':fields.many2one('account.account', 'Parent target', help="Creates an account with the selected template under this existing parent.", required=True),
    }
    _defaults = {
        'cparent_id': _get_def_cparent,
    }

    def action_create(self,cr,uid,ids,context=None):
        acc_obj=self.pool.get('account.account')
        tmpl_obj=self.pool.get('account.account.template')
        data= self.read(cr,uid,ids)
        company_id = acc_obj.read(cr,uid,[data[0]['cparent_id']],['company_id'])[0]['company_id'][0]
        account_template = tmpl_obj.browse(cr,uid,context['tmpl_ids'])
        #tax_ids = []
        #for tax in account_template.tax_ids:
        #    tax_ids.append(tax_template_ref[tax.id])
        vals={
            'name': account_template.name,
            #'sign': account_template.sign,
            'currency_id': account_template.currency_id and account_template.currency_id.id or False,
            'code': account_template.code,
            'type': account_template.type,
            'user_type': account_template.user_type and account_template.user_type.id or False,
            'reconcile': account_template.reconcile,
            'shortcut': account_template.shortcut,
            'note': account_template.note,
            'parent_id': data[0]['cparent_id'],
            # 'tax_ids': [(6,0,tax_ids)], todo!!
            'company_id': company_id,
            }
        # print "Creating:", vals
        new_account = acc_obj.create(cr,uid,vals)
        return {'type':'state', 'state': 'end' }

    def action_cancel(self,cr,uid,ids,context=None):
        return { 'type': 'state', 'state': 'end' }

account_add_tmpl_wizard()

class account_tax_code_template(osv.osv):

    _name = 'account.tax.code.template'
    _description = 'Tax Code Template'
    _order = 'code'
    _rec_name = 'code'
    _columns = {
        'name': fields.char('Tax Case Name', size=64, required=True),
        'code': fields.char('Case Code', size=64),
        'info': fields.text('Description'),
        'parent_id': fields.many2one('account.tax.code.template', 'Parent Code', select=True),
        'child_ids': fields.one2many('account.tax.code.template', 'parent_id', 'Child Codes'),
        'sign': fields.float('Sign for parent', required=True),
        'notprintable':fields.boolean("Not Printable in Invoice", help="Check this box if you don't want any VAT related to this Tax Code to appear on invoices"),
    }

    _defaults = {
        'sign': lambda *args: 1.0,
        'notprintable': lambda *a: False,
    }

    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['name','code'], context, load='_classic_write')
        return [(x['id'], (x['code'] and x['code'] + ' - ' or '') + x['name']) \
                for x in reads]

    def _check_recursion(self, cr, uid, ids):
        level = 100
        while len(ids):
            cr.execute('select distinct parent_id from account_tax_code_template where id =ANY(%s)',(ids,))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

    _constraints = [
        (_check_recursion, 'Error ! You can not create recursive Tax Codes.', ['parent_id'])
    ]
    _order = 'code,name'
account_tax_code_template()


class account_chart_template(osv.osv):
    _name="account.chart.template"
    _description= "Templates for Account Chart"

    _columns={
        'name': fields.char('Name', size=64, required=True),
        'account_root_id': fields.many2one('account.account.template','Root Account',required=True,domain=[('parent_id','=',False)]),
        'tax_code_root_id': fields.many2one('account.tax.code.template','Root Tax Code',required=True,domain=[('parent_id','=',False)]),
        'tax_template_ids': fields.one2many('account.tax.template', 'chart_template_id', 'Tax Template List', help='List of all the taxes that have to be installed by the wizard'),
        'bank_account_view_id': fields.many2one('account.account.template','Bank Account',required=True),
        'property_account_receivable': fields.many2one('account.account.template','Receivable Account'),
        'property_account_payable': fields.many2one('account.account.template','Payable Account'),
        'property_account_expense_categ': fields.many2one('account.account.template','Expense Category Account'),
        'property_account_income_categ': fields.many2one('account.account.template','Income Category Account'),
        'property_account_expense': fields.many2one('account.account.template','Expense Account on Product Template'),
        'property_account_income': fields.many2one('account.account.template','Income Account on Product Template'),
    }

account_chart_template()

class account_tax_template(osv.osv):

    _name = 'account.tax.template'
    _description = 'Templates for Taxes'

    _columns = {
        'chart_template_id': fields.many2one('account.chart.template', 'Chart Template', required=True),
        'name': fields.char('Tax Name', size=64, required=True),
        'sequence': fields.integer('Sequence', required=True, help="The sequence field is used to order the taxes lines from lower sequences to higher ones. The order is important if you have a tax that has several tax children. In this case, the evaluation order is important."),
        'amount': fields.float('Amount', required=True, digits=(14,4), help="For Tax Type percent enter % ratio between 0-1."),
        'type': fields.selection( [('percent','Percent'), ('fixed','Fixed'), ('none','None'), ('code','Python Code')], 'Tax Type', required=True),
        'applicable_type': fields.selection( [('true','True'), ('code','Python Code')], 'Applicable Type', required=True, help="If not applicable (computed through a Python code), the tax won't appear on the invoice."),
        'domain':fields.char('Domain', size=32, help="This field is only used if you develop your own module allowing developers to create specific taxes in a custom domain."),
        'account_collected_id':fields.many2one('account.account.template', 'Invoice Tax Account'),
        'account_paid_id':fields.many2one('account.account.template', 'Refund Tax Account'),
        'parent_id':fields.many2one('account.tax.template', 'Parent Tax Account', select=True),
        'child_depend':fields.boolean('Tax on Children', help="Set if the tax computation is based on the computation of child taxes rather than on the total amount."),
        'python_compute':fields.text('Python Code'),
        'python_compute_inv':fields.text('Python Code (reverse)'),
        'python_applicable':fields.text('Python Code'),
        'tax_group': fields.selection([('vat','VAT'),('other','Other')], 'Tax Group', help="If a default tax if given in the partner it only override taxes from account (or product) of the same group."),

        #
        # Fields used for the VAT declaration
        #
        'base_code_id': fields.many2one('account.tax.code.template', 'Base Code', help="Use this code for the VAT declaration."),
        'tax_code_id': fields.many2one('account.tax.code.template', 'Tax Code', help="Use this code for the VAT declaration."),
        'base_sign': fields.float('Base Code Sign', help="Usually 1 or -1."),
        'tax_sign': fields.float('Tax Code Sign', help="Usually 1 or -1."),

        # Same fields for refund invoices

        'ref_base_code_id': fields.many2one('account.tax.code.template', 'Refund Base Code', help="Use this code for the VAT declaration."),
        'ref_tax_code_id': fields.many2one('account.tax.code.template', 'Refund Tax Code', help="Use this code for the VAT declaration."),
        'ref_base_sign': fields.float('Base Code Sign', help="Usually 1 or -1."),
        'ref_tax_sign': fields.float('Tax Code Sign', help="Usually 1 or -1."),
        'include_base_amount': fields.boolean('Include in Base Amount', help="Set if the amount of tax must be included in the base amount before computing the next taxes."),
        'description': fields.char('Internal Name', size=32),
        'type_tax_use': fields.selection([('sale','Sale'),('purchase','Purchase'),('all','All')], 'Tax Use In', required=True,)
    }

    def name_get(self, cr, uid, ids, context={}):
        if not len(ids):
            return []
        res = []
        for record in self.read(cr, uid, ids, ['description','name'], context):
            name = record['description'] and record['description'] or record['name']
            res.append((record['id'],name ))
        return res

    def _default_company(self, cr, uid, context={}):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            return user.company_id.id
        return self.pool.get('res.company').search(cr, uid, [('parent_id', '=', False)])[0]

    _defaults = {
        'python_compute': lambda *a: '''# price_unit\n# address : res.partner.address object or False\n# product : product.product object or None\n# partner : res.partner object or None\n\nresult = price_unit * 0.10''',
        'python_compute_inv': lambda *a: '''# price_unit\n# address : res.partner.address object or False\n# product : product.product object or False\n\nresult = price_unit * 0.10''',
        'applicable_type': lambda *a: 'true',
        'type': lambda *a: 'percent',
        'amount': lambda *a: 0,
        'sequence': lambda *a: 1,
        'tax_group': lambda *a: 'vat',
        'ref_tax_sign': lambda *a: 1,
        'ref_base_sign': lambda *a: 1,
        'tax_sign': lambda *a: 1,
        'base_sign': lambda *a: 1,
        'include_base_amount': lambda *a: False,
        'type_tax_use': lambda *a: 'all',
    }
    _order = 'sequence'


account_tax_template()

# Fiscal Position Templates

class account_fiscal_position_template(osv.osv):
    _name = 'account.fiscal.position.template'
    _description = 'Template for Fiscal Position'

    _columns = {
        'name': fields.char('Fiscal Position Template', size=64, translate=True, required=True),
        'chart_template_id': fields.many2one('account.chart.template', 'Chart Template', required=True),
        'account_ids': fields.one2many('account.fiscal.position.account.template', 'position_id', 'Account Mapping'),
        'tax_ids': fields.one2many('account.fiscal.position.tax.template', 'position_id', 'Tax Mapping')
    }

account_fiscal_position_template()

class account_fiscal_position_tax_template(osv.osv):
    _name = 'account.fiscal.position.tax.template'
    _description = 'Fiscal Position Template Tax Mapping'
    _rec_name = 'position_id'

    _columns = {
        'position_id': fields.many2one('account.fiscal.position.template', 'Fiscal Position', required=True, ondelete='cascade'),
        'tax_src_id': fields.many2one('account.tax.template', 'Tax Source', required=True),
        'tax_dest_id': fields.many2one('account.tax.template', 'Replacement Tax')
    }

account_fiscal_position_tax_template()

class account_fiscal_position_account_template(osv.osv):
    _name = 'account.fiscal.position.account.template'
    _description = 'Fiscal Position Template Account Mapping'
    _rec_name = 'position_id'
    _columns = {
        'position_id': fields.many2one('account.fiscal.position.template', 'Fiscal Position', required=True, ondelete='cascade'),
        'account_src_id': fields.many2one('account.account.template', 'Account Source', domain=[('type','<>','view')], required=True),
        'account_dest_id': fields.many2one('account.account.template', 'Account Destination', domain=[('type','<>','view')], required=True)
    }

account_fiscal_position_account_template()

    # Multi charts of Accounts wizard

class wizard_multi_charts_accounts(osv.osv_memory):
    """
    Create a new account chart for a company.
    Wizards ask for:
        * a company
        * an account chart template
        * a number of digits for formatting code of non-view accounts
        * a list of bank accounts owned by the company
    Then, the wizard:
        * generates all accounts from the template and assigns them to the right company
        * generates all taxes and tax codes, changing account assignations
        * generates all accounting properties and assigns them correctly
    """
    _name='wizard.multi.charts.accounts'
    _inherit = 'res.config'

    _columns = {
        'company_id':fields.many2one('res.company','Company',required=True),
        'chart_template_id': fields.many2one('account.chart.template','Chart Template',required=True),
        'bank_accounts_id': fields.one2many('account.bank.accounts.wizard', 'bank_account_id', 'Bank Accounts',required=True),
        'code_digits':fields.integer('# of Digits',required=True,help="No. of Digits to use for account code"),
        'seq_journal':fields.boolean('Separated Journal Sequences',help="Check this box if you want to use a different sequence for each created journal. Otherwise, all will use the same sequence."),
    }

    def _get_chart(self, cr, uid, context={}):
        ids = self.pool.get('account.chart.template').search(cr, uid, [], context=context)
        if ids:
            return ids[0]
        return False
    _defaults = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr,uid,[uid],c)[0].company_id.id,
        'chart_template_id': _get_chart,
        'code_digits': lambda *a:6,
        'seq_journal': True
    }

    def execute(self, cr, uid, ids, context=None):
        obj_multi = self.browse(cr,uid,ids[0])
        obj_acc = self.pool.get('account.account')
        obj_acc_tax = self.pool.get('account.tax')
        obj_journal = self.pool.get('account.journal')
        obj_sequence = self.pool.get('ir.sequence')
        obj_acc_template = self.pool.get('account.account.template')
        obj_fiscal_position_template = self.pool.get('account.fiscal.position.template')
        obj_fiscal_position = self.pool.get('account.fiscal.position')

        # Creating Account
        obj_acc_root = obj_multi.chart_template_id.account_root_id
        tax_code_root_id = obj_multi.chart_template_id.tax_code_root_id.id
        company_id = obj_multi.company_id.id

        #new code
        acc_template_ref = {}
        tax_template_ref = {}
        tax_code_template_ref = {}
        todo_dict = {}

        #create all the tax code
        children_tax_code_template = self.pool.get('account.tax.code.template').search(cr, uid, [('parent_id','child_of',[tax_code_root_id])], order='id')
        children_tax_code_template.sort()
        for tax_code_template in self.pool.get('account.tax.code.template').browse(cr, uid, children_tax_code_template):
            vals={
                'name': (tax_code_root_id == tax_code_template.id) and obj_multi.company_id.name or tax_code_template.name,
                'code': tax_code_template.code,
                'info': tax_code_template.info,
                'parent_id': tax_code_template.parent_id and ((tax_code_template.parent_id.id in tax_code_template_ref) and tax_code_template_ref[tax_code_template.parent_id.id]) or False,
                'company_id': company_id,
                'sign': tax_code_template.sign,
            }
            new_tax_code = self.pool.get('account.tax.code').create(cr,uid,vals)
            #recording the new tax code to do the mapping
            tax_code_template_ref[tax_code_template.id] = new_tax_code

        #create all the tax
        for tax in obj_multi.chart_template_id.tax_template_ids:
            #create it
            vals_tax = {
                'name':tax.name,
                'sequence': tax.sequence,
                'amount':tax.amount,
                'type':tax.type,
                'applicable_type': tax.applicable_type,
                'domain':tax.domain,
                'parent_id': tax.parent_id and ((tax.parent_id.id in tax_template_ref) and tax_template_ref[tax.parent_id.id]) or False,
                'child_depend': tax.child_depend,
                'python_compute': tax.python_compute,
                'python_compute_inv': tax.python_compute_inv,
                'python_applicable': tax.python_applicable,
                'tax_group':tax.tax_group,
                'base_code_id': tax.base_code_id and ((tax.base_code_id.id in tax_code_template_ref) and tax_code_template_ref[tax.base_code_id.id]) or False,
                'tax_code_id': tax.tax_code_id and ((tax.tax_code_id.id in tax_code_template_ref) and tax_code_template_ref[tax.tax_code_id.id]) or False,
                'base_sign': tax.base_sign,
                'tax_sign': tax.tax_sign,
                'ref_base_code_id': tax.ref_base_code_id and ((tax.ref_base_code_id.id in tax_code_template_ref) and tax_code_template_ref[tax.ref_base_code_id.id]) or False,
                'ref_tax_code_id': tax.ref_tax_code_id and ((tax.ref_tax_code_id.id in tax_code_template_ref) and tax_code_template_ref[tax.ref_tax_code_id.id]) or False,
                'ref_base_sign': tax.ref_base_sign,
                'ref_tax_sign': tax.ref_tax_sign,
                'include_base_amount': tax.include_base_amount,
                'description':tax.description,
                'company_id': company_id,
                'type_tax_use': tax.type_tax_use
            }
            new_tax = obj_acc_tax.create(cr,uid,vals_tax)
            #as the accounts have not been created yet, we have to wait before filling these fields
            todo_dict[new_tax] = {
                'account_collected_id': tax.account_collected_id and tax.account_collected_id.id or False,
                'account_paid_id': tax.account_paid_id and tax.account_paid_id.id or False,
            }
            tax_template_ref[tax.id] = new_tax

        #deactivate the parent_store functionnality on account_account for rapidity purpose
        self.pool._init = True

        children_acc_template = obj_acc_template.search(cr, uid, [('parent_id','child_of',[obj_acc_root.id]),('nocreate','!=',True)])
        children_acc_template.sort()
        for account_template in obj_acc_template.browse(cr, uid, children_acc_template):
            tax_ids = []
            for tax in account_template.tax_ids:
                tax_ids.append(tax_template_ref[tax.id])
            #create the account_account

            dig = obj_multi.code_digits
            code_main = account_template.code and len(account_template.code) or 0
            code_acc = account_template.code or ''
            if code_main>0 and code_main<=dig and account_template.type != 'view':
                code_acc=str(code_acc) + (str('0'*(dig-code_main)))
            vals={
                'name': (obj_acc_root.id == account_template.id) and obj_multi.company_id.name or account_template.name,
                #'sign': account_template.sign,
                'currency_id': account_template.currency_id and account_template.currency_id.id or False,
                'code': code_acc,
                'type': account_template.type,
                'user_type': account_template.user_type and account_template.user_type.id or False,
                'reconcile': account_template.reconcile,
                'shortcut': account_template.shortcut,
                'note': account_template.note,
                'parent_id': account_template.parent_id and ((account_template.parent_id.id in acc_template_ref) and acc_template_ref[account_template.parent_id.id]) or False,
                'tax_ids': [(6,0,tax_ids)],
                'company_id': company_id,
            }
            new_account = obj_acc.create(cr,uid,vals)
            acc_template_ref[account_template.id] = new_account
        #reactivate the parent_store functionnality on account_account
        self.pool._init = False
        self.pool.get('account.account')._parent_store_compute(cr)

        for key,value in todo_dict.items():
            if value['account_collected_id'] or value['account_paid_id']:
                obj_acc_tax.write(cr, uid, [key], {
                    'account_collected_id': acc_template_ref[value['account_collected_id']],
                    'account_paid_id': acc_template_ref[value['account_paid_id']],
                })

        # Creating Journals
        vals_journal={}
        view_id = self.pool.get('account.journal.view').search(cr,uid,[('name','=','Journal View')])[0]
        seq_id = obj_sequence.search(cr,uid,[('name','=','Account Journal')])[0]

        if obj_multi.seq_journal:
            seq_id_sale = obj_sequence.search(cr,uid,[('name','=','Sale Journal')])[0]
            seq_id_purchase = obj_sequence.search(cr,uid,[('name','=','Purchase Journal')])[0]
        else:
            seq_id_sale = seq_id
            seq_id_purchase = seq_id

        vals_journal['view_id'] = view_id

        #Sales Journal
        vals_journal['name'] = _('Sales Journal')
        vals_journal['type'] = 'sale'
        vals_journal['code'] = _('SAJ')
        vals_journal['sequence_id'] = seq_id_sale

        if obj_multi.chart_template_id.property_account_receivable:
            vals_journal['default_credit_account_id'] = acc_template_ref[obj_multi.chart_template_id.property_account_income_categ.id]
            vals_journal['default_debit_account_id'] = acc_template_ref[obj_multi.chart_template_id.property_account_income_categ.id]

        obj_journal.create(cr,uid,vals_journal)

        # Purchase Journal
        vals_journal['name'] = _('Purchase Journal')
        vals_journal['type'] = 'purchase'
        vals_journal['code'] = _('EXJ')
        vals_journal['sequence_id'] = seq_id_purchase

        if obj_multi.chart_template_id.property_account_payable:
            vals_journal['default_credit_account_id'] = acc_template_ref[obj_multi.chart_template_id.property_account_expense_categ.id]
            vals_journal['default_debit_account_id'] = acc_template_ref[obj_multi.chart_template_id.property_account_expense_categ.id]

        obj_journal.create(cr,uid,vals_journal)

        # Bank Journals
        view_id_cash = self.pool.get('account.journal.view').search(cr,uid,[('name','=','Cash Journal View')])[0]
        view_id_cur = self.pool.get('account.journal.view').search(cr,uid,[('name','=','Multi-Currency Cash Journal View')])[0]
        ref_acc_bank = obj_multi.chart_template_id.bank_account_view_id

        current_num = 1
        for line in obj_multi.bank_accounts_id:
            #create the account_account for this bank journal
            tmp = self.pool.get('res.partner.bank').name_get(cr, uid, [line.acc_no.id])[0][1]
            dig = obj_multi.code_digits
            if ref_acc_bank.code:
                try:
                    new_code = str(int(ref_acc_bank.code.ljust(dig,'0')) + current_num)
                except Exception,e:
                    new_code = str(ref_acc_bank.code.ljust(dig-len(str(current_num)),'0')) + str(current_num)
            vals = {
                'name': line.acc_no.bank and line.acc_no.bank.name+' '+tmp or tmp,
                'currency_id': line.currency_id and line.currency_id.id or False,
                'code': new_code,
                'type': 'other',
                'user_type': account_template.user_type and account_template.user_type.id or False,
                'reconcile': True,
                'parent_id': acc_template_ref[ref_acc_bank.id] or False,
                'company_id': company_id,
            }
            acc_cash_id  = obj_acc.create(cr,uid,vals)

            if obj_multi.seq_journal:
                vals_seq={
                        'name': _('Bank Journal ') + vals['name'],
                        'code': 'account.journal',
                }
                seq_id = obj_sequence.create(cr,uid,vals_seq)

            #create the bank journal
            vals_journal['name']= vals['name']
            vals_journal['code']= _('BNK') + str(current_num)
            vals_journal['sequence_id'] = seq_id
            vals_journal['type'] = 'cash'
            if line.currency_id:
                vals_journal['view_id'] = view_id_cur
                vals_journal['currency'] = line.currency_id.id
            else:
                vals_journal['view_id'] = view_id_cash
            vals_journal['default_credit_account_id'] = acc_cash_id
            vals_journal['default_debit_account_id'] = acc_cash_id
            obj_journal.create(cr,uid,vals_journal)

            current_num += 1

        #create the properties
        property_obj = self.pool.get('ir.property')
        fields_obj = self.pool.get('ir.model.fields')

        todo_list = [
            ('property_account_receivable','res.partner','account.account'),
            ('property_account_payable','res.partner','account.account'),
            ('property_account_expense_categ','product.category','account.account'),
            ('property_account_income_categ','product.category','account.account'),
            ('property_account_expense','product.template','account.account'),
            ('property_account_income','product.template','account.account')
        ]
        for record in todo_list:
            r = []
            r = property_obj.search(cr, uid, [('name','=', record[0] ),('company_id','=',company_id)])
            account = getattr(obj_multi.chart_template_id, record[0])
            field = fields_obj.search(cr, uid, [('name','=',record[0]),('model','=',record[1]),('relation','=',record[2])])
            vals = {
                'name': record[0],
                'company_id': company_id,
                'fields_id': field[0],
                'value': account and 'account.account,'+str(acc_template_ref[account.id]) or False,
            }
            if r:
                #the property exist: modify it
                property_obj.write(cr, uid, r, vals)
            else:
                #create the property
                property_obj.create(cr, uid, vals)

        fp_ids = obj_fiscal_position_template.search(cr, uid,[('chart_template_id', '=', obj_multi.chart_template_id.id)])

        if fp_ids:
            for position in obj_fiscal_position_template.browse(cr, uid, fp_ids):

                vals_fp = {
                           'company_id' : company_id,
                           'name' : position.name,
                           }
                new_fp = obj_fiscal_position.create(cr, uid, vals_fp)

                obj_tax_fp = self.pool.get('account.fiscal.position.tax')
                obj_ac_fp = self.pool.get('account.fiscal.position.account')

                for tax in position.tax_ids:
                    vals_tax = {
                                'tax_src_id' : tax_template_ref[tax.tax_src_id.id],
                                'tax_dest_id' : tax.tax_dest_id and tax_template_ref[tax.tax_dest_id.id] or False,
                                'position_id' : new_fp,
                                }
                    obj_tax_fp.create(cr, uid, vals_tax)

                for acc in position.account_ids:
                    vals_acc = {
                                'account_src_id' : acc_template_ref[acc.account_src_id.id],
                                'account_dest_id' : acc_template_ref[acc.account_dest_id.id],
                                'position_id' : new_fp,
                                }
                    obj_ac_fp.create(cr, uid, vals_acc)
wizard_multi_charts_accounts()

class account_bank_accounts_wizard(osv.osv_memory):
    _name='account.bank.accounts.wizard'

    _columns = {
        'acc_name':fields.char('Account Name.', size=64, required=True),
        'bank_account_id':fields.many2one('wizard.multi.charts.accounts', 'Bank Account', required=True),
        'currency_id':fields.many2one('res.currency', 'Currency'),
        'account_type':fields.selection([('cash','Cash'),('check','Check'),('bank','Bank')], 'Type', size=32),
    }
    _defaults = {
        'currency_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.currency_id.id,
        }

account_bank_accounts_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

