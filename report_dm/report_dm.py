# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution····
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

from osv import fields,osv
#Order quantity per Offer Steps
'''class report_order_quantity_offer_steps(osv.osv):
    _name = "report_order_quantity_offer_steps"
    _description = "Order quantity per Offer Steps"
    _auto = False
    _columns = {
        'name': fields.date('Month', readonly=True),
        'state': fields.selection([
            ('draft','Quotation'),
            ('waiting_date','Waiting Schedule'),
            ('manual','Manual in progress'),
            ('progress','In progress'),
            ('shipping_except','Shipping Exception'),
            ('invoice_except','Invoice Exception'),
            ('done','Done'),
            ('cancel','Cancel')
        ], 'Order State', readonly=True),
        'product_id':fields.many2one('product.product', 'Product', readonly=True),
        'quantity': fields.float('# of Products', readonly=True),
        'price_total': fields.float('Total Price', readonly=True),
        'price_average': fields.float('Average Price', readonly=True),
        'count': fields.integer('# of Lines', readonly=True),
    }
    _order = 'name desc,price_total desc'
    def init(self, cr):
        cr.execute("""
            create or replace view report_order_quantity_offer_steps as (
                select
                    min(l.id) as id,
                    to_char(s.date_order, 'YYYY-MM-01') as name,
                    s.state,
                    l.product_id,
                    sum(l.product_uom_qty*u.factor) as quantity,
                    count(*),
                    sum(l.product_uom_qty*l.price_unit) as price_total,
                    (sum(l.product_uom_qty*l.price_unit)/sum(l.product_uom_qty*u.factor))::decimal(16,2) as price_average
                from sale_order s
                    right join sale_order_line l on (s.id=l.order_id)
                    left join product_uom u on (u.id=l.product_uom)
                where l.product_uom_qty != 0
                group by l.product_id, to_char(s.date_order, 'YYYY-MM-01'),s.state
            )
        """)
report_sale_order_product()'''

#vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
