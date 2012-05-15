# -*- coding: utf-8 -*-
from osv import fields, osv
import random
import string
from etherpad import EtherpadLiteClient
import urllib2
from tools.translate import _


class pad_common(osv.osv_memory):
    _name = 'pad.common'
    
    def pad_generate_url(self, cr, uid, model, context=None):
        pad_url_template = self._pad_url_template(cr, uid, context)
        s = string.ascii_uppercase + string.digits
        salt = ''.join([s[random.randint(0, len(s) - 1)] for i in range(8)])
        template_vars = {
            'db' : cr.dbname,
            'model' : model,
            'salt' : salt,
        }
        url = pad_url_template % template_vars
        api_key =  self._pad_api_key(cr, uid, context)
        if api_key:
            urls = url.split('/')
            api_url = '/'.join(urls[:3]) + "/api"
            pad_id = urls[-1]            
            ep_client = EtherpadLiteClient(api_key, api_url)
            try:
                ep_client.createPad(pad_id," ")
            except ValueError as strerror:
                raise osv.except_osv(_('Configuration Error !'),_("Etherpad Have Wrong API Key."))
            except urllib2.HTTPError as e:
                raise osv.except_osv(_('Configuration Error !'),_("Etherpad Have Wrong API URL."))
            except urllib2.URLError as e:
                raise osv.except_osv(_('Configuration Error !'),_("Etherpad Have Wrong Pad URL Template."))
        return url

    def _pad_api_key(self, cr, uid, context=None):
        return self.pool.get('res.users').browse(cr,uid, uid, context).company_id.etherpad_api_key
        
    def _pad_url_template(self, cr, uid, context=None):
        return self.pool.get('res.users').browse(cr,uid, uid, context).company_id.pad_url_template


    def _pad_user_name(self, cr, uid, ids=None, name = None, arg = None, context=None):        
        res = {}
        user = self.pool.get('res.users')
        for id in ids:
            res[id] = user.browse(cr,uid, uid,context=context).name
        return res        
    
    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'pad_url':self.pad_generate_url(cr, uid, self._name),            
        })
        return super(pad_common, self).copy(cr, uid, id, default, context)
                    
    _columns = {
        'pad_url': fields.char('Full Screen', size=512),
        'pad_username': fields.function(_pad_user_name, string='User Name', type='char',size=64),
        
    }
    _defaults = {
        'pad_url': lambda self, cr, uid, context: self.pad_generate_url(cr, uid, self._name, context),
        'pad_username': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid, context).name,
    }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
