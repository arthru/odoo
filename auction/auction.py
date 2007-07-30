##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be) All Rights Reserved.
#					Fabien Pinckaers <fp@tiny.Be>
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

import time
import netsvc
from osv import fields, osv, orm
import ir
from mx import DateTime

#----------------------------------------------------------
# Auction Artists
#----------------------------------------------------------
class auction_artists(osv.osv):
	_name = "auction.artists"
	_columns = {
		'name': fields.char('Artist/Author Name', size=64, required=True),
		'pseudo': fields.char('Pseudo', size=64),
		'birth_death_dates':fields.char('Birth / Death dates',size=64),
		'biography': fields.text('Biography'),
	}
auction_artists()

#----------------------------------------------------------
# Auction Dates
#----------------------------------------------------------
class auction_dates(osv.osv):
	_name = "auction.dates"

	def _adjudication_get(self, cr, uid, ids, prop, unknow_none,unknow_dict):
		tmp={}
		for id in ids:
			tmp[id]=0.0
			cr.execute("select sum(obj_price) from auction_lots where auction_id=%d", (id,))
			sum = cr.fetchone()
			if sum:
				tmp[id]=sum[0]
		return tmp

	def name_get(self, cr, uid, ids, context={}):
		if not len(ids):
			return []
		reads = self.read(cr, uid, ids, ['name', 'auction1'], context)
		name = [(r['id'],'['+r['auction1']+'] '+ r['name']) for r in reads]
		return name

	_columns = {
		'name': fields.char('Auction date', size=64, required=True),
		'expo1': fields.date('First Exposition Day', required=True),
		'expo2': fields.date('Last Exposition Day', required=True),
		'auction1': fields.date('First Auction Day', required=True),
		'auction2': fields.date('Last Auction Day', required=True),
		'journal_id': fields.many2one('account.journal', 'Buyer Journal', required=True),
		'journal_seller_id': fields.many2one('account.journal', 'Seller Journal', required=True),
		'buyer_costs': fields.many2many('account.tax', 'auction_buyer_taxes_rel', 'auction_id', 'tax_id', 'Buyer Costs'),
		'seller_costs': fields.many2many('account.tax', 'auction_seller_taxes_rel', 'auction_id', 'tax_id', 'Seller Costs'),
		'acc_income': fields.many2one('account.account', 'Income Account', required=True),
		'acc_expense': fields.many2one('account.account', 'Expense Account', required=True),
		#'acc_refund': fields.many2one('account.account', 'Refund Account', required=True),
		'adj_total': fields.function(_adjudication_get, method=True, string='Total Adjudication',store=True),
		'journal_id': fields.many2one('account.journal', 'Journal', required=True),
		'state': fields.selection((('draft','Draft'),('sold','Closed')),'State',required=True, select=1, readonly=True),
		#'state': fields.selection((('draft','Draft'),('close','Closed')),'State', readonly=True),
		'account_analytic_id': fields.many2one('account.analytic.account', 'Analytic Account', required=True),

	}
	_defaults = {
		'state': lambda *a: 'draft',
	}
	_order = "auction1 desc"

	def close(self, cr, uid, ids, *args):
		"""
		Close an auction date.

		Create invoices for all buyers and sellers.
		STATE = unsold instead of 'close'

		RETURN: True
		"""
		cr.execute('select count(*) as c from auction_lots where auction_id in ('+','.join(map(str,ids))+') and state=%s and obj_price>0 and ach_uid is null and obj_price is not null', ('draft',))
		nbr = cr.fetchone()[0]
		if nbr>0:
			cr.execute('select * from auction_lots where auction_id in ('+','.join(map(str,ids))+') and state=%s and obj_price>0 and ach_uid is null and obj_price is not null', ('draft',))
			raise orm.except_orm('UserError', ('Please assign all buyer before closing the auction !', 'init'))
		ach_uids = {}
		cr.execute('select ach_uid,id from auction_lots where auction_id in ('+','.join(map(str,ids))+') and state=%s and obj_price>0', ('draft',))
		for arg in cr.fetchall():
			if arg[0] not in ach_uids:
				ach_uids[arg[0]]=[]
			ach_uids[arg[0]].append(arg[1])
		for arg in ach_uids:
			self.pool.get('auction.lots').lots_invoice(cr, uid, ach_uids[arg], arg)
		cr.execute('update auction_lots set obj_price=0.0 where obj_price is null and auction_id in ('+','.join(map(str,ids))+')')
		cr.execute('update auction_lots set state=%s where state=%s and auction_id in ('+','.join(map(str,ids))+')', ('draft','unsold'))
		cr.execute('select * from auction_lots where auction_id in ('+','.join(map(str,ids))+') and obj_price>0')
		ids2 = [x[0] for x in cr.fetchall()]
		self.pool.get('auction.lots').seller_trans_create(cr, uid, ids2)
		self.write(cr, uid, ids, {'state':'unsold'})
		return True
auction_dates()


#----------------------------------------------------------
# Deposits
#----------------------------------------------------------
def _inv_uniq(cr, ids):
	cr.execute('select name from auction_deposit where id in ('+','.join(map(lambda x: str(x), ids))+')')
	for datas in cr.fetchall():
		cr.execute('select count(*) from auction_deposit where name=%s', (datas[0],))
		if cr.fetchone()[0]>1:
			return False
	return True

class auction_deposit(osv.osv):
	_name = "auction.deposit"
	_description="Deposit Border"
	_order = "id desc"
	_columns = {
		'name': fields.char('Depositer Inventory', size=64, required=True),
		'partner_id': fields.many2one('res.partner', 'Seller', required=True, change_default=True),
		'date_dep': fields.date('Deposit date', required=True),
		'method': fields.selection((('keep','Keep until sold'),('decease','Decrease limit of 10%'),('contact','Contact the Seller')), 'Withdrawned method', required=True),
		'tax_id': fields.many2one('account.tax', 'Expenses'),
		'create_uid': fields.many2one('res.users', 'Created by', readonly=True),
		'info': fields.char('Description', size=64),
		'lot_id': fields.one2many('auction.lots', 'bord_vnd_id', 'Objects'),
		'specific_cost_ids': fields.one2many('auction.deposit.cost', 'deposit_id', 'Specific Costs'),
		'total_neg': fields.boolean('Allow Negative Amount'),
	}
	_defaults = {
		'date_dep': lambda *a: time.strftime('%Y-%m-%d'),
		'method': lambda *a: 'keep',
		'total_neg': lambda *a: False,
		'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'auction.deposit'),
	}
	_constraints = [
	#	(_inv_uniq, 'Twice the same inventory number !', ['name'])
	]
	def partner_id_change(self, cr, uid, ids, part):
		return {}
auction_deposit()

#----------------------------------------------------------
# (Specific) Deposit Costs
#----------------------------------------------------------
class auction_deposit_cost(osv.osv):
	_name = 'auction.deposit.cost'
	_columns = {
		'name': fields.char('Cost Name', required=True, size=64),
		'amount': fields.float('Amount'),
		'account': fields.many2one('account.account', 'Destination Account', required=True),
		'deposit_id': fields.many2one('auction.deposit', 'Deposit'),
	}
auction_deposit_cost()

#----------------------------------------------------------
# Lots Categories
#----------------------------------------------------------
class auction_lot_category(osv.osv):
	_name = 'auction.lot.category'
	_columns = {
		'name': fields.char('Category Name', required=True, size=64),
		'priority': fields.float('Priority'),
		'active' : fields.boolean('Active'),
		'aie_categ' : fields.selection([('41',"Unclassifieds"),
			('2',"Antiques"),
			('42',"Antique/African Arts"),
			('59',"Antique/Argenterie"),
			('45',"Antique/Art from the Ivory Coast"),
			('46',"Antique/Art from the Ivory Coast/African Arts"),
			('12',"Antique/Books, manuscripts, eso."),
			('11',"Antique/Carpet and textilles"),
			('14',"Antique/Cartoons"),
			('26',"Antique/Clocks and watches"),
			('31',"Antique/Collectible & art objects"),
			('33',"Antique/Engravings"),
			('10',"Antique/Furnitures"),
			('50',"Antique/Graphic Arts"),
			('37',"Antique/Jewelry"),
			('9',"Antique/Lightings"),
			('52',"Antique/Metal Ware"),
			('51',"Antique/Miniatures / Collections"),
			('53',"Antique/Musical Instruments"),
			('19',"Antique/Old weapons and militaria"),
			('43',"Antique/Oriental Arts"),
			('47',"Antique/Oriental Arts/Chineese furnitures"),
			('24',"Antique/Others"),
			('8',"Antique/Painting"),
			('25',"Antique/Porcelain, Ceramics, Glassmaking, ..."),
			('13',"Antique/Posters"),
			('56',"Antique/Religiosa"),
			('54',"Antique/Scientific Instruments"),
			('18',"Antique/Sculpture, bronze, eso."),
			('55',"Antique/Tin / Copper wares"),
			('16',"Antique/Toys"),
			('57',"Antique/Verreries"),
			('17',"Antique/Wine"),
			('1',"Contemporary Art"),
			('58',"Cont. Art/Arts"),
			('27',"Cont. Art/Curiosa"),
			('15',"Cont. Art/Jewelry"),
			('30',"Cont. Art/Other Media"),
			('3',"Cont. Art/Photo"),
			('4',"Cont. Art/Painting"),
			('5',"Cont. Art/Sculpture"),
			('48',"Cont. Art/Shows")],
			'Aie Category'),
	}
	_defaults = {
		'active' : lambda *a: 1,
		'aie_categ' : lambda *a:1,
	}
auction_lot_category()

def _type_get(self, cr, uid,ids):
	cr.execute('select name, name from auction_lot_category order by name')
	return cr.fetchall()

#----------------------------------------------------------
# Lots
#----------------------------------------------------------
def _inv_constraint(cr, ids):
	cr.execute('select id, bord_vnd_id, lot_num from auction_lots where id in ('+','.join(map(lambda x: str(x), ids))+')')
	for datas in cr.fetchall():
		cr.execute('select count(*) from auction_lots where bord_vnd_id=%s and lot_num=%s', (datas[1],datas[2]))
		if cr.fetchone()[0]>1:
			return False
	return True

class auction_lots(osv.osv):
	_name = "auction.lots"
	_order = "obj_num,lot_num"
	_description="Object"

	def button_not_bought(self,cr,uid,ids,*a):
		return self.write(cr,uid,ids, {'state':'unsold'})

	def button_draft(self,cr,uid,ids,*a):
		return self.write(cr,uid,ids, {'state':'draft'})

	def button_bought(self,cr,uid,ids,*a):
		return self.write(cr,uid,ids, {'state':'sold'})

	def _buyerprice(self, cr, uid, ids, name, args, context):
		res={}
		lots=self.pool.get('auction.lots').browse(cr,uid,ids)
		pt_tax=self.pool.get('account.tax')
		for lot in lots:
			amount_total=0.0
			if ((lot.obj_price==0) and (lot.state=='draft')):
				montant=lot.lot_est1
			else:
				montant=lot.obj_price
			taxes = []
			if lot.author_right:
				taxes.append(lot.author_right)
			if lot.auction_id:
				taxes += lot.auction_id.buyer_costs
			tax=pt_tax.compute(cr,uid,taxes,montant,1)
			for t in tax:
				amount_total+=t['amount']
			amount_total += montant
			res[lot.id] = amount_total
		return res


	def _sellerprice(self, cr, uid, ids,*a):
		res={}
		lots=self.pool.get('auction.lots').browse(cr,uid,ids)
		pt_tax=self.pool.get('account.tax')
		for lot in lots:
			amount_total=0.0
			if ((lot.obj_price==0) and (lot.state=='draft')):
				montant=lot.lot_est1
			else:
				montant=lot.obj_price
			taxes = []
			if lot.bord_vnd_id.tax_id:
				taxes.append(lot.bord_vnd_id.tax_id)
			elif lot.auction_id and lot.auction_id.seller_costs:
				taxes += lot.auction_id.seller_costs
			tax=pt_tax.compute(cr,uid,taxes,montant,1)
			for t in tax:
				amount_total+=t['amount']
			res[lot.id] =  montant+amount_total
		return res

	def _grossprice(self, cr, uid, ids, name, args, context):
		"""gross revenue"""
		res={}
		auction_lots_obj = self.read(cr,uid,ids,['seller_price','buyer_price','auction_id'])
		for auction_data in auction_lots_obj:
			total_tax = 0.0
			if auction_data['auction_id']:
				total_tax += auction_data['buyer_price']-auction_data['seller_price']
			res[auction_data['id']] = total_tax
		return res


	def _grossmargin(self, cr, uid, ids, name, args, context):
		"""
		gross Margin : Gross revenue * 100 / Adjudication
		(state==unsold or obj_ret_price>0): adj_price = 0 (=> gross margin = 0, net margin is negative)
		"""

		res={}
		total=0.0
		montant=0.0
		auction_lots_obj = self.read(cr,uid,ids,['gross_revenue','auction_id','lot_est1','obj_price','state','obj_ret'])
		for auction_data in auction_lots_obj:
			if (auction_data['state']=='unsold') or (auction_data['obj_ret']>0): #pbleme avec le write=> boucle infinie
				res[auction_data['id']]=0
				montant=0.0
			elif ((auction_data ['obj_price']==0) and (auction_data['state']=='draft')):
				montant=auction_data['lot_est1']
			else: montant=auction_data['obj_price']
			if montant >0:
				total+=(auction_data['gross_revenue']*100)/montant
			else: total=0
			res[auction_data['id']]=total
		return res

	def onchange_obj_ret(self, cr, uid, ids, obj_ret, *args):
		if obj_ret:
			return {'value': {'obj_price': 0}}
		return {}

	def _costs(self,cr,uid,ids,context,*a):
		"""
		costs: Total credit of analytic account
		/ # objects sold during this auction
		(excluding analytic lines that are in the analytic journal of the auction date).
		"""
		res={}
		som=0.0

		for lot in self.browse(cr,uid,ids):
			if not lot.auction_id:
				res[lot.id] = 0.0
				continue
			auct_id=lot.auction_id.id
			cr.execute('select count(*) from auction_lots where auction_id=%d', (auct_id,))
			nb = cr.fetchone()[0]
			account_analytic_line_obj = self.pool.get('account.analytic.line')
			line_ids = account_analytic_line_obj.search(cr, uid, [('account_id', '=', lot.auction_id.account_analytic_id.id),('journal_id', '<>', lot.auction_id.journal_id.id)])
			for line in account_analytic_line_obj.browse(cr,uid,line_ids):
				if line.amount:
					som-=line.amount
			res[lot.id]=som/nb
		return res

	def _netprice(self, cr, uid, ids, name, args, context):
		"""This is the net revenue"""
		res={}
		auction_lots_obj = self.read(cr,uid,ids,['seller_price','buyer_price','auction_id','costs'])
		for auction_data in auction_lots_obj:
			total_tax = 0.0
			if auction_data['auction_id']:
				total_tax += auction_data['buyer_price']-auction_data['seller_price']-auction_data['costs']
			res[auction_data['id']] = total_tax
		return res

	def _netmargin(self, cr, uid, ids, name, args, context):
		res={}
		total_tax = 0.0
		total=0.0
		montant=0.0
		auction_lots_obj = self.read(cr,uid,ids,['net_revenue','auction_id','lot_est1','obj_price','state'])
		for auction_data in auction_lots_obj:
			if ((auction_data ['obj_price']==0) and (auction_data['state']=='draft')):
				montant=auction_data['lot_est1']
			else: montant=auction_data ['obj_price']
			if montant>0:
				total_tax += (auction_data['net_revenue']*100)/montant
			else:
				total_tax=0
			res[auction_data['id']] =  total_tax
		return res

	def _is_paid_vnd(self,cr,uid,ids,*a):
		res = {}
		lots=self.browse(cr,uid,ids)
		for lot in lots:
			res[lot.id] = False
			if lot.sel_inv_id:
				if lot.sel_inv_id.state == 'paid':
					res[lot.id] = True
		return res
	def _is_paid_ach(self,cr,uid,ids,*a):
		res = {}
		lots=self.browse(cr,uid,ids)
		for lot in lots:
			res[lot.id] = False
			if lot.ach_inv_id:
				if lot.ach_inv_id.state == 'paid':
					res[lot.id] = True
		return res
	_columns = {
		'bid_lines':fields.one2many('auction.bid_line','lot_id', 'Bids'),
		'auction_id': fields.many2one('auction.dates', 'Auction Date'),
		'bord_vnd_id': fields.many2one('auction.deposit', 'Depositer Inventory', required=True),
		'name': fields.char('Short Description',size=64, required=True),
		'name2': fields.char('Short Description (2)',size=64),
		'lot_type': fields.selection(_type_get, 'Object category', size=64),
		'author_right': fields.many2one('account.tax', 'Author rights'),
		'lot_est1': fields.float('Minimum Estimation'),
		'lot_est2': fields.float('Maximum Estimation'),
		'lot_num': fields.integer('List Number', required=True, select=1 ),
		'create_uid': fields.many2one('res.users', 'Created by', readonly=True),
		'history_ids':fields.one2many('auction.lot.history', 'lot_id', 'Auction history'),
		'lot_local':fields.char('Location',size=64),
		'artist_id':fields.many2one('auction.artists', 'Artist/Author'),
		'artist2_id':fields.many2one('auction.artists', 'Artist/Author 2'),
		'important':fields.boolean('To be Emphatized'),
		'product_id':fields.many2one('product.product', 'Product', required=True),
		'obj_desc': fields.text('Object Description'),
		'obj_num': fields.integer('Catalog Number'),
		'obj_ret': fields.float('Price retired'),
		'obj_comm': fields.boolean('Commission'),
		'obj_price': fields.float('Adjudication price'),
		'ach_avance': fields.float('Buyer Advance'),
		'ach_login': fields.char('Buyer Username',size=64),
		'ach_uid': fields.many2one('res.partner', 'Buyer'),
		'ach_emp': fields.boolean('Taken Away'),
		'ach_inv_id': fields.many2one('account.invoice','Buyer Invoice', readonly=True, states={'draft':[('readonly',False)]}),
		'sel_inv_id': fields.many2one('account.invoice','Seller Invoice', readonly=True, states={'draft':[('readonly',False)]}),
		'vnd_lim': fields.float('Seller limit'),
		'vnd_lim_net': fields.boolean('Net limit ?'),
		'image': fields.binary('Image'),
		'paid_vnd':fields.function(_is_paid_vnd,string='Seller Paid',method=True,type='boolean'),
		'paid_ach':fields.function(_is_paid_ach,string='Buyer invoice reconciled',method=True,type='boolean'),
		'state': fields.selection((('draft','Draft'),('unsold','Unsold'),('paid','Paid'),('sold','Sold')),'State', required=True, readonly=True),
		'buyer_price': fields.function(_buyerprice, method=True, string='Buyer price',store=True),
		'seller_price': fields.function(_sellerprice, method=True, string='Seller price',store=True),
		'gross_revenue':fields.function(_grossprice, method=True, string='Gross revenue',store=True),
		'gross_margin':fields.function(_grossmargin, method=True, string='Gross Margin (%)',store=True),
		'costs':fields.function(_costs,method=True,string='Indirect costs',store=True),
		'statement': fields.many2one('account.bank.statement', 'Payement', readonly=True),
		'net_revenue':fields.function(_netprice, method=True, string='Net revenue',store=True),
		'net_margin':fields.function(_netmargin, method=True, string='Net Margin (%)',store=True)
	}
	_defaults = {
		'state':lambda *a: 'draft',
		'lot_num':lambda *a:1

	}
	_constraints = [
#		(_inv_constraint, 'Twice the same inventory number !', ['lot_num','bord_vnd_id'])
	]

	def name_get(self, cr, user, ids, context={}):
		if not len(ids):
			return []
		result = [ (r['id'], str(r['obj_num'])+' - '+r['name']) for r in self.read(cr, user, ids, ['name','obj_num'])]
		return result

	def name_search(self, cr, user, name, args=[], operator='ilike', context={}):
		try:
			ids = self.search(cr, user, [('obj_num','=',int(name))]+ args)
		except:
			ids = []
		if not ids:
			ids = self.search(cr, user, [('name',operator,name)]+ args)
		return self.name_get(cr, user, ids)

	def _sum_taxes_by_type_and_id(self, taxes):
		"""
		PARAMS: taxes: a list of dictionaries of the form {'id':id, 'amount':amount, ...}
		RETURNS	: a list of dictionaries of the form {'id':id, 'amount':amount, ...}; one dictionary per unique id.
			The others fields in the dictionaries (other than id and amount) are those of the first tax with a particular id.
		"""
		taxes_summed = {}
		for tax in taxes:
			key = (tax['type'], tax['id'])
			if key in taxes_summed:
				taxes_summed[key]['amount'] += tax['amount']
			else:
				taxes_summed[key] = tax

		return taxes_summed.values()

	def compute_buyer_costs(self, cr, uid, ids):
		amount_total = {}
		lots = self.browse(cr, uid, ids)
##CHECKME: est-ce que ca vaudrait la peine de faire des groupes de lots qui ont les memes couts pour passer des listes de lots a compute?
		taxes = []
		amount=0.0
	#	pt_tax=pool.get('account.tax')
		for lot in lots:
			taxes = lot.product_id.taxes_id
			if lot.bord_vnd_id.tax_id:
				taxes.append(lot.author_right)
			else:
				taxes += lot.auction_id.buyer_costs
			tax=self.pool.get('account.tax').compute(cr,uid,taxes,lot.obj_price,1)
			for t in tax:
				amount+=t['amount']
			amount+=lot.obj_price

		print "VALUE OF AMOUNT TOTAL",amount
		amount_total['value']= amount
		amount_total['amount']= amount
		return amount_total



#		for t in taxes_res:
#			t.update({'type': 0})
#		return self._sum_taxes_by_type_and_id(taxes_res)

#	lots=self.browse(cr,uid,ids)
#	amount=0.0
#	for lot in lots:
#		taxes=lot.product_id.taxe_id


	def _compute_lot_seller_costs(self, cr, uid, lot, manual_only=False):
		costs = []

		tax_cost_ids = [i.id for i in lot.auction_id.seller_costs]

		# if there is a specific deposit cost for this depositer, add it
		border_id = lot.bord_vnd_id
		if border_id:
			if border_id.tax_id:
				tax_cost_ids.append(border_id.tax_id.id)
		tax_costs = self.pool.get('account.tax').compute(cr, uid, tax_cost_ids, lot.obj_price, 1)

		# delete useless keys from the costs computed by the tax object... this is useless but cleaner...
		for cost in tax_costs:
			del cost['account_paid_id']
			del cost['account_collected_id']

		if not manual_only:
			costs.extend(tax_costs)
			for c in costs:
				c.update({'type': 0})

		if lot.vnd_lim_net and lot.obj_price>0:
#FIXME: la string 'remise lot' devrait passer par le systeme de traductions
			obj_price_wh_costs = reduce(lambda x, y: x + y['amount'], tax_costs, lot.obj_price)
			if obj_price_wh_costs < lot.vnd_lim:
				costs.append({	'type': 1,
								'id': lot.obj_num,
								'name': 'Remise lot '+ str(lot.obj_num),
								'amount': lot.vnd_lim - obj_price_wh_costs}
								#'account_id': lot.auction_id.acc_refund.id
							)
		return costs
	def compute_seller_costs(self, cr, uid, ids, manual_only=False):
		lots = self.browse(cr, uid, ids)
		costs = []

		# group objects (lots) by deposit id
		# ie create a dictionary containing lists of objects
		bord_lots = {}
		for lot in lots:
			key = lot.bord_vnd_id.id
			if not key in bord_lots:
				bord_lots[key] = []
			bord_lots[key].append(lot)

		# use each list of object in turn
		for lots in bord_lots.values():
			total_adj = 0
			total_cost = 0
			for lot in lots:
				total_adj += lot.obj_price or 0.0
				lot_costs = self._compute_lot_seller_costs(cr, uid, lot, manual_only)
				for c in lot_costs:
					total_cost += c['amount']
				costs.extend(lot_costs)
			bord = lots[0].bord_vnd_id
			if bord:
				if bord.specific_cost_ids:
					bord_costs = [{'type':2, 'id':c.id, 'name':c.name, 'amount':c.amount, 'account_id':c.account} for c in bord.specific_cost_ids]
					for c in bord_costs:
						total_cost += c['amount']
					costs.extend(bord_costs)
			if (total_adj+total_cost)<0:
#FIXME: translate tax name
				new_id = bord and bord.id or 0
				c = {'type':3, 'id':new_id, 'amount':-total_cost-total_adj, 'name':'Ristourne'}#, 'account_id':lots[0].auction_id.acc_refund.id}
				costs.append(c)
		return self._sum_taxes_by_type_and_id(costs)

	# sum remise limite net and ristourne
	def compute_seller_costs_summed(self, cr, uid, ids): #ach_pay_id
		taxes = self.compute_seller_costs(cr, uid, ids)
		taxes_summed = {}
		for tax in taxes:
			if tax['type'] == 1:
				tax['id'] = 0
	#FIXME: translate tax names
				tax['name'] = 'Remise limite nette'
			elif tax['type'] == 2:
				tax['id'] = 0
				tax['name'] = 'Frais divers'
			elif tax['type'] == 3:
				tax['id'] = 0
				tax['name'] = 'Rist.'
			key = (tax['type'], tax['id'])
			if key in taxes_summed:
				taxes_summed[key]['amount'] += tax['amount']
			else:
				taxes_summed[key] = tax
		return taxes_summed.values()

	# creates the transactions between tInvoicehe auction company and the seller
	# this is done by creating a new in_invoice for each
	def seller_trans_create(self,cr, uid,ids,context):
		"""
			Create a seller invoice for each bord_vnd_id, for selected ids.
		"""

		# use each list of object in turn
		invoices = {}
		group={}
		inv_ref=self.pool.get('account.invoice')
		for lot in self.browse(cr,uid,ids,context):
			partner_id = lot.bord_vnd_id.partner_id.id
			if not lot.auction_id.id:
				continue


			lot_name = lot.obj_num

			if lot.bord_vnd_id.id in invoices:
				inv_id = invoices[lot.bord_vnd_id.id]
			else:
				res = self.pool.get('res.partner').address_get(cr, uid, [lot.bord_vnd_id.partner_id.id], ['contact', 'invoice'])
				contact_addr_id = res['contact']
				invoice_addr_id = res['invoice']
				inv = {
					'name': 'Auction:' +lot.name,
					'journal_id': lot.auction_id.journal_seller_id.id,
					'partner_id': lot.bord_vnd_id.partner_id.id,
					'type': 'in_invoice',
				}
				inv.update(inv_ref.onchange_partner_id(cr,uid, [], 'in_invoice', lot.bord_vnd_id.partner_id.id)['value'])
				inv['account_id'] = inv['account_id'] and inv['account_id'][0]
				inv_id = inv_ref.create(cr, uid, inv, context)
				invoices[lot.bord_vnd_id.id] = inv_id

			self.write(cr,uid,[lot.id],{'sel_inv_id':inv_id,'state':'sold'})

			taxes = map(lambda x: x.id, lot.product_id.taxes_id)
			if lot.bord_vnd_id.tax_id:
				taxes.append(lot.bord_vnd_id.tax_id.id)
			else:
				taxes += map(lambda x: x.id, lot.auction_id.seller_costs)

			inv_line= {
				'invoice_id': inv_id,
				'quantity': 1,
				'product_id': lot.product_id.id,
				'name': '['+str(lot.obj_num)+'] '+lot.auction_id.name,
				'invoice_line_tax_id': [(6,0,taxes)],
				'account_analytic_id': lot.auction_id.account_analytic_id.id,
				'account_id': lot.auction_id.acc_expense.id,
				'price_unit': lot.obj_price,
			}
			self.pool.get('account.invoice.line').create(cr, uid, inv_line,context)
			inv_ref.button_compute(cr, uid, [inv_id])
		for inv in inv_ref.browse(cr, uid, invoices.values(), context):
			inv_ref.write(cr, uid, [inv.id], {
				'check_total': inv.total
			})
			wf_service = netsvc.LocalService('workflow')
			wf_service.trg_validate(uid, 'account.invoice', inv.id, 'invoice_open', cr)
		return invoices.values()

#	def lots_invoice_and_cancel_old_invoice(self, cr, uid, ids, invoice_number=False, buyer_id=False, action=False):
#		lots = self.read(cr, uid, ids, ['ach_inv_id'])
#
#		num_invoiced = 0
#		inv_ids = {}
#		for lot in lots:
#			if lot['ach_inv_id']:
#				inv_ids[lot['ach_inv_id'][0]] = True
#				num_invoiced += 1
#
#		if num_invoiced:
#			if not invoice_number:
#				# if some objects were already invoiced and the user didn't specify an invoice number,
#				# raise an exception
#				raise orm.except_orm('UserError', ('%d object(s) are already invoiced !' % (num_invoiced,), 'init'))
#			else:
#				wf_service = netsvc.LocalService("workflow")
#				# if the user gave an invoice number, cancel the old invoices containing
#				# the selected objects
#				for id in inv_ids:
#					wf_service.trg_validate(uid, 'account.invoice', id, 'invoice_cancel', cr)
#
#		# create a new invoice for the selected objects
#		return self.lots_invoice(cr, uid, ids, invoice_number, buyer_id, action)

	def lots_invoice(self, cr, uid, ids, context):
		"""(buyer invoice
			Create an invoice for selected lots (IDS) to BUYER_ID.
			Set created invoice to the ACTION state.
			PRE:
				ACTION:
					False: no action
					xxxxx: set the invoice state to ACTION

			RETURN: id of generated invoice
		"""

		dt = time.strftime('%Y-%m-%d')
		inv_ref=self.pool.get('account.invoice')
		invoices={}
		for lot in self.browse(cr, uid, ids,context):
			partner_ref = lot.ach_uid.id
			if not lot.auction_id.id:
				continue
			if not partner_ref:
				raise orm.except_orm('Missed buyer !', 'Please fill the field buyer in the third tab or use the button "Map user" to associate a buyer to this auction !')

			if (lot.auction_id.id,lot.ach_uid.id) in invoices:
				inv_id = invoices[(lot.auction_id.id,lot.ach_uid.id)]
			else:
				price = lot.obj_price or 0.0
				lot_name =lot.obj_num
				inv={
					'name':lot.auction_id.name,
					'journal_id': lot.auction_id.journal_id.id,
					'partner_id': lot.ach_uid.id,
					'type': 'out_invoice'
				}
				inv.update(inv_ref.onchange_partner_id(cr,uid, [], 'out_invoice', lot.ach_uid.id)['value'])
				inv['account_id'] = inv['account_id'] and inv['account_id'][0]

				inv_id = inv_ref.create(cr, uid, inv, context)

				invoices[(lot.auction_id.id,lot.ach_uid.id)] = inv_id
			self.write(cr,uid,[lot.id],{'ach_inv_id':inv_id,'state':'sold'})

			#calcul des taxes
			taxes = map(lambda x: x.id, lot.product_id.taxes_id)
			taxes+=map(lambda x:x.id, lot.auction_id.buyer_costs)
			if lot.author_right:
				taxes.append(lot.author_right.id)

			inv_line= {
				'invoice_id': inv_id,
				'quantity': 1,
				'product_id': lot.product_id.id,
				'name': '['+str(lot.obj_num)+'] '+ lot.name,
				'invoice_line_tax_id': [(6,0,taxes)],
				'account_analytic_id': lot.auction_id.account_analytic_id.id,
				'account_id': lot.auction_id.acc_income.id,
				'price_unit': lot.obj_price,
			}
			self.pool.get('account.invoice.line').create(cr, uid, inv_line,context)
		for inv in inv_ref.browse(cr, uid, invoices.values(), context):
			inv_ref.button_compute(cr, uid, [inv.id])
			wf_service = netsvc.LocalService('workflow')
			wf_service.trg_validate(uid, 'account.invoice', inv.id, 'invoice_open', cr)
		return invoices.values()

	def lots_pay(self, cr, uid, ids, buyer_id, account_id, amount):
		lots = self.browse(cr, uid, ids)
		if not len(lots):
			return True

		partner_ref = lots[0].ach_login
		auction = lots[0].auction_id
		auction_ref = auction.auction1
		account_src_id = ir.ir_get(cr,uid,[('meta','res.partner'), ('name','account.receivable')], (buyer_id or []) and [('id',str(buyer_id))] )[0][2]

#TODO: passer par le systeme de traduction
		auction_name = u'Auction ' + auction_ref + u', Part.: '+(partner_ref or '')+ u', %d lot(s)' %(len(lots),)

		transfer = {
			'name': auction_name[:60],
			'partner_id': buyer_id,
			'reference': auction_ref,
			'account_src_id': account_src_id,
			'type': 'in_payment',
			'account_dest_id': account_id,
			'amount': amount,
		}

		transfer_id = self.pool.get('account.transfer').create(cr, uid, transfer)
		self.pool.get('account.transfer').pay_validate(cr,uid,[transfer_id])
		self.write(cr, uid, ids, {'state':'paid', 'ach_pay_id':transfer_id})
		return True

	def lots_cancel_payment(self, cr, uid, ids):
		cr.execute('select id,ach_pay_id,ach_inv_id,state from auction_lots where ach_pay_id is not null and id in ('+','.join(map(str, ids))+')')
		results = cr.dictfetchall()

		pay_ids = []			# list of payment ids
		lot_invoiced_ids = []	# list of lot ids whose state is 'paid' and inv_id is not null
		lot_paid_ids = []		# list of lot ids whose state is 'paid' and inv_id is null
		not_paid_ids = []		# list of lot ids whose state is not 'paid'
		number_lot_paid = 0
		for r in results:
			if r['ach_pay_id']:
				pay_ids.append(r['ach_pay_id'])
				number_lot_paid += 1

			if r['state']=='paid':
				if r['ach_inv_id']:
					lot_invoiced_ids.append(r['id'])
				else:
					lot_paid_ids.append(r['id'])
			else:
				not_paid_ids.append(r['id'])

		if len(ids)!=number_lot_paid:
			print "Warning: not all lots were paid"

		if len(pay_ids):
			self.pool.get('account.transfer').pay_cancel(cr, uid, pay_ids)
			self.pool.get('account.transfer').unlink(cr, uid, pay_ids)

		if len(lot_paid_ids):
			self.write(cr,uid,lot_paid_ids, {'ach_pay_id':False, 'state':'draft'})
		if len(lot_invoiced_ids):
			self.write(cr,uid,lot_invoiced_ids, {'ach_pay_id':False, 'state':'invoiced'})
		if len(not_paid_ids):
			self.write(cr,uid,not_paid_ids, {'ach_pay_id':False})
		return True

	def numerotate(self, cr, uid, ids):
		cr.execute('select auction_id from auction_lots where id=%d', (ids[0],))
		auc_id = cr.fetchone()[0]
		cr.execute('select max(obj_num) from auction_lots where auction_id=%d', (auc_id,))
		try:
			max = cr.fetchone()[0]
		except:
			max = 0
		for id in ids:
			max+=1
			cr.execute('update auction_lots set obj_num=%d where id=%d', (max, id))
		return []

auction_lots()

#----------------------------------------------------------
# Auction Bids
#----------------------------------------------------------
class auction_bid(osv.osv):
	_name = "auction.bid"
	_description="Bid auctions"
	_columns = {
		'partner_id': fields.many2one('res.partner', 'Buyer Name', required=True),
		'contact_tel':fields.char('Contact',size=64),
		'name': fields.char('Bid ID', size=64,required=True),
		'auction_id': fields.many2one('auction.dates', 'Auction Date', required=True),
		'bid_lines': fields.one2many('auction.bid_line', 'bid_id', 'Bid'),
	}
	_defaults = {
		'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'auction.bid'),
	}

auction_bid()

class auction_lot_history(osv.osv):
	_name = "auction.lot.history"
	_description="Lot history"
	_columns = {
		'name': fields.date('Date',size=64),
		'lot_id': fields.many2one('auction.lots','Object', required=True, ondelete='cascade'),
		'auction_id': fields.many2one('auction.dates', 'Auction date', required=True, ondelete='cascade'),
		'price': fields.float('Withdrawn price', digits=(16,2))
	}
	_defaults = {
		'name': lambda *args: time.strftime('%Y-%m-%d')
	}
auction_lot_history()

class auction_bid_lines(osv.osv):
	_name = "auction.bid_line"
	_description="Bid"
	_columns = {
		'name': fields.char('Bid date',size=64),
		'bid_id': fields.many2one('auction.bid','Bid ID', required=True, ondelete='cascade'),
		'lot_id': fields.many2one('auction.lots','Object', required=True, ondelete='cascade'),
		'call': fields.boolean('To be Called'),
		'price': fields.float('Maximum Price')
	}
	_defaults = {
		'name': lambda *args: time.strftime('%Y-%m-%d')
	}
auction_bid_lines()

class report_buyer_auction(osv.osv):
	_name = "report.buyer.auction"
	_description = "Auction Reporting on buyer view"
	_auto = False
	_columns = {
		'buyer_login': fields.char('Buyer Login',size=64, readonly=True, select=1),
		'buyer':fields.many2one('res.partner', 'Buyer', readonly=True, select=2),
		'object':fields.integer('No of objects',readonly=True, select=1),
		'total_price':fields.float('Total Adj.', digits=(16,2), readonly=True, select=2),
		'avg_price':fields.float('Avg Adj.', digits=(16,2), readonly=True, select=2),
		'date': fields.date('Create Date',  select=1),
		'auction': fields.many2one('auction.dates', 'Auction date',readonly=True, select=1),

	}

	def init(self, cr):
		cr.execute('''
		create or replace view report_buyer_auction  as (
			select
				min(al.id) as id,
				al.ach_login as "buyer_login",
				substring(al.create_date for 7) || '-01' as date,
				al.ach_uid as "buyer",
				ad.id as auction,
				count(al.id) as "object",
				sum(al.obj_price) as "total_price",
				(sum(al.obj_price)/count(al.id)) as "avg_price"
			from
				auction_lots al,
				auction_dates ad
			where
				ad.id=al.auction_id
			group by
				substring(al.create_date for 7),
				al.ach_uid,
				ad.id,
				al.ach_login
		)''')
report_buyer_auction()

class report_buyer_auction2(osv.osv):
	_name = "report.buyer.auction2"
	_description = "Auction Reporting on buyer view"
	_auto = False
	_columns = {
		'auction': fields.many2one('auction.dates', 'Auction date',readonly=True, select=1),
		'buyer_login': fields.char('Buyer Login',size=64, readonly=True, select=True),
		'buyer':fields.many2one('res.partner', 'Buyer', readonly=True, select=2),
		'sumadj':fields.float('Sum of adjustication',readonly=True, select=True),
		'gross_revenue':fields.float('Gross Revenue', readonly=True, select=True),
		'net_revenue':fields.float('Net Revenue', readonly=True, select=True),
		'net_margin':fields.float('Net Margin', readonly=True, select=True),
		'date': fields.date('Create Date',  required=True)
	}
	def init(self, cr):
		cr.execute('''
			create or replace view report_buyer_auction2  as (
				select
					min(al.id) as id,
					substring(al.create_date for 7) || '-01' as date,
					al.ach_login as "buyer_login",
					al.ach_uid as "buyer",
					sum(al.obj_price) as sumadj,
					ad.id as auction,
					sum(al.gross_revenue) as gross_revenue,
					sum(al.net_revenue) as net_revenue,
					sum(al.net_margin) as net_margin
				from
					auction_lots al,
					auction_dates ad
				where
					al.auction_id=ad.id
				group by
					al.ach_uid,
					al.ach_login,
					ad.id,
					substring(al.create_date for 7)
			)''')
report_buyer_auction2()


class report_seller_auction(osv.osv):
	_name = "report.seller.auction"
	_description = "Auction Reporting on seller view"
	_auto = False
	_rec_name = 'date'
	_columns = {
		'auction': fields.many2one('auction.dates', 'Auction date',readonly=True, select=1),
		'seller': fields.many2one('res.partner','Seller',readonly=True, select=1),
		'object_number':fields.integer('No of Objects',readonly=True),
		'total_price':fields.float('Total adjudication',readonly=True),
		'avg_price':fields.float('Avg adjudication',readonly=True),
		'avg_estimation':fields.float('Avg estimation',readonly=True),
		'date': fields.date('Create Date',  required=True, select=1),
		'state': fields.selection((('draft','Draft'),('unsold','Unsold'),('sold','Sold')),'State',readonly=True, select=1)
	}

	def init(self, cr):
		cr.execute('''
			create or replace view report_seller_auction  as (
				select
					adl.id as auction,
					min(al.id) as id,
					adl.auction1 as date,
					ad.partner_id as seller,
					count(al.id) as "object_number",
					SUM(al.obj_price) as "total_price",
					(SUM(al.obj_price)/count(al.id)) as avg_price,
					sum(al.lot_est1+al.lot_est2)/2 as avg_estimation,
					al.state
				from
					auction_dates adl,
					auction_lots al,
					auction_deposit ad
				where
					al.auction_id=adl.id and ad.id=al.bord_vnd_id
				group by
					ad.partner_id,
					al.state,adl.auction1,adl.id
				)''')
report_seller_auction()

class report_seller_auction2(osv.osv):
	_name = "report.seller.auction2"
	_description = "Auction Reporting on seller view2"
	_auto = False
	_columns = {
		'seller': fields.many2one('res.partner','Seller',readonly=True, select=1),
		'auction': fields.many2one('auction.dates', 'Auction date',readonly=True, select=1),
		'sum_adj':fields.float('Sum Adjustication',readonly=True, select=2),
		'gross_revenue':fields.float('Gross revenue',readonly=True, select=2),
		'net_revenue':fields.float('Net revenue',readonly=True, select=2),
		'net_margin':fields.float('Net margin', readonly=True, select=2),
		'date': fields.date('Start of auction',  required=1),
	}

	def init(self, cr):
		cr.execute('''create or replace view report_seller_auction2  as
			(select
				min(al.id) as id,
				adl.auction1 as date,
				ad.partner_id as seller,
				adl.id as auction,
				sum(al.obj_price) as "sum_adj",
				sum(al.gross_revenue) as "gross_revenue",
				sum(al.net_revenue) as "net_revenue",
				sum(al.net_margin) as "net_margin"
			from
				auction_lots al,auction_dates adl,auction_deposit ad
			where
				adl.id=al.auction_id and ad.id=al.bord_vnd_id
			group by
				al.ach_uid,adl.auction1,adl.id,ad.partner_id)
			 ''')

report_seller_auction2()

class report_auction_view2(osv.osv):
	_name = "report.auction.view2"
	_description = "Auction Reporting on  view2"
	_auto = False
	_rec_name = 'date'
	_columns = {
		'auction': fields.many2one('auction.dates', 'Auction date',readonly=True, select=1),
		'sum_adj':fields.float('Sum of adjudication',readonly=True),
		'obj_number':fields.integer('# of Objects',readonly=True),
		'gross_revenue':fields.float('Gross revenue',readonly=True),
		'net_revenue':fields.float('Net revenue',readonly=True),
		'obj_margin':fields.float('Avg margin', readonly=True),
		'obj_margin_procent':fields.float('Net margin (%)', readonly=True),
		'date': fields.date('Beginning of auction',  required=True, select=1)
	}
	def init(self, cr):
		cr.execute('''create or replace view report_auction_view2 as (
			select
				ad.id,
				ad.auction1 as date,
				ad.id as "auction",
				count(al.id) as "obj_number",
				SUM(al.obj_price) as "sum_adj",
				SUM(al.gross_revenue) as "gross_revenue",
				SUM(al.net_revenue) as "net_revenue",
				SUM(al.net_revenue)/count(al.id) as "obj_margin",
				SUM(al.net_revenue)*100/sum(al.obj_price) as "obj_margin_procent"
			from
				auction_lots al
			left join
				auction_dates ad on (al.auction_id=ad.id)
			group by
				ad.id,
				ad.auction1
			)''')
report_auction_view2()

class report_auction_view(osv.osv):
	_name = "report.auction.view"
	_description = "Auction Reporting on view1"
	_auto = False
	_rec_name = 'auction_id'
	_columns = {
		'auction_id': fields.many2one('auction.dates', 'Auction date',readonly=True, select=1),
		'nobjects':fields.float('No of objects',readonly=True),
		'nbuyer':fields.float('No of buyers',readonly=True),
		'nseller':fields.float('No of sellers',readonly=True),
		'min_est':fields.float('Minimum Estimation', readonly=True, select=2),
		'max_est':fields.float('Maximum Estimation', readonly=True, select=2),
		'adj_price':fields.float('Adjudication price', readonly=True, select=2),
	}

	def init(self, cr):
		cr.execute('''create or replace view report_auction_view  as
			(select
				al.auction_id as id,
				al.auction_id as "auction_id",
				count(al.id) as "nobjects",
				count(al.ach_uid) as "nbuyer",
				count(al.bord_vnd_id) as "nseller",
				sum(al.lot_est1) as "min_est",
				sum(al.lot_est2) as "max_est",
				sum(al.obj_price) as "adj_price"
			from
				auction_lots al
			group by
				al.auction_id
		)''')

report_auction_view()

class report_auction_object_date(osv.osv):
	_name = "report.auction.object.date"
	_description = "Objects per day"
	_auto = False
	_columns = {
		'obj_num': fields.integer('# of Objects'),
		'name': fields.date('Created date', select=2),
		'month': fields.date('Month', select=1),
		'user_id':fields.many2one('res.users', 'User',select=1),
	}
 #l.create_uid as user,

	def init(self, cr):
		cr.execute("""create or replace view report_auction_object_date as
			(select
			   min(l.id) as id,
			   substring(l.create_date for 10) as name,
			   substring(l.create_date for 7)|| '-01' as month,
			   count(l.obj_num) as obj_num,
			   l.create_uid as user_id
			from
				auction_lots l
			group by
				substring(l.create_date for 10),
				substring(l.create_date for 7),
				l.create_uid
			)
		""")
report_auction_object_date()

class report_auction_estimation_adj_category(osv.osv):
	_name = "report.auction.estimation.adj.category"
	_description = "comparaison estimate/adjudication "
	_auto = False
	_columns = {
			'lot_est1': fields.float('Minimum Estimation',select=2),
			'lot_est2': fields.float('Maximum Estimation',select=2),
			'obj_price': fields.float('Adjudication price'),
			'date': fields.date('Date', readonly=True,select=1),
			'lot_type': fields.selection(_type_get, 'Object Type', size=64),
			'adj_total': fields.float('Total Adjudication',select=2),
			'user_id':fields.many2one('res.users', 'User', select=1)
	}

	def init(self, cr):
		cr.execute("""
			create or replace view report_auction_estimation_adj_category as (
				select
				   min(l.id) as id,
				   substring(l.create_date for 7)||'-'||'01' as date,
				   l.lot_type as lot_type,
				   sum(l.lot_est1) as lot_est1,
				   sum(l.lot_est2) as lot_est2,
				   sum(l.obj_price) as adj_total,
				   l.create_uid as user_id
				from
					auction_lots l,auction_dates m
				where
					l.auction_id=m.id and l.obj_price >0
				group by
					 substring(l.create_date for 7),lot_type,l.create_uid
			)
		""")
report_auction_estimation_adj_category()

class report_auction_adjudication(osv.osv):
	_name = "report.auction.adjudication"
	_description = "report_auction_adjudication"
	_auto = False
	_columns = {
			'name': fields.many2one('auction.dates','Auction date',readonly=True,select=1),
			'state': fields.selection((('draft','Draft'),('close','Closed')),'State', select=1),
			'adj_total': fields.float('Total Adjudication')
	}


	def init(self, cr):
		cr.execute("""
			create or replace view report_auction_adjudication as (
				select
					l.id as id,
					l.id as name,
					sum(m.obj_price) as adj_total
				from
					auction_dates l ,auction_lots m
					where
						m.auction_id=l.id
					group by
						l.id,l.name,l.auction1,l.auction2
			)
		""")
report_auction_adjudication()

class report_attendance(osv.osv):
	_name="report.attendance"
	_description = "Report Sign In/Out"
	_auto = False
	#_rec_name='date'
	_columns = {
		'name': fields.date('Date', readonly=True,select=1),
		'employee_id' : fields.many2one('hr.employee', 'Employee', select=1, readonly=True),
		'total_attendance': fields.float('Total', readonly=True),
}
	def init(self, cr):
		cr.execute("""CREATE OR REPLACE VIEW report_attendance AS
			SELECT
				id,
				name,
				employee_id,
				CASE WHEN SUM(total_attendance) < 0
					THEN (SUM(total_attendance) +
						CASE WHEN current_date <> name
							THEN 1440
							ELSE (EXTRACT(hour FROM current_time) * 60) + EXTRACT(minute FROM current_time)
						END
						)
					ELSE SUM(total_attendance)
				END /60  as total_attendance
			FROM (
				SELECT
					max(a.id) as id,
					a.name::date as name,
					a.employee_id,
					SUM(((EXTRACT(hour FROM a.name) * 60) + EXTRACT(minute FROM a.name)) * (CASE WHEN a.action = 'sign_in' THEN -1 ELSE 1 END)) as total_attendance
				FROM hr_attendance a
				where name > current_date + interval '-1 day'
				GROUP BY a.name::date, a.employee_id
			) AS fs
			GROUP BY name,fs.id,employee_id
			""")

report_attendance()


class report_deposit_border(osv.osv):
	_name="report.deposit.border"
	_description = "Report deposit border"
	_auto = False
	_rec_name='bord'
	_columns = {
		'bord': fields.char('Depositer Inventory', size=64, required=True),
		'seller': fields.many2one('res.users','Seller',select=1),
		'moy_est' : fields.float('Avg. Est', select=1, readonly=True),
		'total_marge': fields.float('Total margin', readonly=True),
		'nb_obj':fields.float('# of objects', readonly=True),
}
	def init(self, cr):
		cr.execute("""CREATE OR REPLACE VIEW report_deposit_border AS
			SELECT
				min(al.id) as id,
				ab.partner_id as seller,
				ab.name as bord,
				COUNT(al.id) as nb_obj,
				SUM((al.lot_est1 + al.lot_est2)/2) as moy_est,
				SUM(al.net_revenue)/(count(ad.id)) as total_marge

			FROM
				auction_lots al,auction_deposit ab,auction_dates ad
			WHERE
				ad.id=al.auction_id
				and al.bord_vnd_id=ab.id
			GROUP BY
				ab.name,ab.partner_id""")
report_deposit_border()

class report_object_encoded(osv.osv):
	_name = "report.object.encoded"
	_description = "Object encoded"
	_auto = False
	_columns = {
		'state': fields.selection((('draft','Draft'),('unsold','Unsold'),('paid','Paid'),('invoiced','Invoiced')),'State', required=True,select=True),
		'user_id':fields.many2one('res.users', 'User', select=1),
		'estimation': fields.float('Estimation',select=2),
		'date': fields.date('Create Date',  required=True),
		'gross_revenue':fields.float('Gross revenue',readonly=True, select=2),
		'net_revenue':fields.float('Net revenue',readonly=True, select=2),
		'obj_margin':fields.float('Net margin', readonly=True, select=2),
		'obj_ret':fields.integer('# obj ret', readonly=True, select=2),
		'adj':fields.integer('Adj.', readonly=True, select=2),
		'obj_num':fields.integer('# of Encoded obj.', readonly=True, select=1),
	}
	def init(self, cr):
		cr.execute('''create or replace view report_object_encoded  as
			(select min(al.id) as id,
				substring(al.create_date for 10) as date,
				al.state as state,
				al.create_uid as user_id,
				(SELECT count(1) FROM auction_lots WHERE obj_ret>0) as obj_ret,
				sum((100* al.lot_est1)/al.obj_price) as estimation,
				COUNT(al.obj_num) as obj_num
			from auction_lots al
			where al.obj_price>0 and state='draft'
			group by substring(al.create_date for 10), al.state, al.create_uid)
			 ''')
report_object_encoded()


class report_object_encoded_manager(osv.osv):
	_name = "report.object.encoded.manager"
	_description = "Object encoded"
	_auto = False
	_columns = {
		'state': fields.selection((('draft','Draft'),('unsold','Unsold'),('paid','Paid'),('invoiced','Invoiced')),'State', required=True,select=True),
		'user_id':fields.many2one('res.users', 'User', select=True),
		'estimation': fields.float('Estimation',select=True),
		'date': fields.date('Create Date',  required=True),
		'gross_revenue':fields.float('Gross revenue',readonly=True, select=True),
		'net_revenue':fields.float('Net revenue',readonly=True, select=True),
		'obj_margin':fields.float('Net margin', readonly=True, select=True),
		'obj_ret':fields.integer('# obj ret', readonly=True, select=True),
		'adj':fields.integer('Adj.', readonly=True, select=True),
		'obj_num':fields.integer('# of Encoded obj.', readonly=True, select=True),
	}
	def init(self, cr):
		cr.execute('''create or replace view report_object_encoded_manager  as
			(select
				min(al.id) as id,
				substring(al.create_date for 10) as date,
				al.state as state,
				al.create_uid as user_id,
				sum((100*lot_est1)/obj_price) as estimation,
				(SELECT count(1) FROM auction_lots WHERE obj_ret>0) as obj_ret,
				SUM(al.gross_revenue) as "gross_revenue",
				SUM(al.net_revenue) as "net_revenue",
				SUM(al.net_revenue)/count(al.id) as "obj_margin",
				COUNT(al.obj_num) as obj_num,
				SUM(al.obj_price) as "adj"
			from auction_lots al
			where al.obj_price>0 and state='draft'
			group by substring(al.create_date for 10), al.state, al.create_uid)
			 ''')
report_object_encoded_manager()
