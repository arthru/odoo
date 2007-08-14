# -*-encoding: iso8859-1 -*-
##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
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

import sql_db
from osv.osv import osv_pools
from report.interface import report_rml
import pooler
class report_custom(report_rml):
	def create(self, uid, ids, datas, context):
		start = datas['form']['start']
		stop = datas['form']['stop']
		# select all ranges which contain some labels in the (start, stop) range
		vignettes_obj = pooler.get_pool(cr.dbname).get('huissier.vignettes')
		#cr = sql_db.db.cursor()
		new_ids = vignettes_obj.search(cr, uid, [('first','<=',stop),('last','>=',start)])
		cr.close()
		
#		file('/tmp/terp.xml','wb+').write(xml)
		return report_rml.create(self, uid, new_ids, datas, context)

report_custom('report.huissier.labels.reprint', 'huissier.vignettes', 'addons/huissier/report/labels.xml', 'addons/huissier/report/labels.xsl')
