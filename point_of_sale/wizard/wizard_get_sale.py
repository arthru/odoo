##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
#
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


import pooler
import netsvc
import wizard
from osv import osv


picking_form = """<?xml version="1.0"?>
<form string="Select an Open Sale Order">
	<field name="picking_id" domain="[('state','in',('assigned','confirmed'))]" context="{'contact_display':'partner'}"/>
</form>
"""

picking_fields = {
	'picking_id': {'string':'Sale Order', 'type':'many2one','relation': 'stock.picking','required':True}
}

def _sale_complete(self, cr, uid, data, context):
	pool = pooler.get_pool(cr.dbname)
	order = pool.get('pos.order').browse(cr,uid,data['id'],context)

	pick = pool.get('stock.picking').browse(cr,uid,data['form']['picking_id'],context)

	order.write(cr, uid, data['id'], {
		'last_out_picking':data['form']['picking_id'],
		'partner_id': pick.address_id and pick.address_id.partner_id.id
	})

	order = pool.get('stock.picking').write(cr,uid,[data['form']['picking_id']],{
		'invoice_state':'none',
		'pos_order': data['id']
	})

	for line in pick.move_lines:
		pool.get('pos.order.line').create(cr, uid, {
			'name': line.sale_line_id.name,
			'order_id': data['id'],
			'qty': line.product_qty,
			'product_id': line.product_id.id,
			'price_unit': line.sale_line_id.price_unit,
			'discount': line.sale_line_id.discount,
		})
	return {}

class pos_sale_get(wizard.interface):

	states = {
		'init' : {'actions' : [],
				 'result' : {'type' : 'form',
							 'arch': picking_form,
							 'fields': picking_fields,
							 'state' : (('end', 'Cancel'),
										('set', 'Confirm',
										 'gtk-ok', True)
										)
							 }
				 },
		'set' : {'actions' : [_sale_complete],
					 'result' : {'type' : 'state',
								 'state': "end",
							  }
				  },
	}

pos_sale_get('pos.sale.get')
