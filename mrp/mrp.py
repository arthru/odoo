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

from mx import DateTime
from osv import fields
from osv import osv
from tools.translate import _
import ir
import netsvc
import time

#----------------------------------------------------------
# Work Centers
#----------------------------------------------------------
# capacity_hour : capacity per hour. default: 1.0.
#          Eg: If 5 concurrent operations at one time: capacity = 5 (because 5 employees)
# unit_per_cycle : how many units are produced for one cycle
#
# TODO: Work Center may be recursive ?
#
class mrp_workcenter(osv.osv):
    _name = 'mrp.workcenter'
    _description = 'Work Center'
    _inherits = {'resource.resource':"resource_id"}
    _columns = {
#        'name': fields.char('Work Center Name', size=64, required=True),
        'note': fields.text('Description', help="Description of the workcenter. Explain here what's a cycle according to this workcenter."),
        'capacity_per_cycle': fields.float('Capacity per Cycle', help="Number of operations this workcenter can do in parallel. If this workcenter represents a team of 5 workers, the capacity per cycle is 5."),
        'time_cycle': fields.float('Time for 1 cycle (hour)', help="Time in hours for doing one cycle."),
        'time_start': fields.float('Time before prod.', help="Time in hours for the setup."),
        'time_stop': fields.float('Time after prod.', help="Time in hours for the cleaning."),
        'costs_hour': fields.float('Cost per hour'),
        'costs_hour_account_id': fields.many2one('account.analytic.account', 'Hour Account', domain=[('type','<>','view')],
            help="Complete this only if you want automatic analytic accounting entries on production orders."),
        'costs_cycle': fields.float('Cost per cycle'),
        'costs_cycle_account_id': fields.many2one('account.analytic.account', 'Cycle Account', domain=[('type','<>','view')],
            help="Complete this only if you want automatic analytic accounting entries on production orders."),
        'costs_journal_id': fields.many2one('account.analytic.journal', 'Analytic Journal'),
        'costs_general_account_id': fields.many2one('account.account', 'General Account', domain=[('type','<>','view')]),
#        'company_id': fields.many2one('res.company','Company',required=True),
       'resource_id': fields.many2one('resource.resource','Resource',ondelete='cascade'),
    }
    _defaults = {
        'capacity_per_cycle': lambda *a: 1.0,
     }
mrp_workcenter()


class mrp_property_group(osv.osv):
    """
    Group of mrp properties.
    """
    _name = 'mrp.property.group'
    _description = 'Property Group'
    _columns = {
        'name': fields.char('Property Group', size=64, required=True),
        'description': fields.text('Description'),
    }
mrp_property_group()

class mrp_property(osv.osv):
    """
    Properties of mrp.
    """
    _name = 'mrp.property'
    _description = 'Property'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'composition': fields.selection([('min','min'),('max','max'),('plus','plus')], 'Properties composition', required=True, help="Not used in computations, for information purpose only."),
        'group_id': fields.many2one('mrp.property.group', 'Property Group', required=True),
        'description': fields.text('Description'),
    }
    _defaults = {
        'composition': lambda *a: 'min',
    }
mrp_property()

class mrp_routing(osv.osv):
    """
    For specifying the routings of workcenters.
    """
    _name = 'mrp.routing'
    _description = 'Routing'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'active': fields.boolean('Active', help="If the active field is set to true, it will allow you to hide the routing without removing it."),
        'code': fields.char('Code', size=8),

        'note': fields.text('Description'),
        'workcenter_lines': fields.one2many('mrp.routing.workcenter', 'routing_id', 'Work Centers'),

        'location_id': fields.many2one('stock.location', 'Production Location',
            help="Keep empty if you produce at the location where the finished products are needed." \
                "Set a location if you produce at a fixed location. This can be a partner location " \
                "if you subcontract the manufacturing operations."
        ),
    }
    _defaults = {
        'active': lambda *a: 1,
    }
mrp_routing()

class mrp_routing_workcenter(osv.osv):
    """
    Defines working cycles and hours of a workcenter using routings.
    """
    _name = 'mrp.routing.workcenter'
    _description = 'Routing workcenter usage'
    _columns = {
        'workcenter_id': fields.many2one('mrp.workcenter', 'Work Center', required=True),
        'name': fields.char('Name', size=64, required=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of routing workcenters."),
        'cycle_nbr': fields.float('Number of Cycles', required=True,
            help="Time in hours for doing one cycle."),
        'hour_nbr': fields.float('Number of Hours', required=True, help="Cost per hour"),
        'routing_id': fields.many2one('mrp.routing', 'Parent Routing', select=True, ondelete='cascade',
             help="Routing indicates all the workcenters used, for how long and/or cycles." \
                "If Routing is indicated then,the third tab of a production order (workcenters) will be automatically pre-completed."),
        'note': fields.text('Description')
    }
    _defaults = {
        'cycle_nbr': lambda *a: 1.0,
        'hour_nbr': lambda *a: 0.0,
    }
mrp_routing_workcenter()

class mrp_bom(osv.osv):
    """
    Defines bills of material for a product.
    """
    _name = 'mrp.bom'
    _description = 'Bills of Material'
    
    def _child_compute(self, cr, uid, ids, name, arg, context={}):
        """ Gets child bom.
        @param self: The object pointer
        @param cr: The current row, from the database cursor,
        @param uid: The current user ID for security checks
        @param ids: List of selected IDs
        @param name: Name of the field
        @param arg: User defined argument
        @param context: A standard dictionary for contextual values
        @return:  Dictionary of values
        """
        result = {}
        bom_obj = self.pool.get('mrp.bom')
        for bom in self.browse(cr, uid, ids, context=context):
            result[bom.id] = map(lambda x: x.id, bom.bom_lines)
            if bom.bom_lines:
                continue
            ok = ((name=='child_complete_ids') and (bom.product_id.supply_method=='produce'))
            if bom.type=='phantom' or ok:
                sids = bom_obj.search(cr, uid, [('bom_id','=',False),('product_id','=',bom.product_id.id)])
                if sids:
                    bom2 = bom_obj.browse(cr, uid, sids[0], context=context)
                    result[bom.id] += map(lambda x: x.id, bom2.bom_lines)                 

        return result
    
    def _compute_type(self, cr, uid, ids, field_name, arg, context):
        """ Sets particular method for the selected bom type.
        @param field_name: Name of the field
        @param arg: User defined argument
        @return:  Dictionary of values
        """  
        res = dict(map(lambda x: (x,''), ids))
        for line in self.browse(cr, uid, ids):
            if line.type == 'phantom' and not line.bom_id:
                res[line.id] = 'set'
                continue
            if line.bom_lines or line.type == 'phantom':
                continue
            if line.product_id.supply_method == 'produce':
                if line.product_id.procure_method == 'make_to_stock':
                    res[line.id] = 'stock'
                else:
                    res[line.id] = 'order'
        return res
    
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'code': fields.char('Code', size=16),
        'active': fields.boolean('Active', help="If the active field is set to true, it will allow you to hide the bills of material without removing it."),
        'type': fields.selection([('normal','Normal BoM'),('phantom','Sets / Phantom')], 'BoM Type', required=True,
                                 help= "If a sub-product is used in several products, it can be useful to create its own BoM."\
                                 "Though if you don't want separated production orders for this sub-product, select Set/Phantom as BoM type."\
                                 "If a Phantom BoM is used for a root product, it will be sold and shipped as a set of components, instead of being produced."),
        'method': fields.function(_compute_type, string='Method', method=True, type='selection', selection=[('',''),('stock','On Stock'),('order','On Order'),('set','Set / Pack')]),
        'date_start': fields.date('Valid From', help="Validity of this BoM or component. Keep empty if it's always valid."),
        'date_stop': fields.date('Valid Until', help="Validity of this BoM or component. Keep empty if it's always valid."),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of bills of material."),
        'position': fields.char('Internal Reference', size=64, help="Reference to a position in an external plan."),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_uos_qty': fields.float('Product UOS Qty'),
        'product_uos': fields.many2one('product.uom', 'Product UOS', help="Product UOS (Unit of Sale) is the unit of measurement for the invoicing and promotion of stock."),
        'product_qty': fields.float('Product Qty', required=True),
        'product_uom': fields.many2one('product.uom', 'Product UOM', required=True, help="UoM (Unit of Measure) is the unit of measurement for the inventory control"),
        'product_rounding': fields.float('Product Rounding', help="Rounding applied on the product quantity."),
        'product_efficiency': fields.float('Product Efficiency', required=True, help="Material efficiency. A factor of 0.9 means a loss of 10% in the production."),
        'bom_lines': fields.one2many('mrp.bom', 'bom_id', 'BoM Lines'),
        'bom_id': fields.many2one('mrp.bom', 'Parent BoM', ondelete='cascade', select=True),
        'routing_id': fields.many2one('mrp.routing', 'Routing', help="The list of operations (list of workcenters) to produce the finished product. The routing is mainly used to compute workcenter costs during operations and to plan future loads on workcenters based on production planning."),
        'property_ids': fields.many2many('mrp.property', 'mrp_bom_property_rel', 'bom_id','property_id', 'Properties'),
        'revision_ids': fields.one2many('mrp.bom.revision', 'bom_id', 'BoM Revisions'),
        'revision_type': fields.selection([('numeric','numeric indices'),('alpha','alphabetical indices')], 'Index type'),
        'child_complete_ids': fields.function(_child_compute,relation='mrp.bom', method=True, string="BoM Hierarchy", type='many2many'),
        'company_id': fields.many2one('res.company','Company',required=True),
        'multi_level_bom': fields.boolean('Multi-level BoM'),
    }
    _defaults = {
        'active': lambda *a: 1,
        'product_efficiency': lambda *a: 1.0,
        'product_qty': lambda *a: 1.0,
        'product_rounding': lambda *a: 1.0,
        'type': lambda *a: 'normal',
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'mrp.bom', context=c),
        'multi_level_bom': lambda *a: 0, 
    }
    _order = "sequence"
    _sql_constraints = [
        ('bom_qty_zero', 'CHECK (product_qty>0)',  'All product quantities must be greater than 0.\n' \
            'You should install the mrp_subproduct module if you want to manage extra products on BoMs !'),
    ]

    def _check_recursion(self, cr, uid, ids):
        level = 100
        while len(ids):
            cr.execute('select distinct bom_id from mrp_bom where id =ANY(%s)',(ids,))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True
    _constraints = [
        (_check_recursion, 'Error ! You can not create recursive BoM.', ['parent_id'])
    ]


    def onchange_product_id(self, cr, uid, ids, product_id, name, context={}):
        """ Changes UoM and name if product_id changes.
        @param name: Name of the field
        @param product_id: Changed product_id
        @return:  Dictionary of changed values
        """
        if product_id:
            prod = self.pool.get('product.product').browse(cr, uid, [product_id])[0]
            v = {'product_uom': prod.uom_id.id}
            if not name:
                v['name'] = prod.name
            return {'value': v}
        return {}

    def _bom_find(self, cr, uid, product_id, product_uom, properties=[]):
        """ Finds BoM for particular product and product uom.
        @param product_id: Selected product.
        @param product_uom: Unit of measure of a product.
        @param properties: List of related properties.
        @return: False or BoM id.
        """
        bom_result = False
        # Why searching on BoM without parent ?
        cr.execute('select id from mrp_bom where product_id=%s and bom_id is null order by sequence', (product_id,))
        ids = map(lambda x: x[0], cr.fetchall())
        max_prop = 0
        result = False
        for bom in self.pool.get('mrp.bom').browse(cr, uid, ids):
            prop = 0
            for prop_id in bom.property_ids:
                if prop_id.id in properties:
                    prop += 1
            if (prop > max_prop) or ((max_prop == 0) and not result):
                result = bom.id
                max_prop = prop
        return result

    def _bom_explode(self, cr, uid, bom, factor, properties, addthis=False, level=0):
        """ Finds Products and Workcenters for related BoM for manufacturing order.
        @param bom: BoM of particular product.
        @param factor: Factor of product UoM.
        @param properties: A dictionary for contextual values.
        @param addthis: If BoM found then True else False.
        @param level: Depth level to find BoM lines starts from 10.
        @return: result: List of dictionaries containing product details.
                 result2: List of dictionaries containing workcenter details.
        """
        factor = factor / (bom.product_efficiency or 1.0)
        factor = rounding(factor, bom.product_rounding)
        if factor < bom.product_rounding:
            factor = bom.product_rounding
        result = []
        result2 = []
        phantom = False
        if bom.type == 'phantom' and not bom.bom_lines:
            newbom = self._bom_find(cr, uid, bom.product_id.id, bom.product_uom.id, properties)
            if newbom:
                res = self._bom_explode(cr, uid, self.browse(cr, uid, [newbom])[0], factor*bom.product_qty, properties, addthis=True, level=level+10)
                result = result + res[0]
                result2 = result2 + res[1]
                phantom = True
            else:
                phantom = False
        if not phantom:
            if addthis and not bom.bom_lines:
                result.append(
                {
                    'name': bom.product_id.name,
                    'product_id': bom.product_id.id,
                    'product_qty': bom.product_qty * factor,
                    'product_uom': bom.product_uom.id,
                    'product_uos_qty': bom.product_uos and bom.product_uos_qty * factor or False,
                    'product_uos': bom.product_uos and bom.product_uos.id or False,
                })
            if bom.routing_id:
                for wc_use in bom.routing_id.workcenter_lines:
                    wc = wc_use.workcenter_id
                    d, m = divmod(factor, wc_use.workcenter_id.capacity_per_cycle)
                    mult = (d + (m and 1.0 or 0.0))
                    cycle = mult * wc_use.cycle_nbr
                    print mult, wc_use.hour_nbr, wc.time_start, wc.time_stop, cycle
                    result2.append({
                        'name': bom.routing_id.name,
                        'workcenter_id': wc.id,
                        'sequence': level+(wc_use.sequence or 0),
                        'cycle': cycle,
                        'hour': float(wc_use.hour_nbr*mult + ((wc.time_start or 0.0)+(wc.time_stop or 0.0)+cycle*(wc.time_cycle or 0.0)) * (wc.time_efficiency or 1.0)),
                    })
            for bom2 in bom.bom_lines:
                res = self._bom_explode(cr, uid, bom2, factor, properties, addthis=True, level=level+10)
                result = result + res[0]
                result2 = result2 + res[1]
        return result, result2

    def set_indices(self, cr, uid, ids, context={}):
        """ Sets Indices.
        @return: True
        """
        if not ids or (ids and not ids[0]):
            return True
        res = self.read(cr, uid, ids, ['revision_ids', 'revision_type'])
        rev_ids = res[0]['revision_ids']
        idx = 1
        new_idx = []
        bom_rev_obj = self.pool.get('mrp.bom.revision')
        for rev_id in rev_ids:
            if res[0]['revision_type'] == 'numeric':
                bom_rev_obj.write(cr, uid, [rev_id], {'indice': idx})
            else:
                bom_rev_obj.write(cr, uid, [rev_id], {'indice': "%c" %(idx+96,)})
            idx += 1
        return True

mrp_bom()

class mrp_bom_revision(osv.osv):
    _name = 'mrp.bom.revision'
    _description = 'Bill of material revisions'
    
    _columns = {
        'name': fields.char('Modification name', size=64, required=True),
        'description': fields.text('Description'),
        'date': fields.date('Modification Date'),
        'indice': fields.char('Revision', size=16),
        'last_indice': fields.char('last indice', size=64),
        'author_id': fields.many2one('res.users', 'Author'),
        'bom_id': fields.many2one('mrp.bom', 'BoM', select=True),
    }

    _defaults = {
        'author_id': lambda x, y, z, c: z,
        'date': lambda *a: time.strftime('%Y-%m-%d'),
    }

mrp_bom_revision()

def rounding(f, r):
    if not r:
        return f
    return round(f / r) * r

class many2many_domain(fields.many2many):
    def set(self, cr, obj, id, name, values, user=None, context=None):
        if not values:
            return
        return super(many2many_domain, self).set(cr, obj, id, name, values, user=user,
                context=context)

    def get(self, cr, obj, ids, name, user=None, offset=0, context=None, values=None):
        if not context:
            context = {}
        res = {}
        move_obj = obj.pool.get('stock.move')
        for prod in obj.browse(cr, user, ids, context=context):
            cr.execute("SELECT move_id from mrp_production_move_ids where\
                production_id=%s" % (prod.id))
            m_ids = map(lambda x: x[0], cr.fetchall())
            final = move_obj.search(cr, user, self._domain + [('id', 'in', tuple(m_ids))])
            res[prod.id] = final
        return res

class one2many_domain(fields.one2many):
    def set(self, cr, obj, id, field, values, user=None, context=None):
        if not values:
            return
        return super(one2many_domain, self).set(cr, obj, id, field, values, 
                                            user=user, context=context)

    def get(self, cr, obj, ids, name, user=None, offset=0, context=None, values=None):
        if not context:
            context = {}
        res = {}
        move_obj = obj.pool.get('stock.move')
        for prod in obj.browse(cr, user, ids, context=context):
            cr.execute("SELECT id from stock_move where production_id=%s" % (prod.id))
            m_ids = map(lambda x: x[0], cr.fetchall())
            final = move_obj.search(cr, user, self._domain + [('id', 'in', tuple(m_ids))])
            res[prod.id] = final
        return res

class mrp_production(osv.osv):
    """
    Production Orders / Manufacturing Orders
    """
    _name = 'mrp.production'
    _description = 'Production'
    _date_name  = 'date_planned'    

    def _production_calc(self, cr, uid, ids, prop, unknow_none, context={}):
        """ Calculates total hours and total no. of cycles for a production order.
        @param prop: Name of field.
        @param unknow_none: 
        @return: Dictionary of values.
        """
        result = {}
        for prod in self.browse(cr, uid, ids, context=context):
            result[prod.id] = {
                'hour_total': 0.0,
                'cycle_total': 0.0,
            }
            for wc in prod.workcenter_lines:
                result[prod.id]['hour_total'] += wc.hour
                result[prod.id]['cycle_total'] += wc.cycle
        return result

    def _production_date_end(self, cr, uid, ids, prop, unknow_none, context={}):
        """ Finds production end date.
        @param prop: Name of field.
        @param unknow_none: 
        @return: Dictionary of values.
        """
        result = {}
        for prod in self.browse(cr, uid, ids, context=context):
            result[prod.id] = prod.date_planned
        return result

    def _production_date(self, cr, uid, ids, prop, unknow_none, context={}):
        """ Finds production planned date.
        @param prop: Name of field.
        @param unknow_none:  
        @return: Dictionary of values.
        """
        result = {}
        for prod in self.browse(cr, uid, ids, context=context):
            result[prod.id] = prod.date_planned[:10]
        return result

    def _ref_calc(self, cr, uid, ids, field_names=None, arg=False, context={}):
        """ Finds reference sale order for production order.
        @param field_names: Names of fields.
        @param arg: User defined arguments
        @return: Dictionary of values.
        """
        res = {}
        for f in field_names:
            for order_id in ids:
                res[order_id] = {f:False}
        return res

    _columns = {
        'name': fields.char('Reference', size=64, required=True),
        'origin': fields.char('Source Document', size=64, help="Reference of the document that generated this production order request."),
        'priority': fields.selection([('0','Not urgent'),('1','Normal'),('2','Urgent'),('3','Very Urgent')], 'Priority'),

        'product_id': fields.many2one('product.product', 'Product', required=True, domain=[('type','<>','service')]),
        'product_qty': fields.float('Product Qty', required=True, states={'draft':[('readonly',False)]}, readonly=True),
        'product_uom': fields.many2one('product.uom', 'Product UOM', required=True, states={'draft':[('readonly',False)]}, readonly=True),
        'product_uos_qty': fields.float('Product UoS Qty', states={'draft':[('readonly',False)]}, readonly=True),
        'product_uos': fields.many2one('product.uom', 'Product UoS', states={'draft':[('readonly',False)]}, readonly=True),

        'location_src_id': fields.many2one('stock.location', 'Raw Materials Location', required=True,
            help="Location where the system will look for components."),
        'location_dest_id': fields.many2one('stock.location', 'Finished Products Location', required=True,
            help="Location where the system will stock the finished products."),

        'date_planned_end': fields.function(_production_date_end, method=True, type='date', string='Scheduled End'),
        'date_planned_date': fields.function(_production_date, method=True, type='date', string='Scheduled Date'),
        'date_planned': fields.datetime('Scheduled date', required=True, select=1),
        'date_start': fields.datetime('Start Date'),
        'date_finnished': fields.datetime('End Date'),

        'bom_id': fields.many2one('mrp.bom', 'Bill of Material', domain=[('bom_id','=',False)]),
        'routing_id': fields.many2one('mrp.routing', string='Routing', on_delete='set null', help="The list of operations (list of workcenters) to produce the finished product. The routing is mainly used to compute workcenter costs during operations and to plan futur loads on workcenters based on production plannification."),

        'picking_id': fields.many2one('stock.picking', 'Picking list', readonly=True,
            help="This is the internal picking list that brings the finished product to the production plan"),
        'move_prod_id': fields.many2one('stock.move', 'Move product', readonly=True),
        'move_lines': many2many_domain('stock.move', 'mrp_production_move_ids', 'production_id', 'move_id', 'Products to Consumme', domain=[('state','not in', ('done', 'cancel'))]),
        'move_lines2': many2many_domain('stock.move', 'mrp_production_move_ids', 'production_id', 'move_id', 'Consummed Products', domain=[('state','in', ('done', 'cancel'))]),
        'move_created_ids': one2many_domain('stock.move', 'production_id', 'Moves Created', domain=[('state','not in', ('done', 'cancel'))]),
        'move_created_ids2': one2many_domain('stock.move', 'production_id', 'Moves Created', domain=[('state','in', ('done', 'cancel'))]),
        'product_lines': fields.one2many('mrp.production.product.line', 'production_id', 'Scheduled goods'),
        'workcenter_lines': fields.one2many('mrp.production.workcenter.line', 'production_id', 'Work Centers Utilisation'),
        'state': fields.selection([('draft','Draft'),('picking_except', 'Picking Exception'),('confirmed','Waiting Goods'),('ready','Ready to Produce'),('in_production','In Production'),('cancel','Cancelled'),('done','Done')],'State', readonly=True,
                                    help='When the production order is created the state is set to \'Draft\'.\n If the order is confirmed the state is set to \'Waiting Goods\'.\n If any exceptions are there, the state is set to \'Picking Exception\'.\
                                    \nIf the stock is available then the state is set to \'Ready to Produce\'.\n When the production get started then the state is set to \'In Production\'.\n When the production is over, the state is set to \'Done\'.'),
        'hour_total': fields.function(_production_calc, method=True, type='float', string='Total Hours', multi='workorder'),
        'cycle_total': fields.function(_production_calc, method=True, type='float', string='Total Cycles', multi='workorder'),

        'sale_name': fields.function(_ref_calc, method=True, multi='sale_name', type='char', string='Sale Name', help='Indicate the name of sale order.'),
        'sale_ref': fields.function(_ref_calc, method=True, multi='sale_ref', type='char', string='Sale Reference', help='Indicate the Customer Reference from sale order.'),
        'company_id': fields.many2one('res.company','Company',required=True),
    }
    _defaults = {
        'priority': lambda *a: '1',
        'state': lambda *a: 'draft',
        'date_planned': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'product_qty':  lambda *a: 1.0,
        'name': lambda x, y, z, c: x.pool.get('ir.sequence').get(y, z, 'mrp.production') or '/',
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'mrp.production', context=c),
    }
    _order = 'date_planned asc, priority desc';
    
    def unlink(self, cr, uid, ids, context=None):
        productions = self.read(cr, uid, ids, ['state'])
        unlink_ids = []
        for s in productions:
            if s['state'] in ['draft','cancel']:
                unlink_ids.append(s['id'])
            else:
                raise osv.except_osv(_('Invalid action !'), _('Cannot delete Production Order(s) which are in %s State!' % s['state']))
        return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)

    def copy(self, cr, uid, id, default=None,context=None):
        if not default:
            default = {}
        default.update({
            'name': self.pool.get('ir.sequence').get(cr, uid, 'mrp.production'),
            'move_lines' : [],
            'move_created_ids': [],
            'state': 'draft'
        })
        return super(mrp_production, self).copy(cr, uid, id, default, context)

    def location_id_change(self, cr, uid, ids, src, dest, context={}):
        """ Changes destination location if source location is changed.
        @param src: Source location id.
        @param dest: Destination location id.
        @return: Dictionary of values.
        """
        if dest:
            return {}
        if src:
            return {'value': {'location_dest_id': src}}
        return {}

    def product_id_change(self, cr, uid, ids, product):
        """ Finds UoM of changed product.
        @param product: Id of changed product.
        @return: Dictionary of values.
        """
        if not product:
            return {}
        res = self.pool.get('product.product').read(cr, uid, [product], ['uom_id'])[0]
        uom = res['uom_id'] and res['uom_id'][0]
        result = {'product_uom': uom}
        return {'value': result}

    def bom_id_change(self, cr, uid, ids, product):
        """ Finds routing for changed BoM.
        @param product: Id of product.
        @return: Dictionary of values.
        """
        if not product:
            return {}
        res = self.pool.get('mrp.bom').read(cr, uid, [product], ['routing_id'])[0]
        routing_id = res['routing_id'] and res['routing_id'][0]
        result = {'routing_id': routing_id}
        return {'value': result}

    def action_picking_except(self, cr, uid, ids):
        """ Changes the state to Exception.
        @return: True 
        """
        self.write(cr, uid, ids, {'state': 'picking_except'})
        return True

    def action_compute(self, cr, uid, ids, properties=[]):
        """ Computes bills of material of a product.
        @param properties: List containing dictionaries of properties.
        @return: No. of products.
        """
        results = []
        bom_obj = self.pool.get('mrp.bom')
        prod_line_obj = self.pool.get('mrp.production.product.line')
        workcenter_line_obj = self.pool.get('mrp.production.workcenter.line')
        for production in self.browse(cr, uid, ids):
            cr.execute('delete from mrp_production_product_line where production_id=%s', (production.id,))
            cr.execute('delete from mrp_production_workcenter_line where production_id=%s', (production.id,))
            bom_point = production.bom_id
            bom_id = production.bom_id.id
            if not bom_point:
                bom_id = bom_obj._bom_find(cr, uid, production.product_id.id, production.product_uom.id, properties)
                if bom_id:
                    bom_point = bom_obj.browse(cr, uid, bom_id)
                    routing_id = bom_point.routing_id.id or False
                    self.write(cr, uid, [production.id], {'bom_id': bom_id, 'routing_id': routing_id})

            if not bom_id:
                raise osv.except_osv(_('Error'), _("Couldn't find bill of material for product"))

            #if bom_point.routing_id and bom_point.routing_id.location_id:
            #   self.write(cr, uid, [production.id], {'location_src_id': bom_point.routing_id.location_id.id})

            factor = production.product_qty * production.product_uom.factor / bom_point.product_uom.factor
            res = bom_obj._bom_explode(cr, uid, bom_point, factor / bom_point.product_qty, properties)
            results = res[0]
            results2 = res[1]
            for line in results:
                line['production_id'] = production.id
                prod_line_obj.create(cr, uid, line)
            for line in results2:
                line['production_id'] = production.id
                workcenter_line_obj.create(cr, uid, line)
        return len(results)

    def action_cancel(self, cr, uid, ids):
        """ Cancels the production order and related stock moves.
        @return: True
        """
        move_obj = self.pool.get('stock.move')
        for production in self.browse(cr, uid, ids):
            if production.move_created_ids:
                move_obj.action_cancel(cr, uid, [x.id for x in production.move_created_ids])
            move_obj.action_cancel(cr, uid, [x.id for x in production.move_lines])
        self.write(cr, uid, ids, {'state': 'cancel'}) #,'move_lines':[(6,0,[])]})
        return True

    #XXX: may be a bug here; lot_lines are unreserved for a few seconds;
    #     between the end of the picking list and the call to this function
    def action_ready(self, cr, uid, ids):
        """ Changes the production state to Ready and location id of stock move.
        @return: True
        """
        move_obj = self.pool.get('stock.move')
        self.write(cr, uid, ids, {'state': 'ready'})
        for production in self.browse(cr, uid, ids):
            if production.move_prod_id:
                move_obj.write(cr, uid, [production.move_prod_id.id],
                        {'location_id': production.location_dest_id.id})
        return True

    def action_production_end(self, cr, uid, ids):
        """ Changes production state to Finish and writes finished date.
        @return: True
        """
        for production in self.browse(cr, uid, ids):
            self._costs_generate(cr, uid, production)
        return self.write(cr, uid, ids, {'state': 'done', 'date_finnished': time.strftime('%Y-%m-%d %H:%M:%S')})

    def test_production_done(self, cr, uid, ids):
        """ Tests whether production is done or not.
        @return: True or False
        """
        res = True
        for production in self.browse(cr, uid, ids):            
            if production.move_lines:                
               res = False

            if production.move_created_ids:                
               res = False        
        return res

    def action_produce(self, cr, uid, production_id, production_qty, production_mode, context=None):
        """ To produce final product base on production mode (consume/consume&produce).
        If Production mode is consume, all stock move lines of raw materials will be done/consumed.
        If Production mode is consume & produce, all stock move lines of raw materials will be done/consumed
        and stock move lines of final product will be also done/produced.
        @param production_id: the ID of mrp.production object
        @param production_qty: specify qty to produce
        @param production_mode: specify production mode (consume/consume&produce).
        @return: True
        """              
        stock_mov_obj = self.pool.get('stock.move')
        production = self.browse(cr, uid, production_id)
        
        raw_product_todo = []
        final_product_todo = []        
        
        if production_mode in ['consume','consume_produce']:
            # To consume remaining qty of raw materials 
            consumed_products = {}
            produced_qty = 0
            for consumed_product in production.move_lines2:
                if consumed_product.scraped:
                    continue
                if not consumed_products.get(consumed_product.product_id.id, False):
                    consumed_products[consumed_product.product_id.id] = 0
                consumed_products[consumed_product.product_id.id] += consumed_product.product_qty
            
            for produced_product in production.move_created_ids2:
                if produced_product.scraped:
                    continue
                produced_qty += produced_product.product_qty

            for raw_product in production.move_lines:                
                consumed_qty = consumed_products.get(raw_product.product_id.id, 0)                
                consumed_qty -= produced_qty                            
                rest_qty = production_qty - consumed_qty 
                if rest_qty > production.product_qty:
                   rest_qty = production.product_qty            
                if rest_qty > 0:
                    stock_mov_obj.action_consume(cr, uid, [raw_product.id], rest_qty, production.location_src_id.id, context=context)

        if production_mode == 'consume_produce':
            # To produce remaining qty of final product
            vals = {'state':'confirmed'}
            final_product_todo = [x.id for x in production.move_created_ids]
            stock_mov_obj.write(cr, uid, final_product_todo, vals)
            produced_products = {}
            for produced_product in production.move_created_ids2:
                if produced_product.scraped:
                    continue
                if not produced_products.get(produced_product.product_id.id, False):
                    produced_products[produced_product.product_id.id] = 0
                produced_products[produced_product.product_id.id] += produced_product.product_qty

            for produce_product in production.move_created_ids:                
                produced_qty = produced_products.get(produce_product.product_id.id, 0)                            
                rest_qty = production.product_qty - produced_qty
                if rest_qty <= production_qty:
                   production_qty = rest_qty 
                if rest_qty > 0 :
                    stock_mov_obj.action_consume(cr, uid, [produce_product.id], production_qty, production.location_dest_id.id, context=context)            
        
        
        for raw_product in production.move_lines2: 
            new_parent_ids = []           
            parent_move_ids = [x.id for x in raw_product.move_history_ids]
            for final_product in production.move_created_ids2:
                if final_product.id not in parent_move_ids:
                    new_parent_ids.append(final_product.id)
            for new_parent_id in new_parent_ids:
                stock_mov_obj.write(cr, uid, [raw_product.id], {'move_history_ids': [(4,new_parent_id)]})

        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'mrp.production', production_id, 'button_produce_done', cr)
        return True

    def _costs_generate(self, cr, uid, production):
        """ Calculates total costs at the end of the production.
        @param production: Id of production order.
        @return: Calculated amount.
        """
        amount = 0.0
        analytic_line_obj = self.pool.get('account.analytic.line')
        for wc_line in production.workcenter_lines:
            wc = wc_line.workcenter_id
            if wc.costs_journal_id and wc.costs_general_account_id:
                value = wc_line.hour * wc.costs_hour
                account = wc.costs_hour_account_id.id
                if value and account:
                    amount += value
                    analytic_line_obj.create(cr, uid, {
                        'name': wc_line.name + ' (H)',
                        'amount': value,
                        'account_id': account,
                        'general_account_id': wc.costs_general_account_id.id,
                        'journal_id': wc.costs_journal_id.id,
                        'code': wc.code
                    } )
            if wc.costs_journal_id and wc.costs_general_account_id:
                value = wc_line.cycle * wc.costs_cycle
                account = wc.costs_cycle_account_id.id
                if value and account:
                    amount += value
                    analytic_line_obj.create(cr, uid, {
                        'name': wc_line.name+' (C)',
                        'amount': value,
                        'account_id': account,
                        'general_account_id': wc.costs_general_account_id.id,
                        'journal_id': wc.costs_journal_id.id,
                        'code': wc.code
                    } )
        return amount

    def action_in_production(self, cr, uid, ids):
        """ Changes state to In Production and writes starting date.
        @return: True 
        """
        move_ids = []        
        self.write(cr, uid, ids, {'state': 'in_production', 'date_start': time.strftime('%Y-%m-%d %H:%M:%S')})
        return True

    def test_if_product(self, cr, uid, ids):
        """
        @return: True or False
        """
        res = True
        for production in self.browse(cr, uid, ids):
            if not production.product_lines:
                if not self.action_compute(cr, uid, [production.id]):
                    res = False
        return res

    def _get_auto_picking(self, cr, uid, production):
        return True

    def action_confirm(self, cr, uid, ids):
        """ Confirms production order.
        @return: Newly generated picking Id.
        """
        picking_id = False
        proc_ids = []
        seq_obj = self.pool.get('ir.sequence')
        pick_obj = self.pool.get('stock.picking')
        move_obj = self.pool.get('stock.move')
        proc_obj = self.pool.get('mrp.procurement')
        wf_service = netsvc.LocalService("workflow")
        for production in self.browse(cr, uid, ids):
            if not production.product_lines:
                self.action_compute(cr, uid, [production.id])
                production = self.browse(cr, uid, [production.id])[0]
            routing_loc = None
            pick_type = 'internal'
            address_id = False
            if production.bom_id.routing_id and production.bom_id.routing_id.location_id:
                routing_loc = production.bom_id.routing_id.location_id
                if routing_loc.usage <> 'internal':
                    pick_type = 'out'
                address_id = routing_loc.address_id and routing_loc.address_id.id or False
                routing_loc = routing_loc.id
            pick_name = seq_obj.get(cr, uid, 'stock.picking.' + pick_type)
            picking_id = pick_obj.create(cr, uid, {
                'name': pick_name,
                'origin': (production.origin or '').split(':')[0] + ':' + production.name,
                'type': pick_type,
                'move_type': 'one',
                'state': 'auto',
                'address_id': address_id,
                'auto_picking': self._get_auto_picking(cr, uid, production),
                'company_id': production.company_id.id,
            })

            source = production.product_id.product_tmpl_id.property_stock_production.id
            data = {
                'name':'PROD:' + production.name,
                'date_planned': production.date_planned,
                'product_id': production.product_id.id,
                'product_qty': production.product_qty,
                'product_uom': production.product_uom.id,
                'product_uos_qty': production.product_uos and production.product_uos_qty or False,
                'product_uos': production.product_uos and production.product_uos.id or False,
                'location_id': source,
                'location_dest_id': production.location_dest_id.id,
                'move_dest_id': production.move_prod_id.id,
                'state': 'waiting',
                'company_id': production.company_id.id,
            }
            res_final_id = move_obj.create(cr, uid, data)

            self.write(cr, uid, [production.id], {'move_created_ids': [(6, 0, [res_final_id])]})
            moves = []
            for line in production.product_lines:
                move_id = False
                newdate = production.date_planned
                if line.product_id.type in ('product', 'consu'):
                    res_dest_id = move_obj.create(cr, uid, {
                        'name':'PROD:' + production.name,
                        'date_planned': production.date_planned,
                        'product_id': line.product_id.id,
                        'product_qty': line.product_qty,
                        'product_uom': line.product_uom.id,
                        'product_uos_qty': line.product_uos and line.product_uos_qty or False,
                        'product_uos': line.product_uos and line.product_uos.id or False,
                        'location_id': routing_loc or production.location_src_id.id,
                        'location_dest_id': source,
                        'move_dest_id': res_final_id,
                        'state': 'waiting',
                        'company_id': production.company_id.id,
                    })
                    moves.append(res_dest_id)
                    move_id = move_obj.create(cr, uid, {
                        'name':'PROD:' + production.name,
                        'picking_id':picking_id,
                        'product_id': line.product_id.id,
                        'product_qty': line.product_qty,
                        'product_uom': line.product_uom.id,
                        'product_uos_qty': line.product_uos and line.product_uos_qty or False,
                        'product_uos': line.product_uos and line.product_uos.id or False,
                        'date_planned': newdate,
                        'move_dest_id': res_dest_id,
                        'location_id': production.location_src_id.id,
                        'location_dest_id': routing_loc or production.location_src_id.id,
                        'state': 'waiting',
                        'company_id': production.company_id.id,
                    })
                proc_id = proc_obj.create(cr, uid, {
                    'name': (production.origin or '').split(':')[0] + ':' + production.name,
                    'origin': (production.origin or '').split(':')[0] + ':' + production.name,
                    'date_planned': newdate,
                    'product_id': line.product_id.id,
                    'product_qty': line.product_qty,
                    'product_uom': line.product_uom.id,
                    'product_uos_qty': line.product_uos and line.product_qty or False,
                    'product_uos': line.product_uos and line.product_uos.id or False,
                    'location_id': production.location_src_id.id,
                    'procure_method': line.product_id.procure_method,
                    'move_id': move_id,
                    'company_id': production.company_id.id,
                })
                wf_service.trg_validate(uid, 'mrp.procurement', proc_id, 'button_confirm', cr)
                proc_ids.append(proc_id)
            wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
            self.write(cr, uid, [production.id], {'picking_id': picking_id, 'move_lines': [(6,0,moves)], 'state':'confirmed'})
        return picking_id

    def force_production(self, cr, uid, ids, *args):
        """ Assigns products.
        @param *args: Arguments
        @return: True
        """
        pick_obj = self.pool.get('stock.picking')
        pick_obj.force_assign(cr, uid, [prod.picking_id.id for prod in self.browse(cr, uid, ids)])
        return True

mrp_production()

class mrp_production_workcenter_line(osv.osv):
    _name = 'mrp.production.workcenter.line'
    _description = 'Work Orders'
    _order = 'sequence'
    
    _columns = {
        'name': fields.char('Work Order', size=64, required=True),
        'workcenter_id': fields.many2one('mrp.workcenter', 'Work Center', required=True),
        'cycle': fields.float('Nbr of cycles', digits=(16,2)),
        'hour': fields.float('Nbr of hours', digits=(16,2)),
        'sequence': fields.integer('Sequence', required=True, help="Gives the sequence order when displaying a list of work orders."),
        'production_id': fields.many2one('mrp.production', 'Production Order', select=True, ondelete='cascade'),
    }
    _defaults = {
        'sequence': lambda *a: 1,
        'hour': lambda *a: 0,
        'cycle': lambda *a: 0,
    }
mrp_production_workcenter_line()

class mrp_production_product_line(osv.osv):
    _name = 'mrp.production.product.line'
    _description = 'Production scheduled products'
    
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_qty': fields.float('Product Qty', required=True),
        'product_uom': fields.many2one('product.uom', 'Product UOM', required=True),
        'product_uos_qty': fields.float('Product UOS Qty'),
        'product_uos': fields.many2one('product.uom', 'Product UOS'),
        'production_id': fields.many2one('mrp.production', 'Production Order', select=True),
    }
mrp_production_product_line()

# ------------------------------------------------------------------
# Procurement
# ------------------------------------------------------------------
#
# Produce, Buy or Find products and place a move
#     then wizard for picking lists & move
#
class mrp_procurement(osv.osv):
    """
    Procument Orders
    """
    _name = "mrp.procurement"
    _description = "Procurement"
    _order = 'priority,date_planned'
    
    _columns = {
        'name': fields.char('Reason', size=64, required=True, help='Procurement name.'),
        'origin': fields.char('Source Document', size=64,
            help="Reference of the document that created this Procurement.\n"
            "This is automatically completed by Open ERP."),
        'priority': fields.selection([('0','Not urgent'),('1','Normal'),('2','Urgent'),('3','Very Urgent')], 'Priority', required=True),
        'date_planned': fields.datetime('Scheduled date', required=True),
        'date_close': fields.datetime('Date Closed'),
        'product_id': fields.many2one('product.product', 'Product', required=True, states={'draft':[('readonly',False)]}, readonly=True),
        'product_qty': fields.float('Quantity', required=True, states={'draft':[('readonly',False)]}, readonly=True),
        'product_uom': fields.many2one('product.uom', 'Product UoM', required=True, states={'draft':[('readonly',False)]}, readonly=True),
        'product_uos_qty': fields.float('UoS Quantity', states={'draft':[('readonly',False)]}, readonly=True),
        'product_uos': fields.many2one('product.uom', 'Product UoS', states={'draft':[('readonly',False)]}, readonly=True),
        'move_id': fields.many2one('stock.move', 'Reservation', ondelete='set null'),

        'bom_id': fields.many2one('mrp.bom', 'BoM', ondelete='cascade', select=True),

        'close_move': fields.boolean('Close Move at end', required=True),
        'location_id': fields.many2one('stock.location', 'Location', required=True, states={'draft':[('readonly',False)]}, readonly=True),
        'procure_method': fields.selection([('make_to_stock','from stock'),('make_to_order','on order')], 'Procurement Method', states={'draft':[('readonly',False)], 'confirmed':[('readonly',False)]},
            readonly=True, required=True, help="If you encode manually a Procurement, you probably want to use" \
            " a make to order method."),

        'purchase_id': fields.many2one('purchase.order', 'Purchase Order'),
        'note': fields.text('Note'),

        'property_ids': fields.many2many('mrp.property', 'mrp_procurement_property_rel', 'procurement_id','property_id', 'Properties'),

        'message': fields.char('Latest error', size=64, help="Exception occurred while computing procurement orders."),
        'state': fields.selection([
            ('draft','Draft'),
            ('confirmed','Confirmed'),
            ('exception','Exception'),
            ('running','Running'),
            ('cancel','Cancel'),
            ('ready','Ready'),
            ('done','Done'),
            ('waiting','Waiting')], 'State', required=True,
            help='When a procurement is created the state is set to \'Draft\'.\n If the procurement is confirmed, the state is set to \'Confirmed\'.\
            \nAfter confirming the state is set to \'Running\'.\n If any exception arises in the order then the state is set to \'Exception\'.\n Once the exception is removed the state becomes \'Ready\'.\n It is in \'Waiting\'. state when the procurement is waiting for another one to finish.'),
        'note': fields.text('Note'),
        'company_id': fields.many2one('res.company','Company',required=True),
    }
    _defaults = {
        'state': lambda *a: 'draft',
        'priority': lambda *a: '1',
        'date_planned': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'close_move': lambda *a: 0,
        'procure_method': lambda *a: 'make_to_order',
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'mrp.procurement', context=c)
    }

    def unlink(self, cr, uid, ids, context=None):
        procurements = self.read(cr, uid, ids, ['state'])
        unlink_ids = []
        for s in procurements:
            if s['state'] in ['draft','cancel']:
                unlink_ids.append(s['id'])
            else:
                raise osv.except_osv(_('Invalid action !'), _('Cannot delete Procurement Order(s) which are in %s State!' % s['state']))
        return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)

    def onchange_product_id(self, cr, uid, ids, product_id, context={}):
        """ Finds UoM and UoS of changed product.
        @param product_id: Changed id of product.
        @return: Dictionary of values.
        """
        if product_id:
            w = self.pool.get('product.product').browse(cr, uid, product_id, context)
            v = {
                'product_uom': w.uom_id.id,
                'product_uos': w.uos_id and w.uos_id.id or w.uom_id.id
            }
            return {'value': v}
        return {}

    def check_product(self, cr, uid, ids):
        """ Checks product type.
        @return: True or False 
        """
        for procurement in self.browse(cr, uid, ids):
            if procurement.product_id.type in ('product', 'consu'):
                return True
        return False

    def check_move_cancel(self, cr, uid, ids, context={}):
        """ Checks if move is cancelled or not.
        @return: True or False. 
        """
        res = True
        ok = False
        for procurement in self.browse(cr, uid, ids, context):
            if procurement.move_id:
                ok = True
                if not procurement.move_id.state == 'cancel':
                    res = False
        return res and ok

    def check_move_done(self, cr, uid, ids, context={}):
        """ Checks if move is done or not.
        @return: True or False. 
        """
        res = True
        for proc in self.browse(cr, uid, ids, context):
            if proc.move_id:
                if not proc.move_id.state == 'done':
                    res = False
        return res

    #
    # This method may be overrided by objects that override mrp.procurment
    # for computing their own purpose
    #
    def _quantity_compute_get(self, cr, uid, proc, context={}):
        """ Finds sold quantity of product.
        @param proc: Current procurement.
        @return: Quantity or False.
        """
        if proc.product_id.type == 'product':
            if proc.move_id.product_uos:
                return proc.move_id.product_uos_qty
        return False

    def _uom_compute_get(self, cr, uid, proc, context={}):
        """ Finds UoS if product is Stockable Product. 
        @param proc: Current procurement.
        @return: UoS or False.
        """
        if proc.product_id.type == 'product':
            if proc.move_id.product_uos:
                return proc.move_id.product_uos.id
        return False

    #
    # Return the quantity of product shipped/produced/served, wich may be
    # different from the planned quantity
    #
    def quantity_get(self, cr, uid, id, context={}):
        """ Finds quantity of product used in procurement.
        @return: Quantity of product. 
        """
        proc = self.browse(cr, uid, id, context)
        result = self._quantity_compute_get(cr, uid, proc, context)
        if not result:
            result = proc.product_qty
        return result

    def uom_get(self, cr, uid, id, context=None):
        """ Finds UoM of product used in procurement.
        @return: UoM of product. 
        """
        proc = self.browse(cr, uid, id, context)
        result = self._uom_compute_get(cr, uid, proc, context)
        if not result:
            result = proc.product_uom.id
        return result

    def check_waiting(self, cr, uid, ids, context=[]):
        """ Checks state of move.
        @return: True or False 
        """
        for procurement in self.browse(cr, uid, ids, context=context):
            if procurement.move_id and procurement.move_id.state == 'auto':
                return True
        return False

    def check_produce_service(self, cr, uid, procurement, context=[]):
        return True

    def check_produce_product(self, cr, uid, procurement, context=[]):
        """ Finds BoM of a product if not found writes exception message.
        @param procurement: Current procurement.
        @return: True or False.
        """
        properties = [x.id for x in procurement.property_ids]
        bom_id = self.pool.get('mrp.bom')._bom_find(cr, uid, procurement.product_id.id, procurement.product_uom.id, properties)
        if not bom_id:
            cr.execute('update mrp_procurement set message=%s where id=%s', (_('No BoM defined for this product !'), procurement.id))
            return False
        return True

    def check_make_to_stock(self, cr, uid, ids, context={}):
        """ Checks product type.
        @return: True or False 
        """
        ok = True
        for procurement in self.browse(cr, uid, ids, context=context):
            if procurement.product_id.type == 'service':
                ok = ok and self._check_make_to_stock_service(cr, uid, procurement, context)
            else:
                ok = ok and self._check_make_to_stock_product(cr, uid, procurement, context)
        return ok

    def check_produce(self, cr, uid, ids, context={}):
        """ Checks product type.
        @return: True or Product Id.
        """
        res = True
        user = self.pool.get('res.users').browse(cr, uid, uid)
        for procurement in self.browse(cr, uid, ids):
            if procurement.product_id.product_tmpl_id.supply_method <> 'produce':
                if procurement.product_id.seller_ids:
                    partner = procurement.product_id.seller_ids[0].name
                    if user.company_id and user.company_id.partner_id:
                        if partner.id == user.company_id.partner_id.id:
                            return True
                return False
            if procurement.product_id.product_tmpl_id.type=='service':
                res = res and self.check_produce_service(cr, uid, procurement, context)
            else:
                res = res and self.check_produce_product(cr, uid, procurement, context)
            if not res:
                return False
        return res

    def check_buy(self, cr, uid, ids):
        """ Checks product type.
        @return: True or Product Id.
        """
        user = self.pool.get('res.users').browse(cr, uid, uid)
        partner_obj = self.pool.get('res.partner')
        for procurement in self.browse(cr, uid, ids):
            if procurement.product_id.product_tmpl_id.supply_method <> 'buy':
                return False
            if not procurement.product_id.seller_ids:
                cr.execute('update mrp_procurement set message=%s where id=%s', (_('No supplier defined for this product !'), procurement.id))
                return False
            partner = procurement.product_id.seller_ids[0].name
            if user.company_id and user.company_id.partner_id:
                if partner.id == user.company_id.partner_id.id:
                    return False
            address_id = partner_obj.address_get(cr, uid, [partner.id], ['delivery'])['delivery']
            if not address_id:
                cr.execute('update mrp_procurement set message=%s where id=%s', (_('No address defined for the supplier'), procurement.id))
                return False
        return True

    def test_cancel(self, cr, uid, ids):
        """ Tests whether state of move is cancelled or not. 
        @return: True or False
        """
        for record in self.browse(cr, uid, ids):
            if record.move_id and record.move_id.state == 'cancel':
                return True
        return False

    def action_confirm(self, cr, uid, ids, context={}):
        """ Confirms procurement and writes exception message if any.
        @return: True
        """
        move_obj = self.pool.get('stock.move')
        for procurement in self.browse(cr, uid, ids):
            if procurement.product_qty <= 0.00:
                raise osv.except_osv(_('Data Insufficient !'), _('Please check the Quantity of Procurement Order(s), it should not be less than 1!'))
            if procurement.product_id.type in ('product', 'consu'):
                if not procurement.move_id:
                    source = procurement.location_id.id
                    if procurement.procure_method == 'make_to_order':
                        source = procurement.product_id.product_tmpl_id.property_stock_procurement.id
                    id = move_obj.create(cr, uid, {
                        'name': 'PROC:' + procurement.name,
                        'location_id': source,
                        'location_dest_id': procurement.location_id.id,
                        'product_id': procurement.product_id.id,
                        'product_qty': procurement.product_qty,
                        'product_uom': procurement.product_uom.id,
                        'date_planned': procurement.date_planned,
                        'state': 'confirmed',
                        'company_id': procurement.company_id.id,
                    })
                    self.write(cr, uid, [procurement.id], {'move_id': id, 'close_move': 1})
                else:
                    # TODO: check this
                    if procurement.procure_method == 'make_to_stock' and procurement.move_id.state in ('waiting',):
                        id = move_obj.write(cr, uid, [procurement.move_id.id], {'state':'confirmed'})
        self.write(cr, uid, ids, {'state': 'confirmed', 'message': ''})
        return True

    def action_move_assigned(self, cr, uid, ids, context={}):
        """ Changes procurement state to Running and writes message.
        @return: True 
        """
        self.write(cr, uid, ids, {'state': 'running', 'message': _('from stock: products assigned.')})
        return True

    def _check_make_to_stock_service(self, cr, uid, procurement, context={}):
        return True

    def _check_make_to_stock_product(self, cr, uid, procurement, context={}):
        """ Checks procurement move state.
        @param procurement: Current procurement.
        @return: True or move id.
        """
        ok = True
        if procurement.move_id:
            id = procurement.move_id.id
            if not (procurement.move_id.state in ('done','assigned','cancel')):
                ok = ok and self.pool.get('stock.move').action_assign(cr, uid, [id])
                cr.execute('select count(id) from stock_warehouse_orderpoint where product_id=%s', (procurement.product_id.id,))
                if not cr.fetchone()[0]:
                    cr.execute('update mrp_procurement set message=%s where id=%s', (_('from stock and no minimum orderpoint rule defined'), procurement.id))
        return ok

    def action_produce_assign_service(self, cr, uid, ids, context={}):
        """ Changes procurement state to Running.
        @return: True 
        """
        for procurement in self.browse(cr, uid, ids):
            self.write(cr, uid, [procurement.id], {'state': 'running'})
        return True

    def action_produce_assign_product(self, cr, uid, ids, context={}):
        """ This is action which call from workflow to assign production order to procurements
        @return: True
        """
        res = self.make_mo(cr, uid, ids, context=context)
        res = res.values()
        return len(res) and res[0] or 0 #TO CHECK: why workflow is generated error if return not integer value

    def make_mo(self, cr, uid, ids, context={}):
        """ Make Manufecturing(production) order from procurement
        @return: New created Production Orders procurement wise 
        """
        res = {}
        company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
        production_obj = self.pool.get('mrp.production')
        move_obj = self.pool.get('stock.move')
        wf_service = netsvc.LocalService("workflow")
        for procurement in self.browse(cr, uid, ids):
            res_id = procurement.move_id.id
            loc_id = procurement.location_id.id
            newdate = DateTime.strptime(procurement.date_planned, '%Y-%m-%d %H:%M:%S') - DateTime.RelativeDateTime(days=procurement.product_id.product_tmpl_id.produce_delay or 0.0)
            newdate = newdate - DateTime.RelativeDateTime(days=company.manufacturing_lead)
            produce_id = production_obj.create(cr, uid, {
                'origin': procurement.origin,
                'product_id': procurement.product_id.id,
                'product_qty': procurement.product_qty,
                'product_uom': procurement.product_uom.id,
                'product_uos_qty': procurement.product_uos and procurement.product_uos_qty or False,
                'product_uos': procurement.product_uos and procurement.product_uos.id or False,
                'location_src_id': procurement.location_id.id,
                'location_dest_id': procurement.location_id.id,
                'bom_id': procurement.bom_id and procurement.bom_id.id or False,
                'date_planned': newdate.strftime('%Y-%m-%d %H:%M:%S'),
                'move_prod_id': res_id,
                'company_id': procurement.company_id.id,
            })
            res[procurement.id] = produce_id
            self.write(cr, uid, [procurement.id], {'state': 'running'})
            bom_result = production_obj.action_compute(cr, uid,
                    [produce_id], properties=[x.id for x in procurement.property_ids])
            wf_service.trg_validate(uid, 'mrp.production', produce_id, 'button_confirm', cr)
            move_obj.write(cr, uid, [res_id],
                    {'location_id': procurement.location_id.id})
        return res
    
    def action_po_assign(self, cr, uid, ids, context={}):
        """ This is action which call from workflow to assign purchase order to procuments
        @return: True
        """
        res = self.make_po(cr, uid, ids, context=context)
        res = res.values()
        return len(res) and res[0] or 0 #TO CHECK: why workflow is generated error if return not integer value

    def make_po(self, cr, uid, ids, context={}):
        """ Make purchase order from procurement
        @return: New created Purchase Orders procurement wise
        """
        res = {}
        company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
        partner_obj = self.pool.get('res.partner')
        uom_obj = self.pool.get('product.uom')
        pricelist_obj = self.pool.get('product.pricelist')
        prod_obj = self.pool.get('product.product')
        acc_pos_obj = self.pool.get('account.fiscal.position')
        po_obj = self.pool.get('purchase.order')
        for procurement in self.browse(cr, uid, ids):
            res_id = procurement.move_id.id
            partner = procurement.product_id.seller_ids[0].name
            partner_id = partner.id
            address_id = partner_obj.address_get(cr, uid, [partner_id], ['delivery'])['delivery']
            pricelist_id = partner.property_product_pricelist_purchase.id

            uom_id = procurement.product_id.uom_po_id.id

            qty = uom_obj._compute_qty(cr, uid, procurement.product_uom.id, procurement.product_qty, uom_id)
            if procurement.product_id.seller_ids[0].qty:
                qty = max(qty,procurement.product_id.seller_ids[0].qty)

            price = pricelist_obj.price_get(cr, uid, [pricelist_id], procurement.product_id.id, qty, False, {'uom': uom_id})[pricelist_id]

            newdate = DateTime.strptime(procurement.date_planned, '%Y-%m-%d %H:%M:%S')
            newdate = newdate - DateTime.RelativeDateTime(days=company.po_lead)
            newdate = newdate - procurement.product_id.seller_ids[0].delay

            #Passing partner_id to context for purchase order line integrity of Line name
            context.update({'lang': partner.lang, 'partner_id': partner_id})

            product = prod_obj.browse(cr, uid, procurement.product_id.id, context=context)

            line = {
                'name': product.partner_ref,
                'product_qty': qty,
                'product_id': procurement.product_id.id,
                'product_uom': uom_id,
                'price_unit': price,
                'date_planned': newdate.strftime('%Y-%m-%d %H:%M:%S'),
                'move_dest_id': res_id,
                'notes': product.description_purchase,
            }

            taxes_ids = procurement.product_id.product_tmpl_id.supplier_taxes_id
            taxes = acc_pos_obj.map_tax(cr, uid, partner.property_account_position, taxes_ids)
            line.update({
                'taxes_id': [(6,0,taxes)]
            })
            purchase_id = po_obj.create(cr, uid, {
                'origin': procurement.origin,
                'partner_id': partner_id,
                'partner_address_id': address_id,
                'location_id': procurement.location_id.id,
                'pricelist_id': pricelist_id,
                'order_line': [(0,0,line)],
                'company_id': procurement.company_id.id,
                'fiscal_position': partner.property_account_position and partner.property_account_position.id or False
            })
            res[procurement.id] = purchase_id
            self.write(cr, uid, [procurement.id], {'state': 'running', 'purchase_id': purchase_id})
        return res

    def action_cancel(self, cr, uid, ids):
        """ Cancels procurement and writes move state to Assigned.
        @return: True 
        """
        todo = []
        todo2 = []
        move_obj = self.pool.get('stock.move')
        for proc in self.browse(cr, uid, ids):
            if proc.close_move:
                if proc.move_id.state not in ('done', 'cancel'):
                    todo2.append(proc.move_id.id)
            else:
                if proc.move_id and proc.move_id.state == 'waiting':
                    todo.append(proc.move_id.id)
        if len(todo2):
            move_obj.action_cancel(cr, uid, todo2)
        if len(todo):
            move_obj.write(cr, uid, todo, {'state': 'assigned'})
        self.write(cr, uid, ids, {'state': 'cancel'})
        wf_service = netsvc.LocalService("workflow")
        for id in ids:
            wf_service.trg_trigger(uid, 'mrp.procurement', id, cr)
        return True

    def action_check_finnished(self, cr, uid, ids):
        return self.check_move_done(cr, uid, ids)

    def action_check(self, cr, uid, ids):
        """ Checks procurement move state whether assigned or done. 
        @return: True 
        """
        ok = False
        for procurement in self.browse(cr, uid, ids):
            if procurement.move_id.state == 'assigned' or procurement.move_id.state == 'done':
                self.action_done(cr, uid, [procurement.id])
                ok = True
        return ok

    def action_ready(self, cr, uid, ids):
        """ Changes procurement state to Ready.
        @return: True 
        """
        res = self.write(cr, uid, ids, {'state': 'ready'})
        return res

    def action_done(self, cr, uid, ids):
        """ Changes procurement state to Done and writes Closed date.
        @return: True 
        """
        move_obj = self.pool.get('stock.move')
        for procurement in self.browse(cr, uid, ids):
            if procurement.move_id:
                if procurement.close_move and (procurement.move_id.state <> 'done'):
                    move_obj.action_done(cr, uid, [procurement.move_id.id])
        res = self.write(cr, uid, ids, {'state': 'done', 'date_close': time.strftime('%Y-%m-%d')})
        wf_service = netsvc.LocalService("workflow")
        for id in ids:
            wf_service.trg_trigger(uid, 'mrp.procurement', id, cr)
        return res

    def run_scheduler(self, cr, uid, automatic=False, use_new_cursor=False, context=None):
        ''' Runs through scheduler.
        @param use_new_cursor: False or the dbname
        '''
        if not context:
            context={}
        self._procure_confirm(cr, uid, use_new_cursor=use_new_cursor, context=context)
        self._procure_orderpoint_confirm(cr, uid, automatic=automatic,\
                use_new_cursor=use_new_cursor, context=context)
mrp_procurement()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

