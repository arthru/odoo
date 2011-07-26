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

from osv import fields, osv
import os
from tools.translate import _


class translate_message(osv.osv_memory):
    _name = "translate.message"
    _description = "Give Message After Translation completed"

    def default_get(self, cr, uid, fields, context=None):
        """ Get default values
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for default value
        @param context: A standard dictionary
        @return: Default values of fields
        """
        if context is None:
            context = {}
        res ={}
        if context.get('warning'):
            if 'message' in fields:
                res.update({'message': _(context.get('warning'))})
        return res

    _columns = {
        'message' : fields.text('Message', size=64, readonly=True),
     }

translate_message()


class wizard_multi_charts_accounts(osv.osv_memory):
    """
    Change wizard that a new account chart for a company.
        * Add option to install languages during the setup
        * Copy translations for COA, Tax, Tax Code and Fiscal Position from templates to target objects.
    """
    _inherit = 'wizard.multi.charts.accounts'

    def copy_translations(self, cr, uid, langs, in_obj, in_field, in_ids, out_obj, out_ids, context):
        result = {}
        if context is None:
            context = {}
        xlat_obj = self.pool.get('ir.translation')
        #find the source from Account Template
        result = [(x.id, x.name) for x in in_obj.browse(cr, uid, in_ids)]
        src = dict(result)
        message = ''
        for lang in langs:
            notdone = []
            #find the value from Translation
            value = xlat_obj._get_ids(cr, uid, in_obj._name + ',' + in_field, 'model', lang, in_ids)
            for j in range(len(in_ids)):
                in_id = in_ids[j]
                if not value[in_id]:
                    # if source have no translation available
                    notdone.append(src[in_id])
                else:
                    #copy Translation from Source to Destination object
                    xlat_obj.create(cr, uid, {
                      'name': out_obj._name + ',' + in_field,
                      'type': 'model',
                      'res_id': out_ids[j],
                      'lang': lang,
                      'src': src[in_id],
                      'value': value,
                })
            if notdone:
                message += '\nLanguage:-%s \n\tThere is no translation available for following accounts: \n\t%s '\
                            % (lang, '\n\t'.join(notdone))
            else:
                message += '\nLanguage:-%s \n\tTranslation successfully done.'  % (lang)
        resource_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'l10n_multilang', 'view_translate_message_wizard')
        #open new wizard its for saw warning message
        if message:
            context.update({'warning': message})
            return {
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'translate.message',
                'views': [(resource_id and resource_id[1] or False,'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': context
            }

    def execute(self, cr, uid, ids, context=None):
        res = super(wizard_multi_charts_accounts, self).execute(cr, uid, ids, context=context)
        obj_multi = self.browse(cr, uid, ids[0], context=context)
        obj_mod = self.pool.get('ir.module.module')
        obj_acc_template = self.pool.get('account.account.template')
        obj_acc = self.pool.get('account.account')
        obj_data = self.pool.get('ir.model.data')

        company_id = obj_multi.company_id.id
        acc_template_root_id = obj_multi.chart_template_id.account_root_id.id
        acc_root_id = obj_acc.search(cr, uid, [('company_id', '=', company_id), ('parent_id', '=', None)])[0]                       
                         
        # load languages
        langs = []
        installed_mids = obj_mod.search(cr, uid, [('state', '=', 'installed')])
        for lang in obj_multi.lang_ids:
            langs.append(lang.code)
            obj_mod.update_translations(cr, uid, installed_mids, lang.code)

        # copy account.account translations
        in_ids = obj_acc_template.search(cr, uid, [('id', 'child_of', [acc_template_root_id])], order='id')[1:]
        out_ids = obj_acc.search(cr, uid, [('id', 'child_of', [acc_root_id])], order='id')[1:]
        result = self.copy_translations(cr, uid, langs, obj_acc_template, 'name', in_ids, obj_acc, out_ids, context)
        if result:
            return result
        return {}

    def onchange_chart_template_id(self, cr, uid, ids, chart_template_id=False, context=None):
        res = super(wizard_multi_charts_accounts, self).onchange_chart_template_id(cr, uid, ids, chart_template_id, context=context)
        installed_lang = self.get_lang(cr, uid, chart_template_id, context=context)
        res['value'].update({'lang_ids': installed_lang})
        return res
    
    def get_lang(self, cr, uid, template_id=False, context=None):
        installed_lang = []
        if template_id:
            cr.execute("SELECT module from ir_model_data where model='account.chart.template' and res_id=%s" % (template_id))
            modulename = cr.fetchone()
            modulename = modulename and modulename[0] or False
            if modulename:
                module_obj = self.pool.get('ir.module.module')
                module_id = module_obj.search(cr, uid, [('name', '=', modulename)], context=context)
                module = module_obj.browse(cr, uid, module_id, context=context)[0]
                dirpath = module_obj._translations_subdir(module)
                if dirpath:
                    for po in os.listdir(dirpath):
                        lang_id = self.pool.get('res.lang').search(cr, uid, [('code', 'ilike', '%s' % (po.split('.')[0])), ('translatable', '=', True)], context=context)
                        if lang_id:
                            installed_lang.append(lang_id[0])
        return installed_lang

    def default_get(self, cr, uid, fields, context=None):
        res = super(wizard_multi_charts_accounts, self).default_get(cr, uid, fields, context=context)
        installed_lang = self.get_lang(cr, uid, res.get('chart_template_id'), context=context)
        res.update({'lang_ids': installed_lang, 'bank_accounts_id': []})
        return res

    _columns = {
        'lang_ids': fields.many2many('res.lang', 'res_lang_type_rel', 'wizard_id', 'lang_id', 'Language'),
        'bank_from_template': fields.boolean('Banks/Cash from Template', 
            help="If True then Generate Bank/Cash accounts and journals from the Templates.", readonly=True),
    }
  
wizard_multi_charts_accounts()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
