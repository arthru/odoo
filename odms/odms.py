

from osv import fields, osv

from mx import DateTime
import time
import xmlrpclib
import threading
#import odmslib
import pooler

import tools
import re


def odms_send(cr, uid, ids, server_id, request, args={}, context={}):

	class odms_request(threading.Thread):
		"""Manage request to ODMS servers"""
		def __init__(self, srv, request, args={}):
			threading.Thread.__init__(self)
			# Get ODMS Server socket
			self.srv_socket = "http://"+srv.ipaddress+":"+srv.port
			print "DEBUG thread :",self.srv_socket
			self.srv = srv
			self.request = request
			self.args = args
			print "DEBUG odms_request - module_names :",args['module_names']

		def run(self):
			print "DEBUG sending request at :",self.srv_socket
			s = xmlrpclib.Server(self.srv_socket)

			# Execute request
			if request == 'debug':
				print "ODMS Debug - vserver socket :",self.srv_socket
				print "ODMS Debug - s :",s
			elif request == 'create_vsv':
				res = s.create_vsv(self.srv.user,self.srv.password,self.args['subs_id'],self.args['module_names'])
				print "ODMS Debug - vs_create :",res	
			elif request == 'create_web':
				res = s.create_web(self.srv.user,self.srv.password,self.args['subs_id'],self.args['url'])
				print "ODMS Debug - web_create :",res
			elif request == 'create_bck':
				res = s.create_bck(srv.user,srv.password,args['subs_id'])
				print "ODMS Debug - bck_create :",res
			else:
				raise osv.except_osv('Error !','Request:',request,' unknow')

	subs_lst = pooler.get_pool(cr.dbname).get('odms.subscription').browse(cr, uid, ids, context)

	nbr_thread=0

	# For each subscription
	for subs in subs_lst:
		# Get server object
		srv_obj = pooler.get_pool(cr.dbname).get('odms.server')
		print "DEBUG - server obj",srv_obj
		srv = srv_obj.browse(cr, uid, [server_id])[0]
		print "DEBUG srv :",srv

		# Execute request
		rqst = odms_request(srv, request, args)
		rqst.start()

		nbr_thread+=1

	return nbr_thread


class odms_vserver(osv.osv):
	_name = "odms.vserver"
	_description = "ODMS Virtual Server"

	_columns = {
		'name': fields.char('Vserver ID', size=64, required=True),
		'ipaddress': fields.char('IP address', size=16, required=True),
		'state' : fields.selection([('notactive','Not active'),('error','Error'),('active','Active')],'State', readonly=True),
	}
	_defaults = {
		'state': lambda *a: 'notactive',
	}
odms_vserver()

class odms_server(osv.osv):
	_name = "odms.server"
	_description = "ODMS Server Configuration"

	def srv_connect(self, cr, uid, ids, context={}):
		
		self.write(cr, uid, ids, {'state':'connected'})
		return True	

	def srv_disconnect(self, cr, uid, ids, context={}):
		self.write(cr, uid, ids, {'state':'notconnected'})
		return True	

	_columns = {
		'name': fields.char('Server name', size=64,required=True),
		'ipaddress': fields.char('IP address', size=16, required=True),
		'port': fields.char('Port', size=5, required=True),
		'user': fields.char('User', size=64, required=True),
		'password': fields.char('User password', size=64, required=True, invisible=True),
		'has_web': fields.boolean('Web service'), 
		'has_vserv': fields.boolean('Vserver service'), 
		'has_bckup': fields.boolean('Backup service'), 
		'nbr_vserv': fields.integer('Number of Virtual Servers', readonly=True),
		'notes': fields.text('Notes'),
		'state' : fields.selection([('notconnected','Not connected'),('connected','connected')],'State', readonly=True),
	}
	_defaults = {
		'has_web': lambda *a: False,
		'has_vserv': lambda *a: False,
		'has_bckup': lambda *a: False,
		'state': lambda *a: 'notconnected',
	}
odms_server()


class odms_bundle(osv.osv):
	_name = "odms.bundle"
	_description = "ODMS bundle"
	_columns = {
		'name': fields.char('Name', size=64, required=True),
		'product_id': fields.many2one('product.product','Product', required=True),
		'price_type': fields.selection([('fixed','Fixed'),('byusers','By users')],'Price type', required=True),
		'module_ids': fields.one2many('odms.module', 'bundle_id', 'Modules'),
	}
	_defaults = {
		'price_type': lambda *a: 'byusers',
	}
odms_bundle()


class odms_module(osv.osv):
	_name = "odms.module"
	_description = "ODMS Module"
	_columns = {
		'name': fields.char('Name', size=64, required=True),
		'bundle_id': fields.many2one('odms.bundle', 'Bundle', required=True),
		'state' : fields.selection([('installed','Installed'),('notinstalled','Not installed')],'State'),
	}
	_defaults = {
		'state': lambda *a: 'notinstalled',
	}
odms_module()


class odms_offer(osv.osv):
	_name = "odms.offer"
	_description = "ODMS Offer"
	_columns = {
		'name': fields.char('Name', size=64, required=True),
		'description': fields.text('Description'),
		'bundle_ids': fields.many2many('odms.bundle', 'odms_offer_bundles_rel', 'offer', 'bundle', 'Bundles'),
		'active': fields.boolean('Active'),
		'section_id': fields.many2one('crm.case.section','Case Section'),
		'portal_id': fields.many2one('portal.portal','User Portal'),
		'email_subject_trial': fields.char('Subject Freetrial', size=64, translate=True),
		'email_subject_subscription': fields.char('Subject Subscription',size=64,  translate=True),
		'email_subject_close': fields.char('Subject Close', size=64, translate=True),
		'email_trial': fields.text('Email Freetrial', translate=True),
		'email_subscription': fields.text('Email Subscription', translate=True),
		'email_close': fields.text('Email Close', translate=True),
	}
	_defaults = {
		'active': lambda *a: True,
	}
odms_offer()


class odms_partner(osv.osv):
	_name = "odms.partner"
	_description = "ODMS Partner"

	def create_partner(self, cr, uid, ids, context={}):
		odpart = self.browse(cr, uid , ids)[0]
			
		# Create new partner
		partner_obj = self.pool.get('res.partner')		
	
		part_id = partner_obj.create(cr, uid,
				{'name':odpart.name, 'vat':odpart.vat, 'website':odpart.website,
					'comment':odpart.notes})

		# Create new partner address
		# TODO : Add country and state
		paddr_obj = self.pool.get('res.partner.address')		
		paddr_id = paddr_obj.create(cr, uid,
				{'partner_id':part_id, 'name':odpart.contactname, 'street':odpart.address,
					'zip':odpart.zip, 'city':odpart.city, 'email':odpart.email, 
						'phone': odpart.phone, 'type': 'contact'})

		# Add partner to subscription
		subs_obj = self.pool.get('odms.subscription')		
		subs_id = subs_obj.search(cr, uid, [('odpartner_id','=',odpart.id)])
		subs_obj.write(cr, uid, subs_id, {'partner_id':part_id})

		# Link partner
		self.write(cr, uid, ids, {'partner_id':part_id})

		# Change state
		self.write(cr, uid, ids, {'state':'created'})
		return True

	_columns = {
		'name': fields.char('Name', size=128, required=True),
		'partner_id': fields.many2one('res.partner', 'Partner'),
		'vat': fields.char('VAT', size=32),
		'contactname': fields.char('Contact name', size=64, required=True),
		'email': fields.char('Email', size=64, required=True),
		'address': fields.char('Address', size=128),
		'zip': fields.char('zip', size=24),
		'city': fields.char('city', size=128),
		'countrystate_id': fields.many2one('res.country.state','Country state'),
		'country_id': fields.many2one('res.country','Country'),
		'phone': fields.char('phone', size=64),
		'website': fields.char('Website', size=64),
		'notes': fields.text('Notes'),
		'state': fields.selection([('draft','Draft'),('created','Created')],'State',readonly=True),
	}
	_defaults = {
		'state': lambda *a: 'draft',
	}
odms_partner()

class odms_subscription(osv.osv):
	_name = "odms.subscription"
	_description = "On Demand Subscription"
	def create(self, cr, uid, vals, context=None):
		print "DEBUG vals :",vals

		# Create subscription
		res =  super(odms_subscription, self).create(cr, uid, vals,
				context=context)

		if 'offer_id' in vals:
			print "DEBUG subs offer :",vals['offer_id']
			subs = self.browse(cr, uid, [res])[0]
			print "DEBUG subs id :",subs.id
			print "DEBUG subs offer bundles :",subs.offer_id.bundle_ids
	
			bundles = []
			offer_bdl_list = []
			bundle_obj = self.pool.get('odms.bundle')
			subs_bundle_obj = self.pool.get('odms.subs_bundle')

			# Get all bundles
			bids = bundle_obj.search(cr, uid, [('id','!=',False)])
			bundle_list = bundle_obj.browse(cr, uid, bids)
			print "DEBUG bundle list :",bundle_list
		
			# Create offer bundle list
			for bdl in subs.offer_id.bundle_ids:
				offer_bdl_list.append(bdl.id)
			print "DEBUG subs offer bundle list :",offer_bdl_list

			# Create subs bundles
			for bdl in bundle_list:
				# if bundle in offer set as installed 
				subs_bid = subs_bundle_obj.create(cr, uid, {
					'subscription_id':subs.id,
					'bundle_id':bdl.id,
					'state': ( bdl.id in offer_bdl_list) and 'installed' or 'notinstalled'
				})
				bundles.append(subs_bid)

		return res

	def create_subs(self, cr, uid, ids, context={}):
		""" 
		s = xmlrpclib.Server('http://localhost:8000')
		print "DEBUG user : ",oduser
		print "DEBUG password : ",odpass

		o = self.browse(cr, uid, ids)
		offer = o[0].offer.id
		print "DEBUG offer : ",offer

		res = s.create_vs(oduser,odpass,offer)
		print "DEBUG res : ",res

		#if (res <= 10): 
		#return False

		"""
		self._test_open(cr, uid, ids, context)
		for sub in self.browse(cr, uid, ids, context=context):
			tools.email_send(sub.user_id.address_id.email, sub.email, sub.offer_id.email_subject_trial, self._email_process(sub, 'email_subscription'))
		self.write(cr, uid, ids, {'state':'active'})
		return True

	def _email_process(self, sub2, select='email_trial'):
		body = getattr(sub2.offer_id, select)
		rregex_replace = lambda matcha: eval(matcha.group(1), {'sub':sub2, 'time':time})
		return re.sub('\\[(.*)\\]', rregex_replace, body)

	def create_trial(self, cr, uid, ids, context=None):
		self._test_open(cr, uid, ids, context)
		for sub in self.browse(cr, uid, ids, context=context):
			if (not sub.user_id) or (not sub.user_id.address_id) or (not sub.user_id.address_id.email):
				raise osv.except_osv('Error !','No email defined for this user !')
			tools.email_send(sub.user_id.address_id.email, sub.email, sub.offer_id.email_subject_trial, self._email_process(sub))
			if not sub.deadline_date:
				self.write(cr, uid, [sub.id], {'deadline_date': DateTime.now() + DateTime.RelativeDateTime(months=1)})
			if sub.offer_id.section_id:
				self.pool.get('crm.case').create(cr, uid, {
					'name': sub.name,
					'section_id': sub.offer_id.section_id.id,
					'email_from': sub.email,
					'partner_id': sub.partner_id and sub.partner_id.id or False,
					'user_id': sub.user_id and sub.user_id.id or False,
					'ref':'odms.subscription,'+str(sub.id),
					'date_action_next': (DateTime.now() + DateTime.RelativeDateTime(days=2)).strftime('%Y-%m-%d')
				}, context=context)
		self.write(cr, uid, ids, {'state':'trial'})
		return True

	def suspend_subs(self, cr, uid, ids, context=None):

		return True

	def delete_subs(self, cr, uid, ids, context=None):

		return True

	def settodraft(self, cr, uid, ids, context=None):
		self.write(cr, uid, ids, {'state':'draft'})
		return True

	def startstop_vserv(self, cr, uid, ids, context=None):

		return True

	def create_vserv(self, cr, uid, ids, context=None):
		subs = self.browse(cr, uid, ids)[0]
		if not subs.vserv_server_id:
			raise osv.except_osv('Error !','There is no vserver server defined for this subscription')
		print "DEBUG create_vserv - server id", subs.vserv_server_id.id

		# Get modules to install
		bndl_ids = subs.bundle_ids
		
		module_names = []	
		for b in bndl_ids:
			if (b.state == 'installed'):
				module_ids = b.bundle_id.module_ids
				print "DEBUG create_vserv - module_ids",module_ids

				for m in module_ids:
					module_names.append(m.name)	
		print "DEBUG create_vserv - module_names",module_names
			
		self.write(cr, uid, subs.id, {'vserv_server_state':'installing'})
		res = odms_send(cr, uid, ids, subs.vserv_server_id.id, 'create_vsv',
			{'subs_id':subs.id,'module_names':module_names}) 
		return res

	def create_web(self, cr, uid, ids, context=None):
		subs = self.browse(cr, uid, ids)[0]
		if subs.url == False:
			raise osv.except_osv('Error !','There is no url defined for this subscription')
		if not subs.web_server_id:
			raise osv.except_osv('Error !','There is no web server defined for this subscription')
		if not subs.vserver_id:
			raise osv.except_osv('Error !','There is no vserver defined for this subscription')
		print "DEBUG web_server_id :", subs.web_server_id
		url = subs.url+'.od.openerp.com'
		print "DEBUG create_web - server id", subs.web_server_id.id
		self.write(cr, uid, subs.id, {'web_server_state':'installing'})
		res = odms_send(cr, uid, ids, subs.web_server_id.id, 'create_web',{'subs_id':subs.id,'url':url}) 
		return res

	def user_create(self, cr, uid, ids, context={}):
		user_ref = self.pool.get('res.users')
		for sub in self.browse(cr, uid, ids, context):
			if not sub.partner_id:
				raise osv.except_osv('Error !','No partner defined for this offer "%s" !' % (sub.offer_id.name,))
			if not sub.partner_id.address:
				raise osv.except_osv('Error !','No address defined for this partner !')
			if not sub.offer_id.portal_id:
				raise osv.except_osv('Error !','No portal defined for this offer "%s" !' % (sub.offer_id.name,))
			portal = sub.offer_id.portal_id
			user = user_ref.search(cr,uid,[('login',"=",sub.email)])
			if user:
				self.write(cr, uid, [sub.id], {'owner_id': user[0]})
				continue
			newuser_id = user_ref.create(cr,uid,{
				'name': sub.partner_id.name,
				'login': sub.email,
				'password': sub.password,
				'address_id': sub.partner_id.address[0].id,
				'action_id': portal.home_action_id and portal.home_action_id.id or portal.menu_action_id.id, 
				'menu_id': portal.menu_action_id.id, 
				'groups_id': [(4,portal.group_id)],
				'company_id': portal.company_id.id,
			})
			self.write(cr, uid, [sub.id], {'owner_id': newuser_id})
		return True

	def _test_open(self, cr, uid, ids, context={}):
		for sub in self.browse(cr, uid, ids, context):
			if not sub.partner_id:
				raise osv.except_osv('Error !','No partner defined for this suscription "%s" !' % (sub.name,))
			if not sub.owner_id:
				raise osv.except_osv('Error !','No portal user defined for this suscription "%s" !' % (sub.name,))
			if not sub.vserv_server_state=='installed':
				raise osv.except_osv('Error !','Vserver Server is not installed !')
			#if not sub.vserver_state=='installed':
			#	raise osv.except_osv('Error !','VServer is not installed !')
			if not sub.web_server_state=='installed':
				raise osv.except_osv('Error !','Web server is not installed !')
			if not sub.bckup_server_state=='installed':
				raise osv.except_osv('Error !','Backup Server is not installed !')
		return True

	def create_bckup(self, cr, uid, ids, context=None):
		subs = self.browse(cr, uid, ids)[0]
		if not subs.bckup_server_id:
			raise osv.except_osv('Error !','There is no backup server defined for this subscription')
		self.write(cr, uid, subs.id, {'bckup_server_state':'installing'})
		res = odms_send(cr, uid, ids, subs.bckup_server_id.id, 'create_bck',{'subs_id':subs.id}) 
		return res

	def create_partner(self, cr, uid, ids, context={}):
		print "DEBUG - accessing create_partner"
		# Get OD partner id
		subs = self.browse(cr, uid ,[ids])[0]
		print "DEBUG - subs browse",subs
		odpart_obj = self.pool.get('odms.partner')
		print "DEBUG - odpart_obj",odpart_obj
		print "DEBUG - subs id",subs.odpartner_id.id
		odpart = odpart_obj.browse(cr, uid, [subs.odpartner_id.id])[0]
		print "DEBUG - odpart :",odpart

		# Get OD pricelist id
		# TODO : Get get pricelist from ?
		plist_obj = self.pool.get('product.pricelist')
		plist_id = plist_obj.browse(cr, uid, [2])[0].id

		# Create new partner
		partner_obj = self.pool.get('res.partner')

		part_id = partner_obj.create(cr, uid,
				{'name':odpart.name, 'vat':odpart.vat, 'website':odpart.website,
					'comment':odpart.notes})

		# Create new partner address
		paddr_obj = self.pool.get('res.partner.address')
		paddr_id = paddr_obj.create(cr, uid,
				{'partner_id':part_id, 'name':odpart.contactname, 'street':odpart.address,
					'zip':odpart.zip, 'city':odpart.city, 'email':odpart.email, 
						'phone':odpart.phone, 'country_id':odpart.country_id.id, 
							'state_id':odpart.countrystate_id.id, 'type':'contact'})

		# Add partner to subscription
		self.write(cr, uid, subs.id, {'partner_id':part_id})

		# Link partner
		self.write(cr, uid, ids, {'partner_id':part_id})

		# Set pricelist
		self.write(cr, uid, ids, {'pricelist_id':plist_id})
		
		# Add partner and Change state
		odpart_obj.write(cr, uid, subs.odpartner_id.id, {'partner_id':part_id, 'state':'created'})

		return {'partner_id':part_id}


	def make_invoice(self, cr, uid, ids, context={}):
		"""Create a new invoice for a subscription"""
		# Get subscrition
		subs_obj = self.browse(cr, uid, ids)

		for subs in subs_obj:
			print "DEBUG - subs :",subs
			print "DEBUG - subs.partner_id :",subs.partner_id.id
			if not subs.partner_id:
				raise osv.except_osv('Error !',
							'There is no partner defined for this subscription')
			if not subs.pricelist_id:
				raise osv.except_osv('Error !',
							'There is no pricelist defined for this subscription')

			# Get invoice account and taxes
			a = subs.partner_id.property_account_receivable.id
			print "DEBUG - Account :", a
	
			# Get invoice lines
			bundles = subs.bundle_ids
			print "DEBUG - bundles :", bundles
			print "DEBUG - bundles  nbr :", len(bundles)
			lines = []
				
			# Build an invoice line for each bundle
			for b in bundles:
				if b.state == 'installed':
					# Get invoice line account
					al =  b.bundle_id.product_id.product_tmpl_id.property_account_income.id
					if not al: 
						al = b.bundle_id.product_id.categ_id.property_account_income_categ.id
					if not al: 
						raise osv.except_osv('Error !',
							'There is no income account defined for this product: "%s" (id:%d)'% (b.bundle_id.product_id.name, b.bundle_id.product_id.id))
					print "DEBUG - Line Account :", al
	
					# Get quantity
					if b.bundle_id.price_type == 'fixed':
						qty = 1
					else:
						qty = subs.max_users
					print "DEBUG - qty :", qty
		
					# get price_unit
					pu = self.pool.get('product.pricelist').price_get(cr, uid, [subs.pricelist_id.id],
						b.bundle_id.product_id.id, qty or 1.0, subs.partner_id)[subs.pricelist_id.id]
					print "DEBUG - pu :",pu
	
					# get taxes
					taxes = b.bundle_id.product_id.taxes_id
					print "DEBUG - Taxes :", taxes
					for t in taxes:
						print "DEBUG - Tax :", t.name
					# Create invoice lines	
					inv_line_id = self.pool.get('account.invoice.line').create(cr, uid, {
						'name': b.bundle_id.name,
						'account_id': al,
						'price_unit': pu,
						'quantity': qty,
						'uos_id': 1,
						'product_id': b.bundle_id.product_id.id,
						'invoice_line_tax_id': [(6,0,[t.id for t in taxes])],
					})
					lines.append(inv_line_id)
	
			# Get payment term
			if subs.partner_id and subs.partner_id.property_payment_term.id:
				pay_term = subs.partner_id.property_payment_term.id
			else:
				pay_term = False
	
			# Get invoice address
			invoice_add_id = subs.partner_id.address_get(cr, uid, [subs.partner_id.id], ['invoice'])
			print "DEBUG - invoice_add_id :",  invoice_add_id
	
			# Get contact address
			contact_add_id = subs.partner_id.address_get(cr, uid, [subs.partner_id.id], ['contact'])
			print "DEBUG - contact_add_id :",  contact_add_id
	
			# Get user => get company => get currency
			user = self.pool.get('res.users').browse(cr, uid, [uid])
			print "DEBUG - user :", user[0]
			print "DEBUG - company :", user[0].company_id.id
			company = user[0].company_id
			currency = company.currency_id
			print "DEBUG - currency :",  currency.id
	
			# Set invoice
			inv = {
				'name': subs.name,
				'origin': subs.name,
				'type': 'out_invoice',
				'reference': "P%dSO%d"%(subs.partner_id.id,subs.id),
				'account_id': a,
				'partner_id': subs.partner_id.id,
				'address_invoice_id': invoice_add_id['invoice'],
				'address_contact_id': contact_add_id['contact'],
				'invoice_line': [(6,0,lines)],
				'currency_id' : currency.id,
				'comment': subs.notes,
				'payment_term': pay_term,
			}
			# Create invoice
			inv_obj = self.pool.get('account.invoice')
			inv_id = inv_obj.create(cr, uid, inv)
			inv_obj.button_compute(cr, uid, [inv_id])
	
		print "DEBUG - inv_id :", inv_id
		return inv_id


	def onchange_partner_id(self, cr, uid, ids, part):
		if not part:
			return {'value':{'pricelist':False}}		
		pricelist = self.pool.get('res.partner').browse(cr, uid, part).property_product_pricelist.id
		print "DEBUG - on_change on partner_id called"
		return {'value':{'pricelist_id': pricelist}}

	
	def _get_vserver_status(self, cr , uid, ids, prop, unknow_none, unknow_dict):
		subs = self.browse(cr, uid, ids)
		print "DEBUG - _get_vserver_status - subs",subs
		res = []
		for s in subs:
			if s.vserver_id:
				print "DEBUG - _get_vserver_status - s.id:",s.id
				vserver_state = self.pool.get('odms.vserver').browse(cr, uid, [s.vserver_id.id])[0]
				print "DEBUG - _get_vserver_status - vserver_state:",vserver_state.state
				res.append((s.id,vserver_state.state))
				print "DEBUG - _get_vserver_status - res:",res
			else:
				res.append((s.id,False))
		return dict(res)
	
	_columns = {
		'name' : fields.char('Subscription name', size=64, required=True),
		'user_id': fields.many2one('res.users', 'Responsible'),
		'owner_id': fields.many2one('res.users', 'Portal User'),
		'partner_id': fields.many2one('res.partner', 'Partner'),
		'odpartner_id': fields.many2one('odms.partner', 'ODMS Partner'),
		'email': fields.char('Login', size=64, required=True),
		'password': fields.char('Password', size=64, required=True),
		'url': fields.char('OD Website URL', size=64),
		'date' : fields.date('Subscription date', readonly=True),
		'activ_date' : fields.date('Activation date'),
		'deadline_date' : fields.date('Deadline date'),
		'nbr_users' : fields.integer('Number of users',readonly=True),
		'max_users' : fields.integer('Maximum users'),
		'offer_id' : fields.many2one('odms.offer', 'Offer', required=True),
		'pricelist_id':fields.many2one('product.pricelist', 'Pricelist', readonly=True, states={'draft':[('readonly',False)]}),
		'bundle_ids' : fields.one2many('odms.subs_bundle', 'subscription_id', 'Bundles'),
		'vserver_id': fields.many2one('odms.vserver', 'VServer ID', readonly=True),
		'vserver_state': fields.function(_get_vserver_status, method=True, type='char',  string='Vserver status'),
		'web_server_id': fields.many2one('odms.server', 'ODMS Web Server'),
		'web_server_state' : fields.selection([('error','Error'),('notinstalled','Not installed'),('installing','Installing'),('installed','Installed')],'Web server state', readonly=True),
		'vserv_server_id': fields.many2one('odms.server', 'ODMS VServer Server'),
		'vserv_server_state' : fields.selection([('error','Error'),('notinstalled','Not installed'),('installing','Installing'),('installed','Installed')],'VServer server state', readonly=True),
		'bckup_server_id': fields.many2one('odms.server', 'ODMS Backup Server'),
		'bckup_server_state' : fields.selection([('error','Error'),('notinstalled','Not installed'),('installing','Installing'),('installed','Installed')],'Backup server state', readonly=True),
		'notes' : fields.text('Notes'),
		'state' : fields.selection([('draft','Draft'),('trial','Free trial'),('active','Active'),('suspended','Suspended'),('deleted','Deleted')],'State', readonly=True),
	}

	_defaults = {
		'date' : lambda *a: time.strftime('%Y-%m-%d'),
		'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'odms.subscription'),
		'state' : lambda *a: 'draft',
		'user_id' : lambda self,cr, uid,ctx: uid,
		'web_server_state' : lambda *a: 'notinstalled',
		'vserv_server_state' : lambda *a: 'notinstalled',
		'bckup_server_state' : lambda *a: 'notinstalled',
		'max_users' : lambda *a: 1,
	}
	_order = "date desc"
odms_subscription()


class odms_subs_bundle(osv.osv):
	_name = "odms.subs_bundle"
	_description = "ODMS Subscription bundle"

	def install_bundle(self, cr, uid, ids, context={}):
		# ...
		self.write(cr, uid, ids, {'state':'installed'})
		return True

	def uninstall_bundle(self, cr, uid, ids, context={}):
		# ...
		self.write(cr, uid, ids, {'state':'notinstalled'})
		return True

	_columns = {
		'subscription_id': fields.many2one('odms.subscription', 'Subscription', required=True),
		'bundle_id': fields.many2one('odms.bundle', 'Bundle', required=True),
		'state' : fields.selection([('installed','Installed'),('notinstalled','Not installed')],'State', readonly=True),
	}
	_defaults = {
		'state': lambda *a: 'notinstalled',
	}
	_rec_name = 'bundle_id'
odms_subs_bundle()

