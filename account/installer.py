# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
from dateutil.relativedelta import relativedelta
from os.path import join as opj
from operator import itemgetter

from tools.translate import _
from osv import fields, osv
import netsvc
import tools

class account_installer(osv.osv_memory):
    _name = 'account.installer'
    _inherit = 'res.config.installer'

    def _get_default_accounts(self, cr, uid, context=None):
        accounts = [{'acc_name':'Current','account_type':'bank'},
                    {'acc_name':'Deposit','account_type':'bank'},
                    {'acc_name':'Cash','account_type':'cash'}]
        return accounts

    def _get_charts(self, cr, uid, context=None):
        modules = self.pool.get('ir.module.module')
        ids = modules.search(cr, uid, [('category_id','=','Account Charts')])
        charts = list(
            sorted(((m.name, m.shortdesc)
                    for m in modules.browse(cr, uid, ids)),
                   key=itemgetter(1)))
        charts.insert(0,('configurable','Generic Chart Of Account'))
        return charts

    _columns = {
        # Accounting
        'charts': fields.selection(_get_charts, 'Chart of Accounts',
            required=True,
            help="Installs localized accounting charts to match as closely as "
                 "possible the accounting needs of your company based on your "
                 "country."),
        'date_start': fields.date('Start Date', required=True),
        'date_stop': fields.date('End Date', required=True),
        'period': fields.selection([('month','Monthly'), ('3months','3 Monthly')], 'Periods', required=True),
        'bank_accounts_id': fields.one2many('account.bank.accounts.wizard', 'bank_account_id', 'Your Bank and Cash Accounts'),
        'sale_tax': fields.float('Sale Tax(%)'),
        'purchase_tax': fields.float('Purchase Tax(%)'),
        'company_id': fields.many2one('res.company', 'Company'),
    }

    def _default_company(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            return user.company_id.id
        return False

    def _get_default_charts(self, cr, uid, context=None):
        module_name = False
        company_id = self._default_company(cr, uid, context=context)
        company = self.pool.get('res.company').browse(cr, uid, company_id)
        address_id = self.pool.get('res.partner').address_get(cr, uid, [company.partner_id.id])
        if address_id['default']:
            address = self.pool.get('res.partner.address').browse(cr, uid, address_id['default'])
            code = address.country_id.code
            module_name = (code and 'l10n_' + code.lower()) or False
        if module_name:
            module_id = self.pool.get('ir.module.module').search(cr, uid, [('name', '=', module_name)])
            if module_id:
                return module_name
        return 'configurable'

    _defaults = {
        'date_start': lambda *a: time.strftime('%Y-01-01'),
        'date_stop': lambda *a: time.strftime('%Y-12-31'),
        'period': 'month',
        'sale_tax': 0.0,
        'purchase_tax': 0.0,
        'company_id': _default_company,
        'bank_accounts_id': _get_default_accounts,
        'charts': _get_default_charts
    }

    def on_change_tax(self, cr, uid, id, tax):
        return {'value': {'purchase_tax': tax}}

    def on_change_start_date(self, cr, uid, id, start_date=False):
        if start_date:
            start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            end_date = (start_date + relativedelta(months=12)) - relativedelta(days=1)
            return {'value':{'date_stop':end_date.strftime('%Y-%m-%d')}}
        return {}

    def generate_configurable_chart(self, cr, uid, ids, context=None):
        obj_acc = self.pool.get('account.account')
        obj_acc_tax = self.pool.get('account.tax')
        obj_journal = self.pool.get('account.journal')
        obj_sequence = self.pool.get('ir.sequence')
        obj_acc_template = self.pool.get('account.account.template')
        obj_fiscal_position_template = self.pool.get('account.fiscal.position.template')
        obj_fiscal_position = self.pool.get('account.fiscal.position')
        mod_obj = self.pool.get('ir.model.data')
        analytic_journal_obj = self.pool.get('account.analytic.journal')

        result = mod_obj._get_id(cr, uid, 'account', 'configurable_chart_template')
        id = mod_obj.read(cr, uid, [result], ['res_id'])[0]['res_id']
        obj_multi = self.pool.get('account.chart.template').browse(cr, uid, id)

        record = self.browse(cr, uid, ids, context=context)[0]

        if context is None:
            context = {}
        company_id = self.browse(cr, uid, ids, context)[0].company_id
        seq_journal = True

        # Creating Account
        obj_acc_root = obj_multi.account_root_id
        tax_code_root_id = obj_multi.tax_code_root_id.id

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
                'name': (tax_code_root_id == tax_code_template.id) and company_id.name or tax_code_template.name,
                'code': tax_code_template.code,
                'info': tax_code_template.info,
                'parent_id': tax_code_template.parent_id and ((tax_code_template.parent_id.id in tax_code_template_ref) and tax_code_template_ref[tax_code_template.parent_id.id]) or False,
                'company_id': company_id.id,
                'sign': tax_code_template.sign,
            }
            new_tax_code = self.pool.get('account.tax.code').create(cr, uid, vals)
            #recording the new tax code to do the mapping
            tax_code_template_ref[tax_code_template.id] = new_tax_code

        #create all the tax
        for tax in obj_multi.tax_template_ids:
            #create it
            vals_tax = {
                'name':tax.name,
                'sequence': tax.sequence,
                'amount': tax.amount,
                'type': tax.type,
                'applicable_type': tax.applicable_type,
                'domain': tax.domain,
                'parent_id': tax.parent_id and ((tax.parent_id.id in tax_template_ref) and tax_template_ref[tax.parent_id.id]) or False,
                'child_depend': tax.child_depend,
                'python_compute': tax.python_compute,
                'python_compute_inv': tax.python_compute_inv,
                'python_applicable': tax.python_applicable,
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
                'company_id': company_id.id,
                'type_tax_use': tax.type_tax_use
            }
            new_tax = obj_acc_tax.create(cr, uid, vals_tax)
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

            dig = 6
            code_main = account_template.code and len(account_template.code) or 0
            code_acc = account_template.code or ''
            if code_main>0 and code_main<=dig and account_template.type != 'view':
                code_acc=str(code_acc) + (str('0'*(dig-code_main)))
            vals={
                'name': (obj_acc_root.id == account_template.id) and company_id.name or account_template.name,
                #'sign': account_template.sign,
                'currency_id': account_template.currency_id and account_template.currency_id.id or False,
                'code': code_acc,
                'type': account_template.type,
                'user_type': account_template.user_type and account_template.user_type.id or False,
                'reconcile': account_template.reconcile,
                'shortcut': account_template.shortcut,
                'note': account_template.note,
                'parent_id': account_template.parent_id and ((account_template.parent_id.id in acc_template_ref) and acc_template_ref[account_template.parent_id.id]) or False,
                'tax_ids': [(6, 0, tax_ids)],
                'company_id': company_id.id,
            }
            new_account = obj_acc.create(cr, uid, vals)
            acc_template_ref[account_template.id] = new_account
            if account_template.name == 'Bank Current Account':
                b_vals={
                    'name': 'Bank Accounts',
                    'code': '110500',
                    'type': 'view',
                    'user_type': account_template.parent_id.user_type and account_template.user_type.id or False,
                    'shortcut': account_template.shortcut,
                    'note': account_template.note,
                    'parent_id': account_template.parent_id and ((account_template.parent_id.id in acc_template_ref) and acc_template_ref[account_template.parent_id.id]) or False,
                    'tax_ids': [(6,0,tax_ids)],
                    'company_id': company_id.id,
                }
                bank_account = obj_acc.create(cr, uid, b_vals)

                view_id_cash = self.pool.get('account.journal.view').search(cr, uid, [('name', '=', 'Bank/Cash Journal View')])[0] #why fixed name here?
                view_id_cur = self.pool.get('account.journal.view').search(cr, uid, [('name', '=', 'Bank/Cash Journal (Multi-Currency) View')])[0] #Why Fixed name here?

                cash_result = mod_obj._get_id(cr, uid, 'account', 'conf_account_type_cash')
                cash_type_id = mod_obj.read(cr, uid, [cash_result], ['res_id'])[0]['res_id']

                bank_result = mod_obj._get_id(cr, uid, 'account', 'conf_account_type_bnk')
                bank_type_id = mod_obj.read(cr, uid, [bank_result], ['res_id'])[0]['res_id']

                check_result = mod_obj._get_id(cr, uid, 'account', 'conf_account_type_chk')
                check_type_id = mod_obj.read(cr, uid, [check_result], ['res_id'])[0]['res_id']

#                record = self.browse(cr, uid, ids, context=context)[0]
                code_cnt = 1
                vals_seq = {
                        'name': _('Bank Journal '),
                        'code': 'account.journal',
                        'prefix': 'BNK/%(year)s/',
                        'padding': 5
                        }
                seq_id = obj_sequence.create(cr, uid, vals_seq)

                #create the bank journals
                analitical_bank_ids = analytic_journal_obj.search(cr, uid, [('type','=','situation')])
                analitical_journal_bank = analitical_bank_ids and analitical_bank_ids[0] or False
                vals_journal = {}
                vals_journal['name'] = _('Bank Journal ')
                vals_journal['code'] = _('BNK')
                vals_journal['sequence_id'] = seq_id
                vals_journal['type'] = 'bank'
                vals_journal['analytic_journal_id'] = analitical_journal_bank
                if vals.get('currency_id', False):
                    vals_journal['view_id'] = view_id_cur
                    vals_journal['currency'] = vals.get('currency_id', False)
                else:
                    vals_journal['view_id'] = view_id_cash
                vals_journal['default_credit_account_id'] = new_account
                vals_journal['default_debit_account_id'] = new_account
                obj_journal.create(cr, uid, vals_journal)

                for val in record.bank_accounts_id:
                    seq_padding = 5
                    if val.account_type == 'cash':
                        type = cash_type_id
                    elif val.account_type == 'bank':
                        type = bank_type_id
                    elif val.account_type == 'check':
                        type = check_type_id
                    else:
                        type = check_type_id
                        seq_padding = None

                    vals_bnk = {'name': val.acc_name or '',
                        'currency_id': val.currency_id.id or False,
                        'code': str(110500 + code_cnt),
                        'type': 'liquidity',
                        'user_type': type,
                        'parent_id':bank_account,
                        'company_id': company_id.id }
                    child_bnk_acc = obj_acc.create(cr, uid, vals_bnk)
                    vals_seq_child = {
                        'name': _(vals_bnk['name'] + ' ' + 'Journal'),
                        'code': 'account.journal',
                        'prefix': _((vals_bnk['name'][:3].upper()) + '/%(year)s/'),
                        'padding': seq_padding
                        }
                    seq_id = obj_sequence.create(cr, uid, vals_seq_child)

                    #create the bank journal
                    vals_journal = {}
                    vals_journal['name'] = vals_bnk['name'] + ' Journal'
                    vals_journal['code'] = _(vals_bnk['name'][:3]).upper()
                    vals_journal['sequence_id'] = seq_id
                    vals_journal['type'] = 'cash'
                    if vals.get('currency_id', False):
                        vals_journal['view_id'] = view_id_cur
                        vals_journal['currency'] = vals_bnk.get('currency_id', False)
                    else:
                        vals_journal['view_id'] = view_id_cash
                    vals_journal['default_credit_account_id'] = child_bnk_acc
                    vals_journal['default_debit_account_id'] = child_bnk_acc
                    vals_journal['analytic_journal_id'] = analitical_journal_bank
                    obj_journal.create(cr,uid,vals_journal)
                    code_cnt += 1

        #reactivate the parent_store functionality on account_account
        self.pool._init = False
        self.pool.get('account.account')._parent_store_compute(cr)

        for key,value in todo_dict.items():
            if value['account_collected_id'] or value['account_paid_id']:
                obj_acc_tax.write(cr, uid, [key], {
                    'account_collected_id': acc_template_ref[value['account_collected_id']],
                    'account_paid_id': acc_template_ref[value['account_paid_id']],
                })

        # Creating Journals Sales and Purchase
        vals_journal={}
        data_id = mod_obj.search(cr, uid, [('model','=','account.journal.view'), ('name','=','account_sp_journal_view')])
        data = mod_obj.browse(cr, uid, data_id[0])
        view_id = data.res_id

        seq_id = obj_sequence.search(cr,uid,[('name','=','Account Journal')])[0]

        if seq_journal:
            seq_sale = {
                        'name': 'Sale Journal',
                        'code': 'account.journal',
                        'prefix': 'SAJ/%(year)s/',
                        'padding': 3
                        }
            seq_id_sale = obj_sequence.create(cr, uid, seq_sale)
            seq_purchase = {
                        'name': 'Purchase Journal',
                        'code': 'account.journal',
                        'prefix': 'EXJ/%(year)s/',
                        'padding': 3
                        }
            seq_id_purchase = obj_sequence.create(cr, uid, seq_purchase)
            seq_refund_sale = {
                        'name': 'Sales Refund Journal',
                        'code': 'account.journal',
                        'prefix': 'SCNJ/%(year)s/',
                        'padding': 3
                        }
            seq_id_sale_refund = obj_sequence.create(cr, uid, seq_refund_sale)
            seq_refund_purchase = {
                        'name': 'Purchase Refund Journal',
                        'code': 'account.journal',
                        'prefix': 'ECNJ/%(year)s/',
                        'padding': 3
                        }
            seq_id_purchase_refund = obj_sequence.create(cr, uid, seq_refund_purchase)
        else:
            seq_id_sale = seq_id
            seq_id_purchase = seq_id
            seq_id_sale_refund = seq_id
            seq_id_purchase_refund = seq_id

        vals_journal['view_id'] = view_id

        #Sales Journal
        analitical_sale_ids = analytic_journal_obj.search(cr,uid,[('type','=','sale')])
        analitical_journal_sale = analitical_sale_ids and analitical_sale_ids[0] or False

        vals_journal['name'] = _('Sales Journal')
        vals_journal['type'] = 'sale'
        vals_journal['code'] = _('SAJ')
        vals_journal['sequence_id'] = seq_id_sale
        vals_journal['analytic_journal_id'] = analitical_journal_sale


        if obj_multi.property_account_receivable:
            vals_journal['default_credit_account_id'] = acc_template_ref[obj_multi.property_account_income_categ.id]
            vals_journal['default_debit_account_id'] = acc_template_ref[obj_multi.property_account_income_categ.id]

        obj_journal.create(cr,uid,vals_journal)

        # Purchase Journal
        analitical_purchase_ids = analytic_journal_obj.search(cr, uid, [('type','=','purchase')])
        analitical_journal_purchase = analitical_purchase_ids and analitical_purchase_ids[0] or False

        vals_journal['name'] = _('Purchase Journal')
        vals_journal['type'] = 'purchase'
        vals_journal['code'] = _('EXJ')
        vals_journal['sequence_id'] = seq_id_purchase
        vals_journal['analytic_journal_id'] = analitical_journal_purchase

        if obj_multi.property_account_payable:
            vals_journal['default_credit_account_id'] = acc_template_ref[obj_multi.property_account_expense_categ.id]
            vals_journal['default_debit_account_id'] = acc_template_ref[obj_multi.property_account_expense_categ.id]

        obj_journal.create(cr,uid,vals_journal)

        # Creating Journals Sales Refund and Purchase Refund
        vals_journal={}
        data_id = mod_obj.search(cr, uid, [('model','=','account.journal.view'), ('name','=','account_sp_refund_journal_view')])
        data = mod_obj.browse(cr, uid, data_id[0])
        view_id = data.res_id

        vals_journal['view_id'] = view_id

        #Sales Refund Journal
        vals_journal['name'] = _('Sales Refund Journal')
        vals_journal['type'] = 'sale_refund'
        vals_journal['refund_journal'] = True
        vals_journal['code'] = _('SCNJ')
        vals_journal['sequence_id'] = seq_id_sale_refund
        vals_journal['analytic_journal_id'] = analitical_journal_sale

        if obj_multi.property_account_receivable:
            vals_journal['default_credit_account_id'] = acc_template_ref[obj_multi.property_account_income_categ.id]
            vals_journal['default_debit_account_id'] = acc_template_ref[obj_multi.property_account_income_categ.id]

        obj_journal.create(cr,uid,vals_journal)

        # Purchase Refund Journal
        vals_journal['name'] = _('Purchase Refund Journal')
        vals_journal['type'] = 'purchase_refund'
        vals_journal['refund_journal'] = True
        vals_journal['code'] = _('ECNJ')
        vals_journal['sequence_id'] = seq_id_purchase_refund
        vals_journal['analytic_journal_id'] = analitical_journal_purchase

        if obj_multi.property_account_payable:
            vals_journal['default_credit_account_id'] = acc_template_ref[obj_multi.property_account_expense_categ.id]
            vals_journal['default_debit_account_id'] = acc_template_ref[obj_multi.property_account_expense_categ.id]

        obj_journal.create(cr, uid, vals_journal)

        # Bank Journals
        view_id_cash = self.pool.get('account.journal.view').search(cr, uid, [('name','=','Bank/Cash Journal View')])[0] #TOFIX: Why put fixed name ?
        view_id_cur = self.pool.get('account.journal.view').search(cr, uid, [('name','=','Bank/Cash Journal (Multi-Currency) View')])[0] #TOFIX: why put fixed name?


        #create the properties
        property_obj = self.pool.get('ir.property')
        fields_obj = self.pool.get('ir.model.fields')

        todo_list = [
            ('property_account_receivable', 'res.partner', 'account.account'),
            ('property_account_payable', 'res.partner', 'account.account'),
            ('property_account_expense_categ', 'product.category', 'account.account'),
            ('property_account_income_categ', 'product.category', 'account.account'),
            ('property_account_expense', 'product.template', 'account.account'),
            ('property_account_income', 'product.template', 'account.account'),
            ('property_reserve_and_surplus_account', 'res.company', 'account.account'),
        ]

        for record in todo_list:
            r = []
            r = property_obj.search(cr, uid, [('name', '=', record[0]), ('company_id', '=', company_id.id)])
            account = getattr(obj_multi, record[0])
            field = fields_obj.search(cr, uid, [('name', '=', record[0]), ('model', '=', record[1]), ('relation', '=', record[2])])
            vals = {
                'name': record[0],
                'company_id': company_id.id,
                'fields_id': field[0],
                'value': account and 'account.account,'+str(acc_template_ref[account.id]) or False,
            }

            if r:
                #the property exist: modify it
                property_obj.write(cr, uid, r, vals)
            else:
                #create the property
                property_obj.create(cr, uid, vals)

        fp_ids = obj_fiscal_position_template.search(cr, uid,[('chart_template_id', '=', obj_multi.id)])

        if fp_ids:
            for position in obj_fiscal_position_template.browse(cr, uid, fp_ids):

                vals_fp = {
                           'company_id': company_id.id,
                           'name': position.name,
                           }
                new_fp = obj_fiscal_position.create(cr, uid, vals_fp)

                obj_tax_fp = self.pool.get('account.fiscal.position.tax')
                obj_ac_fp = self.pool.get('account.fiscal.position.account')

                for tax in position.tax_ids:
                    vals_tax = {
                                'tax_src_id': tax_template_ref[tax.tax_src_id.id],
                                'tax_dest_id': tax.tax_dest_id and tax_template_ref[tax.tax_dest_id.id] or False,
                                'position_id': new_fp,
                                }
                    obj_tax_fp.create(cr, uid, vals_tax)

                for acc in position.account_ids:
                    vals_acc = {
                                'account_src_id': acc_template_ref[acc.account_src_id.id],
                                'account_dest_id': acc_template_ref[acc.account_dest_id.id],
                                'position_id': new_fp,
                                }
                    obj_ac_fp.create(cr, uid, vals_acc)

    def execute(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        fy_obj = self.pool.get('account.fiscalyear')
        mod_obj = self.pool.get('ir.model.data')
        obj_acc = self.pool.get('account.account')
        obj_tax_code = self.pool.get('account.tax.code')
        obj_temp_tax_code = self.pool.get('account.tax.code.template')
        super(account_installer, self).execute(cr, uid, ids, context=context)
        record = self.browse(cr, uid, ids, context=context)[0]
        company_id = record.company_id
        for res in self.read(cr, uid, ids):
            if record.charts == 'configurable':
                fp = tools.file_open(opj('account','configurable_account_chart.xml'))
                tools.convert_xml_import(cr, 'account', fp, {}, 'init',True, None)
                fp.close()
                self.generate_configurable_chart(cr, uid, ids, context=context)
                obj_tax = self.pool.get('account.tax')
                obj_product = self.pool.get('product.product')
                ir_values = self.pool.get('ir.values')
                s_tax = (res.get('sale_tax', 0.0))/100
                p_tax = (res.get('purchase_tax', 0.0))/100
                tax_val = {}
                default_tax = []

                pur_temp_tax = mod_obj._get_id(cr, uid, 'account', 'tax_code_base_purchases')
                pur_temp_tax_id = mod_obj.read(cr, uid, [pur_temp_tax], ['res_id'])[0]['res_id']
                pur_temp_tax_names = obj_temp_tax_code.read(cr, uid, [pur_temp_tax_id], ['name'])
                pur_tax_parent_name = pur_temp_tax_names and pur_temp_tax_names[0]['name'] or False
                pur_taxcode_parent_id = obj_tax_code.search(cr, uid, [('name', 'ilike', pur_tax_parent_name)])
                if pur_taxcode_parent_id:
                    pur_taxcode_parent_id = pur_taxcode_parent_id[0]
                else:
                    pur_taxcode_parent_id = False

                pur_temp_tax_paid = mod_obj._get_id(cr, uid, 'account', 'tax_code_input')
                pur_temp_tax_paid_id = mod_obj.read(cr, uid, [pur_temp_tax_paid], ['res_id'])[0]['res_id']
                pur_temp_tax_paid_names = obj_temp_tax_code.read(cr, uid, [pur_temp_tax_paid_id], ['name'])
                pur_tax_paid_parent_name = pur_temp_tax_names and pur_temp_tax_paid_names[0]['name'] or False
                pur_taxcode_paid_parent_id = obj_tax_code.search(cr, uid, [('name', 'ilike', pur_tax_paid_parent_name)])
                if pur_taxcode_paid_parent_id:
                    pur_taxcode_paid_parent_id = pur_taxcode_paid_parent_id[0]
                else:
                    pur_taxcode_paid_parent_id = False

                sale_temp_tax = mod_obj._get_id(cr, uid, 'account', 'tax_code_base_sales')
                sale_temp_tax_id = mod_obj.read(cr, uid, [sale_temp_tax], ['res_id'])[0]['res_id']
                sale_temp_tax_names = obj_temp_tax_code.read(cr, uid, [sale_temp_tax_id], ['name'])
                sale_tax_parent_name = sale_temp_tax_names and sale_temp_tax_names[0]['name'] or False
                sale_taxcode_parent_id = obj_tax_code.search(cr, uid, [('name', 'ilike', sale_tax_parent_name)])
                if sale_taxcode_parent_id:
                    sale_taxcode_parent_id = sale_taxcode_parent_id[0]
                else:
                    sale_taxcode_parent_id = False

                sale_temp_tax_paid = mod_obj._get_id(cr, uid, 'account', 'tax_code_output')
                sale_temp_tax_paid_id = mod_obj.read(cr, uid, [sale_temp_tax_paid], ['res_id'])[0]['res_id']
                sale_temp_tax_paid_names = obj_temp_tax_code.read(cr, uid, [sale_temp_tax_paid_id], ['name'])
                sale_tax_paid_parent_name = sale_temp_tax_paid_names and sale_temp_tax_paid_names[0]['name'] or False
                sale_taxcode_paid_parent_id = obj_tax_code.search(cr, uid, [('name', 'ilike', sale_tax_paid_parent_name)])
                if sale_taxcode_paid_parent_id:
                    sale_taxcode_paid_parent_id = sale_taxcode_paid_parent_id[0]
                else:
                    sale_taxcode_paid_parent_id = False

                if s_tax*100 > 0.0:
                    tax_account_ids = obj_acc.search(cr, uid, [('name', '=', 'Tax Received')], context=context)
                    sales_tax_account_id = tax_account_ids and tax_account_ids[0] or False
                    vals_tax_code = {
                        'name': 'TAX%s%%'%(s_tax*100),
                        'code': 'TAX%s%%'%(s_tax*100),
                        'company_id': company_id.id,
                        'sign': 1,
                        'parent_id': sale_taxcode_parent_id
                        }
                    new_tax_code = self.pool.get('account.tax.code').create(cr, uid, vals_tax_code)

                    vals_paid_tax_code = {
                        'name': 'TAX Received %s%%'%(s_tax*100),
                        'code': 'TAX Received %s%%'%(s_tax*100),
                        'company_id': company_id.id,
                        'sign': 1,
                        'parent_id': sale_taxcode_paid_parent_id
                        }
                    new_paid_tax_code = self.pool.get('account.tax.code').create(cr, uid, vals_paid_tax_code)

                    sales_tax = obj_tax.create(cr, uid,
                                           {'name':'TAX %s%%'%(s_tax*100),
                                            'amount':s_tax,
                                            'base_code_id':new_tax_code,
                                            'tax_code_id':new_paid_tax_code,
                                            'type_tax_use':'sale',
                                            'account_collected_id':sales_tax_account_id,
                                            'account_paid_id':sales_tax_account_id
                                            })
                    default_account_ids = obj_acc.search(cr, uid, [('name', '=', 'Product Sales')],context=context)
                    if default_account_ids:
                        obj_acc.write(cr, uid, default_account_ids, {'tax_ids': [(6, 0, [sales_tax])]})
                    tax_val.update({'taxes_id': [(6, 0, [sales_tax])]})
                    default_tax.append(('taxes_id', sales_tax))
                if p_tax*100 > 0.0:
                    tax_account_ids = obj_acc.search(cr, uid, [('name', '=', 'Tax Paid')], context=context)
                    purchase_tax_account_id = tax_account_ids and tax_account_ids[0] or False
                    vals_tax_code = {
                        'name': 'TAX%s%%'%(p_tax*100),
                        'code': 'TAX%s%%'%(p_tax*100),
                        'company_id': company_id.id,
                        'sign': 1,
                        'parent_id': pur_taxcode_parent_id
                    }
                    new_tax_code = self.pool.get('account.tax.code').create(cr, uid, vals_tax_code)

                    vals_paid_tax_code = {
                        'name': 'TAX Paid %s%%'%(p_tax*100),
                        'code': 'TAX Paid %s%%'%(p_tax*100),
                        'company_id': company_id.id,
                        'sign': 1,
                        'parent_id': pur_taxcode_paid_parent_id
                    }
                    new_paid_tax_code = self.pool.get('account.tax.code').create(cr, uid, vals_paid_tax_code)

                    purchase_tax = obj_tax.create(cr, uid,
                                            {'name': 'TAX%s%%'%(p_tax*100),
                                             'description': 'TAX%s%%'%(p_tax*100),
                                             'amount': p_tax,
                                             'base_code_id': new_tax_code,
                                            'tax_code_id': new_paid_tax_code,
                                            'type_tax_use': 'purchase',
                                            'account_collected_id': purchase_tax_account_id,
                                            'account_paid_id': purchase_tax_account_id
                                             })
                    default_account_ids = obj_acc.search(cr, uid, [('name', '=', 'Expenses')], context=context)
                    if default_account_ids:
                        obj_acc.write(cr, uid, default_account_ids, {'tax_ids': [(6, 0, [purchase_tax])]})
                    tax_val.update({'supplier_taxes_id': [(6 ,0, [purchase_tax])]})
                    default_tax.append(('supplier_taxes_id', purchase_tax))
                if tax_val:
                    product_ids = obj_product.search(cr, uid, [])
                    for product in obj_product.browse(cr, uid, product_ids):
                        obj_product.write(cr, uid, product.id, tax_val)
                    for name, value in default_tax:
                        ir_values.set(cr, uid, key='default', key2=False, name=name, models =[('product.product',False)], value=[value])

            if 'date_start' in res and 'date_stop' in res:
                f_ids = fy_obj.search(cr, uid, [('date_start', '<=', res['date_start']), ('date_stop', '>=', res['date_stop']), ('company_id', '=', res['company_id'])])
                if not f_ids:
                    name = code = res['date_start'][:4]
                    if int(name) != int(res['date_stop'][:4]):
                        name = res['date_start'][:4] +'-'+ res['date_stop'][:4]
                        code = res['date_start'][2:4] +'-'+ res['date_stop'][2:4]
                    vals = {'name': name,
                            'code': code,
                            'date_start': res['date_start'],
                            'date_stop': res['date_stop'],
                            'company_id': res['company_id']
                           }
                    fiscal_id = fy_obj.create(cr, uid, vals, context=context)
                    if res['period'] == 'month':
                        fy_obj.create_period(cr, uid, [fiscal_id])
                    elif res['period'] == '3months':
                        fy_obj.create_period3(cr, uid, [fiscal_id])


    def modules_to_install(self, cr, uid, ids, context=None):
        modules = super(account_installer, self).modules_to_install(
            cr, uid, ids, context=context)
        chart = self.read(cr, uid, ids, ['charts'],
                          context=context)[0]['charts']
        self.logger.notifyChannel(
            'installer', netsvc.LOG_DEBUG,
            'Installing chart of accounts %s'%chart)
        return modules | set([chart])

account_installer()

class account_bank_accounts_wizard(osv.osv_memory):
    _name='account.bank.accounts.wizard'

    _columns = {
        'acc_name': fields.char('Account Name.', size=64, required=True),
        'bank_account_id': fields.many2one('account.installer', 'Bank Account', required=True),
        'currency_id': fields.many2one('res.currency', 'Secondary Currency', help="Forces all moves for this account to have this secondary currency."),
        'account_type': fields.selection([('cash','Cash'),('check','Check'),('bank','Bank')], 'Account Type', size=32),
    }
#    _defaults = {
#        'currency_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.currency_id.id,
#    }

account_bank_accounts_wizard()

class account_installer_modules(osv.osv_memory):
    _name = 'account.installer.modules'
    _inherit = 'res.config.installer'
    _columns = {
        # Accounting
        'account_analytic_plans': fields.boolean('Multiple Analytic Plans',
            help="Allows invoice lines to impact multiple analytic accounts "
                 "simultaneously."),
        'account_payment': fields.boolean('Suppliers Payment Management',
            help="Streamlines invoice payment and creates hooks to plug "
                 "automated payment systems in."),
        'account_followup': fields.boolean('Followups Management',
            help="Helps you generate reminder letters for unpaid invoices, "
                 "including multiple levels of reminding and customized "
                 "per-partner policies."),
        'account_voucher': fields.boolean('Voucher Management',
            help="Account Voucher module includes all the basic requirements of "
                 "Voucher Entries for Bank, Cash, Sales, Purchase, Expenses, Contra, etc... "),
        'account_anglo_saxon': fields.boolean('Anglo-Saxon Accounting',
            help="This module will support the Anglo-Saxons accounting methodology by "
                "changing the accounting logic with stock transactions."),
#        'account_voucher_payment':fields.boolean('Voucher and Reconcile Management',
#            help="Extension Account Voucher module includes allows to link payment / receipt "
#                 "entries with voucher, also automatically reconcile during the payment and receipt entries."),
    }

    _defaults = {
        'account_voucher': True,
    }

account_installer_modules()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
