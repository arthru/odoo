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

import time
from osv import fields,osv
import netsvc
import mx.DateTime
from mx.DateTime import RelativeDateTime, today, DateTime, localtime
from tools import config
class mrp_repair(osv.osv):
    _name = 'mrp.repair'
    _description = 'Repairs Order'   
    
    def _amount_untaxed(self, cr, uid, ids, field_name, arg, context):
        res = {}
        cur_obj=self.pool.get('res.currency')
        for repair in self.browse(cr, uid, ids):
            res[repair.id] = 0.0
            for line in repair.operations:
                res[repair.id] += line.price_subtotal
            for line in repair.fees_lines:
                res[repair.id] += line.price_subtotal
            cur = repair.pricelist_id.currency_id
            res[repair.id] = cur_obj.round(cr, uid, cur, res[repair.id])
        return res

    def _amount_tax(self, cr, uid, ids, field_name, arg, context):
        res = {}
        cur_obj=self.pool.get('res.currency')
        for repair in self.browse(cr, uid, ids):
            val = 0.0
            cur=repair.pricelist_id.currency_id
            for line in repair.operations:
                for c in self.pool.get('account.tax').compute(cr, uid, line.tax_id, line.price_unit, line.product_uom_qty, repair.partner_invoice_id.id, line.product_id, repair.partner_id):
                    val+= c['amount']
            for line in repair.fees_lines:
                for c in self.pool.get('account.tax').compute(cr, uid, line.tax_id, line.price_unit, line.product_uom_qty, repair.partner_invoice_id.id, line.product_id, repair.partner_id):
                    val+= c['amount']
            res[repair.id]=cur_obj.round(cr, uid, cur, val)
        return res

    def _amount_total(self, cr, uid, ids, field_name, arg, context):
        res = {}
        untax = self._amount_untaxed(cr, uid, ids, field_name, arg, context)
        tax = self._amount_tax(cr, uid, ids, field_name, arg, context)
        cur_obj=self.pool.get('res.currency')
        for id in ids:
            repair=self.browse(cr, uid, [id])[0]
            cur=repair.pricelist_id.currency_id
            res[id] = cur_obj.round(cr, uid, cur, untax.get(id, 0.0) + tax.get(id, 0.0))
        return res
    _columns = {
        'name' : fields.char('Name',size=24, required=True),
        'product_id': fields.many2one('product.product', string='Product to Repair', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'partner_id' : fields.many2one('res.partner', 'Partner', select=True),
        'address_id': fields.many2one('res.partner.address', 'Delivery Address', domain="[('partner_id','=',partner_id)]"),
        'prodlot_id': fields.many2one('stock.production.lot', 'Lot Number', select=True, domain="[('product_id','=',product_id)]"),
        'state': fields.selection([
            ('draft','Quotation'),
            ('confirmed','Confirmed'),
            ('ready','Ready to Repair'),
            ('under_repair','Under Repair'),
            ('2binvoiced','To be Invoiced'),            
            ('invoice_except','Invoice Exception'),
            ('done','Done'),
            ('cancel','Cancel')
            ], 'Repair State', readonly=True, help="Gives the state of the Repair Order"),
        'location_id': fields.many2one('stock.location', 'Current Location', required=True, select=True, readonly=True, states={'draft':[('readonly',False)]}),
        'location_dest_id': fields.many2one('stock.location', 'Delivery Location', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'move_id': fields.many2one('stock.move', 'Move',required=True, domain="[('product_id','=',product_id)]", readonly=True, states={'draft':[('readonly',False)]}),#,('location_dest_id','=',location_id),('prodlot_id','=',prodlot_id)
        'guarantee_limit': fields.date('Guarantee limit'),
        'operations' : fields.one2many('mrp.repair.line', 'repair_id', 'Operation Lines', readonly=True, states={'draft':[('readonly',False)]}),        
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist'),
        'partner_invoice_id':fields.many2one('res.partner.address', 'Invoice to',  domain="[('partner_id','=',partner_id)]"),
        'invoice_method':fields.selection([
            ("none","No Invoice"),
            ("b4repair","Before Repair"),
            ("after_repair","After Repair")
           ], "Invoice Method", 
            select=True, states={'draft':[('readonly',False)]}, readonly=True),
        'invoice_id': fields.many2one('account.invoice', 'Invoice', readonly=True),
        'picking_id': fields.many2one('stock.picking', 'Packing',readonly=True),
        'fees_lines' : fields.one2many('mrp.repair.fee', 'repair_id', 'Fees Lines', readonly=True, states={'draft':[('readonly',False)]}),
        'internal_notes' : fields.text('Internal Notes'),
        'quotation_notes' : fields.text('Quotation Notes'),
        'invoiced': fields.boolean('Invoiced', readonly=True),
        'repaired' : fields.boolean('Repaired', readonly=True),
        'amount_untaxed': fields.function(_amount_untaxed, method=True, string='Untaxed Amount'),
        'amount_tax': fields.function(_amount_tax, method=True, string='Taxes'),
        'amount_total': fields.function(_amount_total, method=True, string='Total'),
    }
    
    _defaults = {
        'state': lambda *a: 'draft',
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'mrp.repair'),
        'invoice_method': lambda *a: 'none',
        'pricelist_id': lambda self, cr, uid,context : self.pool.get('product.pricelist').search(cr,uid,[('type','=','sale')])[0]
    }
    
    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}   
        default.update({
            'state':'draft',
            'repaired':False,
            'invoiced':False,
            'invoice_id': False,
            'picking_id': False,
            'name': self.pool.get('ir.sequence').get(cr, uid, 'mrp.repair'),
        })
        return super(mrp_repair, self).copy(cr, uid, id, default, context)

    
    def onchange_product_id(self, cr, uid, ids, product_id=None):
        return {'value': {
                    'prodlot_id': False, 
                    'move_id': False, 
                    'guarantee_limit' :False, 
                    'location_id':  False, 
                    'location_dest_id': False,
                }
        }
    
    def onchange_move_id(self, cr, uid, ids, prod_id=False, move_id=False):
        if not prod_id:
            return {'value': {
                        'prodlot_id': False, 
                        'move_id': False, 
                        'guarantee_limit' :False, 
                        'location_id':  False, 
                        'location_dest_id': False
                    }
            }
        if move_id:
            move =  self.pool.get('stock.move').browse(cr, uid, move_id)
            product = self.pool.get('product.product').browse(cr, uid, prod_id)
            date = move.date_planned
            limit = mx.DateTime.strptime(date, '%Y-%m-%d %H:%M:%S') + RelativeDateTime(months=product.warranty)
            return {'value': {
                        'guarantee_limit': limit.strftime('%Y-%m-%d'),
                    }
            }
    
    def button_dummy(self, cr, uid, ids, context=None):
        return True

    def onchange_partner_id(self, cr, uid, ids, part):
        if not part:
            return {'value': {
                        'address_id': False,
                        'partner_invoice_id': False,
                        'pricelist_id': self.pool.get('product.pricelist').search(cr,uid,[('type','=','sale')])[0]
                    }
            }
        addr = self.pool.get('res.partner').address_get(cr, uid, [part], ['delivery', 'invoice', 'default'])
        partner = self.pool.get('res.partner').browse(cr, uid, part)
        pricelist = partner.property_product_pricelist and partner.property_product_pricelist.id or False
        return {'value': {
                    'address_id': addr['delivery'], 
                    'partner_invoice_id': addr['invoice'],
                    'pricelist_id': pricelist
                }
        }

    
    def onchange_lot_id(self, cr, uid, ids, lot, product_id):
        if not lot:
            return {'value': {
                        'location_id': False,
                        'location_dest_id': False,
                        'move_id': False,
                        'guarantee_limit': False
                    }
            }
        lot_info = self.pool.get('stock.production.lot').browse(cr, uid, lot)
        move_ids = self.pool.get('stock.move').search(cr, uid, [('prodlot_id', '=', lot)])
        
        if not len(move_ids):
            return {'value': {
                        'location_id': False,
                        'location_dest_id': False,
                        'move_id':  False, 
                        'guarantee_limit':False
                    }
            }

        def get_last_move(lst_move):
            while lst_move.move_dest_id and lst_move.state == 'done':
                lst_move = lst_move.move_dest_id
            return lst_move

        move_id = move_ids[0]
        move = get_last_move(self.pool.get('stock.move').browse(cr, uid, move_id))            
        product = self.pool.get('product.product').browse(cr, uid, product_id)
        date = move.date_planned
        limit = mx.DateTime.strptime(date, '%Y-%m-%d %H:%M:%S') + RelativeDateTime(months=product.warranty)            
        return {'value': {
                    'location_id': move.location_dest_id.id, 
                    'location_dest_id': move.location_dest_id.id,
                    'move_id': move.id,
                    'guarantee_limit': limit.strftime('%Y-%m-%d')
                }
            }
        
    def action_cancel_draft(self, cr, uid, ids, *args):
        if not len(ids):
            return False
        mrp_line_obj = self.pool.get('mrp.repair.line')
        for repair in self.browse(cr, uid, ids):
            mrp_line_obj.write(cr, uid, [l.id for l in repair.operations], {'state': 'draft'})
        self.write(cr, uid, ids, {'state':'draft'})
        wf_service = netsvc.LocalService("workflow")
        for id in ids:
            wf_service.trg_create(uid, 'mrp.repair', id, cr)
        return True

    def action_confirm(self, cr, uid, ids, *args):        
        mrp_line_obj = self.pool.get('mrp.repair.line')
        for o in self.browse(cr, uid, ids):
            if (o.invoice_method == 'b4repair'):                
                self.write(cr, uid, [o.id], {'state': '2binvoiced'})
            else:
                self.write(cr, uid, [o.id], {'state': 'confirmed'})   
                mrp_line_obj.write(cr, uid, [l.id for l in o.operations], {'state': 'confirmed'})
        return True
    
    def action_cancel(self, cr, uid, ids, context=None):
        ok=True
        mrp_line_obj = self.pool.get('mrp.repair.line')
        for repair in self.browse(cr, uid, ids):
            mrp_line_obj.write(cr, uid, [l.id for l in repair.operations], {'state': 'cancel'})
        self.write(cr,uid,ids,{'state':'cancel'})
        return True

    def wkf_invoice_create(self, cr, uid, ids, *args):
        return self.action_invoice_create(cr, uid, ids)

    def action_invoice_create(self, cr, uid, ids, group=False, context=None):
        res={}        
        invoices_group = {}
        for repair in self.browse(cr, uid, ids, context=context):
            res[repair.id]=False
            if repair.state in ('draft','cancel') or repair.invoice_id:                                
                continue           
            if not (repair.partner_id.id and repair.partner_invoice_id.id):
                raise osv.except_osv('No partner !','You have to select a partner in the repair form ! ')
            comment=repair.quotation_notes
            if (repair.invoice_method != 'none'):
                if group and repair.partner_invoice_id.id in invoices_group:
                    inv_id= invoices_group[repair.partner_invoice_id.id]
                    invoice=invoice_obj.browse(cr, uid,inv_id)      
                    invoice_vals = {
                        'name': invoice.name +', '+repair.name,
                        'origin': invoice.origin+', '+repair.name,    
                        'comment':(comment and (invoice.comment and invoice.comment+"\n"+comment or comment)) or (invoice.comment and invoice.comment or ''),
                    }                 
                    invoice_obj.write(cr, uid, [inv_id],invoice_vals,context=context)
                else:
                    a = repair.partner_id.property_account_receivable.id
                    inv = {
                        'name': repair.name,
                        'origin':repair.name,
                        'type': 'out_invoice',                    
                        'account_id': a,
                        'partner_id': repair.partner_id.id,
                        'address_invoice_id': repair.address_id.id,
                        'currency_id': repair.pricelist_id.currency_id.id,
                        'comment': repair.quotation_notes,
                    }
                    inv_obj = self.pool.get('account.invoice')
                    inv_id = inv_obj.create(cr, uid, inv)
                    invoices_group[repair.partner_invoice_id.id] = inv_id 
                self.write(cr, uid, repair.id , {'invoiced':True,'invoice_id' : inv_id}) 
                                
                for operation in repair.operations:
                    if operation.to_invoice == True:                                        
                        if group:
                            name = repair.name + '-' + operation.name
                        else:
                            name = operation.name
                        invoice_line_id=self.pool.get('account.invoice.line').create(cr, uid, {
                            'invoice_id': inv_id, 
                            'name': name,
                            'origin':repair.name,
                            'account_id': a,
                            'quantity' : operation.product_uom_qty,
                            'invoice_line_tax_id': [(6,0,[x.id for x in operation.tax_id])],
                            'uos_id' : operation.product_uom.id,
                            'price_unit' : operation.price_unit,
                            'price_subtotal' : operation.product_uom_qty*operation.price_unit,
                            'product_id' : operation.product_id and operation.product_id.id or False
                            })                   
                        self.pool.get('mrp.repair.line').write(cr, uid, [operation.id], {'invoiced':True,'invoice_line_id':invoice_line_id})
                for fee in repair.fees_lines:
                    if fee.to_invoice == True:
                        if group:
                            name = repair.name + '-' + fee.name
                        else:
                            name = fee.name
                        invoice_fee_id=self.pool.get('account.invoice.line').create(cr, uid, {
                            'invoice_id': inv_id,
                            'name': name,
                            'origin':repair.name,
                            'account_id': a,
                            'quantity': fee.product_uom_qty,
                            'invoice_line_tax_id': [(6,0,[x.id for x in fee.tax_id])],
                            'uos_id': fee.product_uom.id,
                            'product_id': fee.product_id and fee.product_id.id or False,
                            'price_unit': fee.price_unit,
                            'price_subtotal': fee.product_uom_qty*fee.price_unit
                            })
                        self.pool.get('mrp.repair.fee').write(cr, uid, [fee.id], {'invoiced':True,'invoice_line_id':invoice_fee_id})
                res[repair.id]=inv_id
        #self.action_invoice_end(cr, uid, ids)
        return res

    def action_invoice_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'invoice_except'})
        return True

    def action_repair_ready(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'ready'})
        return True

    def action_repair_start(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'under_repair'})
        return True
    
    def action_invoice_end(self, cr, uid, ids, context=None):        
        for order in self.browse(cr, uid, ids):
            val = {}             
            if (order.invoice_method=='b4repair'):
                val['state'] = 'ready'
            else:                
                #val['state'] = 'done'                 
                pass
            self.write(cr, uid, [order.id], val)
        return True     

    def action_repair_end(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids):
            val = {}
            val['repaired']=True
            if (not order.invoiced and order.invoice_method=='after_repair'):
                val['state'] = '2binvoiced'  
            elif (not order.invoiced and order.invoice_method=='b4repair'):
                val['state'] = 'ready'
            else:                
                #val['state'] = 'done'                 
                pass
            self.write(cr, uid, [order.id], val)
        return True     

    def wkf_repair_done(self, cr, uid, ids, *args):
        res=self.action_repair_done(cr,uid,ids)
        return True
        
    def action_repair_done(self, cr, uid, ids, context=None):    
        res = {}    
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        for repair in self.browse(cr, uid, ids, context=context): 
            
            picking = self.pool.get('stock.picking').create(cr, uid, {
                'origin': repair.name,
                'state': 'assigned',
                'move_type': 'one',
                'address_id': repair.address_id and repair.address_id.id or False,
                'note': repair.internal_notes,
                'invoice_state': 'none',
                'type': 'out',  # FIXME delivery ?
            })

            move_id = self.pool.get('stock.move').create(cr, uid, {
                'name': repair.name,
                'picking_id': picking,
                'product_id': repair.product_id.id,
                'product_qty': 1.0,
                'product_uom': repair.product_id.uom_id.id,
                #'product_uos_qty': line.product_uom_qty,
                #'product_uos': line.product_uom.id,
                'prodlot_id': repair.prodlot_id and repair.prodlot_id.id or False,
                'address_id': repair.address_id and repair.address_id.id or False,
                'location_id': repair.location_id.id,
                'location_dest_id': repair.location_dest_id.id,
                'tracking_id': False,
                'state': 'assigned',    # FIXME done ?
            })
            
            self.write(cr, uid, [repair.id], {'state':'done', 'picking_id':picking})
            res[repair.id] = picking
        return res   
        
           
mrp_repair()


class ProductChangeMixin(object):
    def product_id_change(self, cr, uid, ids, pricelist, product, uom=False, product_uom_qty=0, partner_id=False, guarantee_limit=False):
        result = {}
        warning = {}       
        
        if not product_uom_qty:
            product_uom_qty = 1
        result['product_uom_qty'] = product_uom_qty 

        if product:
            product_obj =  self.pool.get('product.product').browse(cr, uid, product)
            result['name'] = product_obj.partner_ref
            result['product_uom'] = product_obj.uom_id and product_obj.uom_id.id or False
            if not pricelist:
                warning={
                    'title':'No Pricelist !',
                    'message':
                        'You have to select a pricelist in the Repair form !\n'
                        'Please set one before choosing a product.'
                }
            else:
                price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
                            product, product_uom_qty, partner_id, {'uom': uom,})[pricelist]
            
                if price is False:
                     warning={
                        'title':'No valid pricelist line found !',
                        'message':
                            "Couldn't find a pricelist line matching this product and quantity.\n"
                            "You have to change either the product, the quantity or the pricelist."
                    }
                else:
                    result.update({'price_unit': price, 'price_subtotal' :price*product_uom_qty})
        
        return {'value': result, 'warning': warning}
     

class mrp_repair_line(osv.osv, ProductChangeMixin):
    _name = 'mrp.repair.line'
    _description = 'Repair Operations Lines'    
    
    def copy(self, cr, uid, id, default=None, context=None):
        if not default: default = {}
        default.update( {'invoice_line_id':False,'move_ids':[],'invoiced':False,'state':'draft'})
        return super(mrp_repair_line, self).copy(cr, uid, id, default, context)
    
    def _amount_line(self, cr, uid, ids, field_name, arg, context):
        res = {}
        cur_obj=self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids):
            res[line.id] = line.to_invoice and line.price_unit * line.product_uom_qty or 0
            cur = line.repair_id.pricelist_id.currency_id
            res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
        return res

    _columns = {
        'name' : fields.char('Name',size=64,required=True),
        'repair_id': fields.many2one('mrp.repair', 'Repair Order Ref',ondelete='cascade', select=True),
        'type': fields.selection([('add','Add'),('remove','Remove')],'Type'),
        'to_invoice': fields.boolean('To Invoice'),                
        'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok','=',True)]),
        'invoiced': fields.boolean('Invoiced',readonly=True),                
        'price_unit': fields.float('Unit Price', required=True, digits=(16, int(config['price_accuracy']))),                
        'price_subtotal': fields.function(_amount_line, method=True, string='Subtotal',digits=(16, int(config['price_accuracy']))),  
        'tax_id': fields.many2many('account.tax', 'repair_operation_line_tax', 'repair_operation_line_id', 'tax_id', 'Taxes'),              
        'product_uom_qty': fields.float('Quantity (UoM)', digits=(16,2), required=True),
        'product_uom': fields.many2one('product.uom', 'Product UoM', required=True),          
        'invoice_line_id': fields.many2one('account.invoice.line', 'Invoice Line', readonly=True),   
        'location_id': fields.many2one('stock.location', 'Source Location', required=True, select=True),
        'location_dest_id': fields.many2one('stock.location', 'Dest. Location', required=True, select=True),      
        'move_ids': fields.one2many('stock.move', 'repair_line_id', 'Inventory Moves', readonly=True),   
        'state': fields.selection([('draft','Draft'),('confirmed','Confirmed'),('done','Done'),('cancel','Canceled')], 'Status', required=True, readonly=True),
    }
    _defaults = {                 
     'state': lambda *a: 'draft',
     'product_uom_qty':lambda *a:1,                 
    }
     
    def onchange_operation_type(self, cr, uid, ids, type,guarantee_limit):
        if not type:
            return {'value': {
                        'location_id': False,
                        'location_dest_id': False
                    }
            }
        stock_id = self.pool.get('stock.location').search(cr, uid, [('name','=','Stock')])[0]
        produc_id = self.pool.get('stock.location').search(cr, uid, [('name','=','Production')])[0]
        to_invoice=False
        if guarantee_limit and today() > mx.DateTime.strptime(guarantee_limit, '%Y-%m-%d'):
            to_invoice=True
        if type == 'add':
            return {'value': {
                        'to_invoice': to_invoice,
                        'location_id': stock_id,
                        'location_dest_id' : produc_id
                    }
            }
        if type == 'remove':
            return {'value': {
                        'to_invoice': to_invoice,
                        'location_id': produc_id,
                        'location_dest_id':False
                    }
            }
    
mrp_repair_line()

class mrp_repair_fee(osv.osv, ProductChangeMixin):
    _name = 'mrp.repair.fee'
    _description = 'Repair Fees line'
    def copy(self, cr, uid, id, default=None, context=None):
        if not default: default = {}
        default.update( {'invoice_line_id':False,'invoiced':False})
        return super(mrp_repair_fee, self).copy(cr, uid, id, default, context)
    def _amount_line(self, cr, uid, ids, field_name, arg, context):
        res = {}
        cur_obj=self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids):
            res[line.id] = line.to_invoice and line.price_unit * line.product_uom_qty or 0
            cur = line.repair_id.pricelist_id.currency_id
            res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
        return res

    _columns = {
        'repair_id': fields.many2one('mrp.repair', 'Repair Order Ref', required=True, ondelete='cascade', select=True),
        'name': fields.char('Description', size=64, select=True,required=True),
        'product_id': fields.many2one('product.product', 'Product'),
        'product_uom_qty': fields.float('Quantity', digits=(16,2), required=True),
        'price_unit': fields.float('Unit Price', required=True),
        'product_uom': fields.many2one('product.uom', 'Product UoM', required=True),
        'price_subtotal': fields.function(_amount_line, method=True, string='Subtotal',digits=(16, int(config['price_accuracy']))),
        'tax_id': fields.many2many('account.tax', 'repair_fee_line_tax', 'repair_fee_line_id', 'tax_id', 'Taxes'),
        'invoice_line_id': fields.many2one('account.invoice.line', 'Invoice Line', readonly=True),
        'to_invoice': fields.boolean('To Invoice'),
        'invoiced': fields.boolean('Invoiced',readonly=True),
    }
    _defaults = {
        'to_invoice': lambda *a: True,
    }
    
mrp_repair_fee()


class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'repair_line_id': fields.many2one('mrp.repair.line', 'Repair Operation Line', ondelete='set null', select=True, readonly=True),
    }
    _defaults = {
        'repair_line_id': lambda *a:False
    }
stock_move()

class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    _columns = {
        'repair_id': fields.many2one('mrp.repair', 'Repair Order', ondelete='set null', select=True, readonly=True),
    }
    _defaults = {
        'repair_id': lambda *a: False
    }
stock_picking()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
