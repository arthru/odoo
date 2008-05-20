
##############################################################################
#
# Copyright (c) 2007 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

from osv import fields,osv
from osv import orm
#Old version
#-----------
#class cci_partner_profile_answer(osv.osv):#added for partner.ods
#    _name="cci_partner_profile.answer"
#    _description="Partner Answer"
#    _columns={
#        "partner_id": fields.many2one('res.partner','Partner'),
#        "address_id": fields.many2one('res.partner.address','Address'),
#        "contact_id": fields.many2one('res.partner.contact','Contact'),
#        "question_id": fields.many2one('crm_profiling.question','Question'),
#        "answer_id": fields.many2one('crm_profiling.answer','Answer'),
#        "answer_text":fields.char('Answer Text',size=20)#should be corect
#        }
#cci_partner_profile_answer()


class question(osv.osv):
	_inherit="crm_profiling.question"
	_columns={
		'target':fields.selection([('res.partner','Partner'),('res.partner.contact','Contact'),('res.partner.address','Address')], 'Target', required=True),
		'open_question':fields.boolean('Open Question'),
		}
	_defaults = {
		'target': lambda *args: 'res.partner',
		'open_question': lambda *args : False,
	}
question()

class answer(osv.osv):
	_inherit="crm_profiling.answer"
	_columns={
		"text": fields.text("Open Answer", translate=True),
		}
answer()

class res_partner_contact(osv.osv):
	_inherit="res.partner.contact"
	_columns={
		"answers_ids": fields.many2many("crm_profiling.answer","contact_question_rel","contact","answer","Answers", domain=[('question_id.target','=','res.partner.contact')]),
		}
res_partner_contact()

class res_partner_address(osv.osv):
	_inherit="res.partner.address"
	_columns={
		"answers_ids": fields.many2many("crm_profiling.answer","address_question_rel","address","answer","Answers",domain=[('question_id.target','=','res.partner.address')]),
		}
res_partner_address()

class partner(osv.osv):
	_inherit="res.partner"

	def _questionnaire_compute(self, cr, uid, data, context):
		temp = []
		for field in data['form']:
			if field.startswith("quest_form") and data['form'][field] != 0 :
				question_id = field.lstrip('quest_form')
				question_rec = self.pool.get('crm_profiling.question').browse(cr, uid, int(question_id))
				if question_rec.open_question:
					vals = {
						'name': '/',
						'question_id': question_rec.id,
						'text': data['form'][field]
					}
					data['form'][field] = self.pool.get('crm_profiling.answer').create(cr, uid, vals, context)
		return super(partner,self)._questionnaire_compute(cr, uid, data, context)

	_columns={
		"answers_ids": fields.many2many("crm_profiling.answer","partner_question_rel","partner","answer","Answers", domain=[('question_id.target','!=','res.partner.address'),('question_id.target','!=','res.partner.contact')]),
		}
partner()

class questionnaire(osv.osv):
	_inherit="crm_profiling.questionnaire"

	def build_form(self, cr, uid, data, context):
		quest_form,quest_fields = super(questionnaire,self).build_form(cr, uid, data, context)
		for field in quest_fields:
			question_id = field.lstrip('quest_form')
			question_rec = self.pool.get('crm_profiling.question').browse(cr, uid, int(question_id))
			if question_rec.open_question:
				quest_fields[field] = {'string': question_rec.name, 'type': 'text',}
		return quest_form, quest_fields
questionnaire()
