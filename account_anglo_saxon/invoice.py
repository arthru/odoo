# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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

from osv import fields, osv

class account_invoice_line(osv.osv):
    _inherit = "account.invoice.line"
    
    def move_line_get(self, cr, uid, invoice_id, context=None):
        res = super(account_invoice_line,self).move_line_get(cr, uid, invoice_id, context)
        inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id)
        if inv.type in ('out_invoice','out_refund'):
            for i_line in inv.invoice_line:
                if i_line.product_id:
                    if inv.type == 'out_invoice':
                        dacc = i_line.product_id.product_tmpl_id.property_stock_account_output and i_line.product_id.product_tmpl_id.property_stock_account_output.id
                        if not dacc:
                            dacc = i_line.product_id.categ_id.property_stock_account_output_categ and i_line.product_id.categ_id.property_stock_account_output_categ.id
                    else:
                        dacc = i_line.product_id.product_tmpl_id.property_stock_account_input and i_line.product_id.product_tmpl_id.property_stock_account_input.id
                        if not dacc:
                            dacc = i_line.product_id.categ_id.property_stock_account_input_categ and i_line.product_id.categ_id.property_stock_account_input_categ.id
                            
                    cacc = i_line.product_id.product_tmpl_id.property_account_expense and i_line.product_id.product_tmpl_id.property_account_expense.id
                    if not cacc:
                        cacc = i_line.product_id.categ_id.property_account_expense_categ and i_line.product_id.categ_id.property_account_expense_categ.id
                    if dacc and cacc:
                        res.append({
                            'type':'src',
                            'name': i_line.name[:64],
                            'price_unit':i_line.product_id.product_tmpl_id.standard_price,
                            'quantity':i_line.quantity,
                            'price':i_line.product_id.product_tmpl_id.standard_price * i_line.quantity,
                            'account_id':dacc,
                            'product_id':i_line.product_id.id,
                            'uos_id':i_line.uos_id.id,
                            'account_analytic_id':i_line.account_analytic_id.id,
                            'taxes':i_line.invoice_line_tax_id,
                            })
                        
                        res.append({
                            'type':'src',
                            'name': i_line.name[:64],
                            'price_unit':i_line.product_id.product_tmpl_id.standard_price,
                            'quantity':i_line.quantity,
                            'price': -1 * i_line.product_id.product_tmpl_id.standard_price * i_line.quantity,
                            'account_id':cacc,
                            'product_id':i_line.product_id.id,
                            'uos_id':i_line.uos_id.id,
                            'account_analytic_id':i_line.account_analytic_id.id,
                            'taxes':i_line.invoice_line_tax_id,
                            })
        elif inv.type in ('in_invoice','in_refund'):
            for i_line in inv.invoice_line:
                if i_line.product_id:
                    if i_line.product_id.product_tmpl_id.type != 'service':
                        acc = i_line.product_id.product_tmpl_id.property_account_creditor_price_difference and i_line.product_id.product_tmpl_id.property_account_creditor_price_difference.id
                        if not acc:
                            acc = i_line.product_id.categ_id.property_account_creditor_price_difference_categ and i_line.product_id.categ_id.property_account_creditor_price_difference_categ.id
                        a = None
                        if inv.type == 'in_invoice':
                            oa = i_line.product_id.product_tmpl_id.property_stock_account_input and i_line.product_id.product_tmpl_id.property_stock_account_input.id
                            if not oa:
                                oa = i_line.product_id.categ_id.property_stock_account_input_categ and i_line.product_id.categ_id.property_stock_account_input_categ.id
                        else:
                            oa = i_line.product_id.product_tmpl_id.property_stock_account_output and i_line.product_id.product_tmpl_id.property_stock_account_output.id
                            if not oa:
                                oa = i_line.product_id.categ_id.property_stock_account_output_categ and i_line.product_id.categ_id.property_stock_account_output_categ.id
                        if oa:
                            fpos = i_line.invoice_id.fiscal_position or False
                            a = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, oa)
                        diff_res = []
                        for line in res:
                            if a == line['account_id'] and i_line.product_id.id == line['product_id']:
                                if i_line.product_id.product_tmpl_id.standard_price != i_line.price_unit and line['price'] == i_line.price_unit and acc:
                                    price_diff = i_line.price_unit - i_line.product_id.product_tmpl_id.standard_price
                                    line.update({'price':i_line.product_id.product_tmpl_id.standard_price * line['quantity']})
                                    diff_res.append({
                                        'type':'src',
                                        'name': i_line.name[:64],
                                        'price_unit':price_diff,
                                        'quantity':line['quantity'],
                                        'price': price_diff * line['quantity'],
                                        'account_id':acc,
                                        'product_id':line['product_id'],
                                        'uos_id':line['uos_id'],
                                        'account_analytic_id':line['account_analytic_id'],
                                        'taxes':line.get('taxes',[]),
                                        })
                        res += diff_res
        return res   
    
    def product_id_change(self, cr, uid, ids, product, uom, qty=0, name='', type='out_invoice', partner_id=False, fposition_id=False, price_unit=False, address_invoice_id=False, context=None):
        if not product:
            return super(account_invoice_line, self).product_id_change(cr, uid, ids, product, uom, qty, name, type, partner_id, fposition_id, price_unit, address_invoice_id, context)
        else:
            res = super(account_invoice_line, self).product_id_change(cr, uid, ids, product, uom, qty, name, type, partner_id, fposition_id, price_unit, address_invoice_id, context)

        if type in ('in_invoice','in_refund'):
            product_obj = self.pool.get('product.product').browse(cr, uid, product, context=context)
            if type == 'in_invoice':
                oa = product_obj.product_tmpl_id.property_stock_account_input and product_obj.product_tmpl_id.property_stock_account_input.id
                if not oa:
                    oa = product_obj.categ_id.property_stock_account_input_categ and product_obj.categ_id.property_stock_account_input_categ.id
            else:
                oa = product_obj.product_tmpl_id.property_stock_account_output and product_obj.product_tmpl_id.property_stock_account_output.id
                if not oa:
                    oa = product_obj.categ_id.property_stock_account_output_categ and product_obj.categ_id.property_stock_account_output_categ.id
            if oa:
                fpos = fposition_id and self.pool.get('account.fiscal.position').browse(cr, uid, fposition_id) or False
                a = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, oa)
                res['value'].update({'account_id':a})            
        return res
         
account_invoice_line()

class account_invoice(osv.osv):
    _inherit = "account.invoice"

    def _refund_cleanup_lines(self, cr, uid, lines):
        for line in lines:
            inv_id = line['invoice_id']
            inv_obj = self.browse(cr,uid,inv_id[0])
            if inv_obj.type == 'in_invoice':
                if line.get('product_id',False):
                    product_obj = self.pool.get('product.product').browse(cr,uid,line['product_id'][0])
                    oa = product_obj.product_tmpl_id.property_stock_account_output and product_obj.product_tmpl_id.property_stock_account_output.id
                    if not oa:
                        oa = product_obj.categ_id.property_stock_account_output_categ and product_obj.categ_id.property_stock_account_output_categ.id
                    if oa:
                        fpos = inv_obj.fiscal_position or False
                        a = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, oa)
                        account_data = self.pool.get('account.account').read(cr,uid,[a],['name'])[0]
                        line.update({'account_id': (account_data['id'],account_data['name'])})
        res = super(account_invoice,self)._refund_cleanup_lines(cr, uid, lines)
        return res
    
account_invoice()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: