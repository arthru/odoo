from itertools import chain
from osv import osv, fields
import time
import tools
import datetime


class fleet_vehicle_model_type(osv.Model):
    _name = 'fleet.vehicle.type'
    _description = 'Type of the vehicle'
    _columns = {
        'name' : fields.char('Name', size=32, required=True),
    }

class fleet_vehicle_tag(osv.Model):
    _name = 'fleet.vehicle.tag'
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
    }

class fleet_vehicle_state(osv.Model):
    _name = 'fleet.vehicle.state'
    _columns = {
        'name': fields.char('Name', required=True),
        'sequence': fields.integer('Order',help="Used to order the note stages")
    }
    _order = 'sequence asc'

class fleet_vehicle_model(osv.Model):

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not ids:
            return []
        reads = self.browse(cr, uid, ids, context=context)
        res = []
        for record in reads:
            name = record.modelname
            if record.brand.name:
                name = record.brand.name+' / '+name
            res.append((record.id, name))
        return res

    def _model_name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    def on_change_brand(self, cr, uid, ids, model_id, context=None):

        if not model_id:
            return {}

        brand = self.pool.get('fleet.vehicle.model.brand').browse(cr, uid, model_id, context=context)

        return {
            'value' : {
                'image' : brand.image,
            }
        }

    _name = 'fleet.vehicle.model'
    _description = 'Model of a vehicle'

    _columns = {
        'name' : fields.function(_model_name_get_fnc, type="char", string='Name', store=True),
        'modelname' : fields.char('Model name', size=32, required=True), 
        'brand' : fields.many2one('fleet.vehicle.model.brand', 'Model Brand', required=True, help='Brand of the vehicle'),
        'vendors': fields.many2many('res.partner','fleet_vehicle_model_vendors','model_id', 'partner_id',string='Vendors',required=False),
        'image': fields.related('brand','image',type="binary",string="Logo",store=False),
        'image_medium': fields.related('model_id','image_medium',type="binary",string="Logo",store=False),
        'image_small': fields.related('model_id','image_small',type="binary",string="Logo",store=False),
    }

class fleet_vehicle_model_brand(osv.Model):
    _name = 'fleet.vehicle.model.brand'
    _description = 'Brand model of the vehicle'

    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image)
        return result
    
    def _set_image(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'image': tools.image_resize_image_big(value)}, context=context)

    _columns = {
        'name' : fields.char('Brand Name',size=32, required=True),

        'image': fields.binary("Logo",
            help="This field holds the image used as logo for the brand, limited to 1024x1024px."),
        'image_medium': fields.function(_get_image, fnct_inv=_set_image,
            string="Medium-sized photo", type="binary", multi="_get_image",
            store = {
                'hr.employee': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Medium-sized logo of the brand. It is automatically "\
                 "resized as a 128x128px image, with aspect ratio preserved. "\
                 "Use this field in form views or some kanban views."),
        'image_small': fields.function(_get_image, fnct_inv=_set_image,
            string="Smal-sized photo", type="binary", multi="_get_image",
            store = {
                'hr.employee': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Small-sized photo of the brand. It is automatically "\
                 "resized as a 64x64px image, with aspect ratio preserved. "\
                 "Use this field anywhere a small image is required."),
    }

class fleet_vehicle(osv.Model):

    _inherit = 'mail.thread'

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not ids:
            return []
        reads = self.browse(cr, uid, ids, context=context)
        res = []
        for record in reads:
            if record.license_plate:
                name = record.license_plate
            if record.model_id.modelname:
                name = record.model_id.modelname + ' / ' + name
            if record.model_id.brand.name:
                name = record.model_id.brand.name+' / '+ name
            res.append((record.id, name))
        return res

    def _vehicle_name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    def act_show_log_services(self, cr, uid, ids, context=None):
        """ This opens log view to view and add new log for this vehicle
            @return: the service log view
        """
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid ,'fleet','act_show_log_services', context)
        res['context'] = {
            'default_vehicle_id': ids[0]
        }
        res['domain']=[('vehicle_id','=', ids[0])]
        return res

    def act_show_log_insurance(self, cr, uid, ids, context=None):
        """ This opens log view to view and add new log for this vehicle
            @return: the insurance log view
        """
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid ,'fleet','act_show_log_insurance', context)
        res['context'] = {
            'default_vehicle_id': ids[0]
        }
        res['domain']=[('vehicle_id','=', ids[0])]
        return res

    def act_show_log_fuel(self, cr, uid, ids, context=None):
        """ This opens log view to view and add new log for this vehicle
            @return: the fuel log view
        """
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid ,'fleet','act_show_log_fuel', context)
        res['context'] = {
            'default_vehicle_id': ids[0]
        }
        res['domain']=[('vehicle_id','=', ids[0])]
        return res    

    def get_odometer(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not ids:
            return []
        reads = self.browse(cr, uid, ids, context=context)
        res = []
        for record in reads:
            odometers = self.pool.get('fleet.vehicle.odometer').search(cr,uid,[('vehicle_id','=',record.id)], order='date desc')
            if len(odometers) > 0:
                res.append((record.id,self.pool.get('fleet.vehicle.odometer').browse(cr, uid, odometers[0], context=context).value))
            else :
                res.append((record.id,0))
        return res

    def _vehicle_odometer_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.get_odometer(cr, uid, ids, context=context)
        return dict(res)

    def str_to_date(self,strdate):
        return datetime.datetime(int(strdate[:4]),int(strdate[5:7]),int(strdate[8:]))

    def get_overdue_insurance_reminder(self,cr,uid,ids,prop,unknow_none,context=None):
        if context is None:
            context={}
        if not ids:
            return dict([])
        reads = self.browse(cr,uid,ids,context=context)
        res=[]
        for record in reads:
            insurances = self.pool.get('fleet.vehicle.log.insurance').search(cr,uid,[('vehicle_id','=',record.id),('state','=','In Progress')],order='expiration_date')
            overdue=0
            if (len(insurances) > 0):
                for element in insurances:
                    current_date_str=time.strftime('%Y-%m-%d')
                    due_time_str=self.pool.get('fleet.vehicle.log.insurance').browse(cr,uid,element,context=context).expiration_date
                    
                    current_date=self.str_to_date(current_date_str)
                    due_time=self.str_to_date(due_time_str)
     
                    diff_time=int((due_time-current_date).days)
                    if diff_time<0:
                        overdue = overdue +1;
                    else:
                        break
                res.append((record.id,overdue))
            else:
                res.append((record.id,0))
        return dict(res)

    def get_next_insurance_reminder(self,cr,uid,ids,prop,unknow_none,context=None):
        if context is None:
            context={}
        if not ids:
            return dict([])
        reads = self.browse(cr,uid,ids,context=context)
        res=[]
        for record in reads:
            insurances = self.pool.get('fleet.vehicle.log.insurance').search(cr,uid,[('vehicle_id','=',record.id),('state','=','In Progress')],order='expiration_date')
            due_soon=0
            if (len(insurances) > 0):
                for element in insurances:
                    current_date_str=time.strftime('%Y-%m-%d')
                    due_time_str=self.pool.get('fleet.vehicle.log.insurance').browse(cr,uid,element,context=context).expiration_date
                    
                    current_date=self.str_to_date(current_date_str)
                    due_time=self.str_to_date(due_time_str)
     
                    diff_time=int((due_time-current_date).days)
                    if diff_time<15 and diff_time>=0:
                        due_soon = due_soon +1;
                    if diff_time>15:
                        break
                res.append((record.id,due_soon))
            else:
                res.append((record.id,0))
        return dict(res)

    def get_next_service_reminder(self,cr,uid,ids,prop,unknow_none,context=None):
        if context is None:
            context={}
        if not ids:
            return dict([])
        reads = self.browse(cr,uid,ids,context=context)
        res=[]
        for record in reads:
            services = self.pool.get('fleet.vehicle.log.services').search(cr,uid,[('vehicle_id','=',record.id)],order='date')
            if (len(services) > 0):
                res.append((record.id,self.pool.get('fleet.vehicle.log.services').browse(cr,uid,services[0],context=context).date))
            else:
                res.append((record.id,None))
        return dict(res)

    _name = 'fleet.vehicle'
    _description = 'Fleet Vehicle'

    _columns = {
        'name' : fields.function(_vehicle_name_get_fnc, type="char", string='Name', store=True),
        'company_id': fields.many2one('res.company', 'Company'),
        'license_plate' : fields.char('License Plate', size=32, required=True, help='License plate number of the vehicle (ie: plate number for a car)'),
        'vin_sn' : fields.char('Chassis Number', size=32, required=False, help='Unique number written on the vehicle motor (VIN/SN number)'),
        'driver' : fields.many2one('res.partner', 'Driver',required=False, help='Driver of the vehicle', domain="['|',('customer','=',True),('employee','=',True)]"),
        'model_id' : fields.many2one('fleet.vehicle.model', 'Model', required=True, help='Model of the vehicle'),
        'log_ids' : fields.one2many('fleet.vehicle.log', 'vehicle_id', 'Other Logs'),
        'log_fuel' : fields.one2many('fleet.vehicle.log.fuel','vehicle_id', 'Fuel Logs'),
        'log_services' : fields.one2many('fleet.vehicle.log.services','vehicle_id', 'Services Logs'),
        'log_insurances' : fields.one2many('fleet.vehicle.log.insurance','vehicle_id', 'Insurances'),
        'acquisition_date' : fields.date('Acquisition Date', required=False, help='Date when the vehicle has been bought'),
        'acquisition_price' : fields.integer('Price', help='Price of the bought vehicle'),
        'color' : fields.char('Color',size=32, help='Color of the vehicle'),
        'state': fields.many2one('fleet.vehicle.state', 'State', help='Current state of the vehicle', ),
        'location' : fields.char('Location',size=32, help='Location of the vehicle (garage, ...)'),
        'doors' : fields.integer('Doors Number', help='Number of doors of the vehicle'),
        'tag_ids' :fields.many2many('fleet.vehicle.tag','vehicle_vehicle_tag_rel','vehicle_tag_id','tag_id','Tags'),

        'odometer' : fields.function(_vehicle_odometer_get_fnc, type="float", string='Odometer', store=False),
        'odometer_unit': fields.selection([('kilometers', 'Kilometers'),('miles','Miles')], 'Odometer Unit', help='Unit of the odometer ',required=False),

        'transmission' : fields.selection([('manual', 'Manual'),('automatic','Automatic')], 'Transmission', help='Transmission Used by the vehicle',required=False),
        'fuel_type' : fields.selection([('gasoline', 'Gasoline'),('diesel','Diesel'),('electric','Electric'),('hybrid','Hybrid')], 'Fuel Type', help='Fuel Used by the vehicle',required=False),
        'horsepower' : fields.integer('Horsepower',required=False),
        'horsepower_tax': fields.float('Horsepower Taxation'),
        'power' : fields.integer('Power (kW)',required=False,help='Power in kW of the vehicle'),
        'co2' : fields.float('CO2 Emissions',required=False,help='CO2 emissions of the vehicle'),

        'image': fields.related('model_id','image',type="binary",string="Logo",store=False),
        'image_medium': fields.related('model_id','image_medium',type="binary",string="Logo",store=False),
        'image_small': fields.related('model_id','image_small',type="binary",string="Logo",store=False),

        'insurance_renewal_due_soon' : fields.function(get_next_insurance_reminder,type="integer",string='Insurance Renewal Due Soon',store=False),
        'insurance_renewal_overdue' : fields.function(get_overdue_insurance_reminder,type="integer",string='Insurance Renewal Overdue',store=False),
        'next_service_date' : fields.function(get_next_service_reminder,type="date",string='Next Service Due Date',store=False),

        }

    _defaults = {
        'doors' : 5,
        'odometer_unit' : 'Kilometers',
    }



    def on_change_model(self, cr, uid, ids, model_id, context=None):

        if not model_id:
            return {}

        model = self.pool.get('fleet.vehicle.model').browse(cr, uid, model_id, context=context)

        return {
            'value' : {
                'image' : model.image,
            }
        }
    def create(self, cr, uid, data, context=None):
        vehicle_id = super(fleet_vehicle, self).create(cr, uid, data, context=context)
        try:
            vehicle = self.browse(cr, uid, vehicle_id, context=context)
            self.message_post(cr, uid, [vehicle_id], body='Vehicle %s has been added to the fleet!' % (vehicle.license_plate), context=context)
        except:
            pass # group deleted: do not push a message
        return vehicle_id

    def write(self, cr, uid, ids, vals, context=None):
        vehicle_id = super(fleet_vehicle,self).write(cr, uid, ids, vals, context)
        try:
            changes = []
            for key,value in vals.items():
                if key in ['license_plate','driver','state']:
                    if key == 'driver':
                        value = self.pool.get('res.partner').browse(cr,uid,value,context=context).name
                    if key == 'state':
                        value = self.pool.get('fleet.vehicle.state').browse(cr,uid,value,context=context).name
                    if key == 'driver':
                        key = 'Driver'
                    elif key == 'license_plate':
                        key = 'License Plate'
                    elif key =='state':
                        key = 'State'
                    changes.append(key + ' to \'' + value+'\'')
            if len(changes) > 0:
                self.message_post(cr, uid, [vehicle_id], body='Vehicle edited. Changes : '+ ", ".join(changes), context=context)
                #self.message_post(cr, uid, [vehicle_id], body='Vehicle edited. Changes : '+ ','.join(chain(*str(changes.items()))), context=context)
        except Exception as e:
            print e
            pass
        return vehicle_id

class fleet_vehicle_odometer(osv.Model):
    _name='fleet.vehicle.odometer'
    _description='Odometer log for a vehicle'

    _order='date desc'

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not ids:
            return []
        reads = self.browse(cr, uid, ids, context=context)
        res = []
        for record in reads:
            if record.vehicle_id.name:
                name = str(record.vehicle_id.name)
            if record.date:
                name = name+ ' / '+ str(record.date)
            res.append((record.id, name))
        return res

    def _vehicle_log_name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)
        
    _columns = {
        'name' : fields.function(_vehicle_log_name_get_fnc, type="char", string='Name', store=True),

        'date' : fields.date('Execution Date'),
        'value' : fields.float('Odometer Value',group_operator="max"),
        'unit': fields.related('vehicle_id','odometer_unit',type="char",string="Unit",store=False, readonly=True),
        'vehicle_id' : fields.many2one('fleet.vehicle', 'Vehicle', required=True),
        
    }
    _defaults = {
        'date' : time.strftime('%Y-%m-%d')
    }

class fleet_vehicle_log_fuel(osv.Model):

    _inherits = {'fleet.vehicle.odometer': 'odometer_id'}

    def on_change_liter(self, cr, uid, ids, liter, price_per_liter, amount, context=None):

        if liter > 0 and price_per_liter > 0:
            return {'value' : {'amount' : float(liter) * float(price_per_liter),}}
        elif liter > 0 and amount > 0:
            return {'value' : {'price_per_liter' : float(amount) / float(liter),}}
        elif price_per_liter > 0 and amount > 0:
            return {'value' : {'liter' : float(amount) / float(price_per_liter),}}
        else :
            return {}

    def on_change_price_per_liter(self, cr, uid, ids, liter, price_per_liter, amount, context=None):

        liter = float(liter);
        price_per_liter = float(price_per_liter);
        if price_per_liter > 0 and liter > 0:
            return {'value' : {'amount' : float(liter) * float(price_per_liter),}}
        elif price_per_liter > 0 and amount > 0:
            return {'value' : {'liter' : float(amount) / float(price_per_liter),}}
        elif liter > 0 and amount > 0:
            return {'value' : {'price_per_liter' : float(amount) / float(liter),}}
        else :
            return {}

    def on_change_amount(self, cr, uid, ids, liter, price_per_liter, amount, context=None):

        if amount > 0 and liter > 0:
            return {'value' : {'price_per_liter' : float(amount) / float(liter),}}
        elif amount > 0 and price_per_liter > 0:
            return {'value' : {'liter' : float(amount) / float(price_per_liter),}}
        elif liter > 0 and price_per_liter > 0:
            return {'value' : {'amount' : float(liter) * float(price_per_liter),}}
        else :
            return {}
        

    _name = 'fleet.vehicle.log.fuel'

    _columns = {
        #'name' : fields.char('Name',size=64),

        'liter' : fields.float('Liter'),
        'price_per_liter' : fields.float('Price Per Liter'),
        'amount': fields.float('Total price'),
        'purchaser_id' : fields.many2one('res.partner', 'Purchaser',domain="['|',('customer','=',True),('employee','=',True)]"),
        'inv_ref' : fields.char('Invoice Reference', size=64),
        'vendor_id' : fields.many2one('res.partner', 'Supplier', domain="[('supplier','=',True)]"),
        'notes' : fields.text('Notes'),
    }
    _defaults = {
        'purchaser_id': lambda self, cr, uid, ctx: uid,
    }

class fleet_vehicle_log_services(osv.Model):

    _inherits = {'fleet.vehicle.odometer': 'odometer_id'}    

    _name = 'fleet.vehicle.log.services'
    _columns = {

        #'name' : fields.char('Name',size=64),
        'date' :fields.date('Service Date',help='Date when the service will be/has been performed'),
        'amount' :fields.float('Cost', help="Total cost of the service"),
        'service_ids' :fields.many2many('fleet.service.type','vehicle_service_type_rel','vehicle_service_type_id','service_id','Services completed'),
        'purchaser_id' : fields.many2one('res.partner', 'Purchaser',domain="['|',('customer','=',True),('employee','=',True)]"),
        'inv_ref' : fields.char('Invoice Reference', size=64),
        'vendor_id' :fields.many2one('res.partner', 'Supplier', domain="[('supplier','=',True)]"),
        'notes' : fields.text('Notes'),
    }
    _defaults = {
        'purchaser_id': lambda self, cr, uid, ctx: uid,
        'date' : time.strftime('%Y-%m-%d'),
    }

class fleet_insurance_type(osv.Model):
    _name = 'fleet.insurance.type'
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
    }

class fleet_insurance_state(osv.Model):
    _name = 'fleet.insurance.state'
    _columns = {
        'name':fields.char('Insurance Status',size=32),
    }

class fleet_vehicle_log_insurance(osv.Model):
    _inherits = {'fleet.vehicle.odometer': 'odometer_id'}

    def compute_next_year_date(self, strdate):
        nextyear=int(strdate[:4])+1
        return str(nextyear)+strdate[4:]

    def on_change_start_date(self, cr, uid, ids, strdate, context=None):
        if (strdate):
           
            return {'value' : {'expiration_date' : self.compute_next_year_date(strdate),}}
        else:
            return {}

    _name = 'fleet.vehicle.log.insurance'
    _order='expiration_date'
    _columns = {

        #'name' : fields.char('Name',size=64),

        'insurance_type' : fields.many2one('fleet.insurance.type', 'Type', required=False, help='Type of the insurance'),
        'start_date' : fields.date('Start Date', required=False, help='Date when the coverage of the insurance begins'),
        'expiration_date' : fields.date('Expiration Date', required=False, help='Date when the coverage of the insurance expirates (by default, one year after begin date)'),
        'price' : fields.float('Price', help="Cost of the insurance for the specified period"),
        'insurer_id' :fields.many2one('res.partner', 'Insurer', domain="[('supplier','=',True)]"),
        'purchaser_id' : fields.many2one('res.partner', 'Purchaser',domain="['|',('customer','=',True),('employee','=',True)]"),
        'ins_ref' : fields.char('Insurance Reference', size=64),
        'state' : fields.many2one('fleet.insurance.state', 'Insurance Status', help='Choose wheter the insurance is still valid or not'),
        'notes' : fields.text('Terms and Conditions'),
    }
    _defaults = {
        'purchaser_id': lambda self, cr, uid, ctx: uid,
        'start_date' : time.strftime('%Y-%m-%d'),
        #'state' : 'in_progress',
        #'expiration_date' : self.compute_next_year_date(time.strftime('%Y-%m-%d')),
    
    }

class fleet_service_type(osv.Model):
    _name = 'fleet.service.type'
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
    }