from osv import fields
from osv import osv
import pooler
import tools
import netsvc

from plugin.customer_function import customer_function
from plugin.dynamic_text import dynamic_text
from plugin.php_url import php_url
from plugin.current_time import current_time

import re
import datetime


internal_html_report = '''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<HTML>
<HEAD>
<META HTTP-EQUIV="CONTENT-TYPE" CONTENT="text/html; charset=utf-8">
    <TITLE></TITLE>
    <META NAME="GENERATOR" CONTENT="OpenOffice.org 3.0  (Linux)">
    <META NAME="CREATED" CONTENT="20090420;15063300">
    <META NAME="CHANGED" CONTENT="20090420;15071700"> 
    <META NAME="Info 4" CONTENT="dm.offer.document">
    <STYLE TYPE="text/css">
        <!--
        @page { margin: 2cm }
        P { margin-bottom: 0.21cm }
        A:link { so-language: zxx }
        -->
    </STYLE>
</HEAD>
<BODY LANG="en-IN" DIR="LTR">
'''
_regex = re.compile('\[\[setHtmlImage\((.+?)\)\]\]')

def merge_message(cr, uid, keystr, context):
    logger = netsvc.Logger()
    def merge(match):
        dm_obj = pooler.get_pool(cr.dbname).get('dm.offer.document')
        id = context.get('document_id')
        obj = dm_obj.browse(cr, uid, id)
        exp = str(match.group()[2:-2]).strip()
        plugin_values = generate_plugin_value(cr, uid, id, context.get('address_id'), context)
        context.update(plugin_values)
        context.update({'object':obj,'time':time})
        result = eval(exp,context)
        if result in (None, False):
            return str("--------")
        return str(result)

    com = re.compile('(\[\[.+?\]\])')
    message = com.sub(merge, keystr)
    return message

def generate_reports(cr,uid,obj,report_type,context):

    print "Calling generate_reports from wi : ", obj.id
    print "Calling generate_reports source code : ", obj.source
    address_id = getattr(obj, obj.source).id
    print "address_id : ",address_id
    address_ids = []

    if obj.is_global:
        """ if segment workitem """
        print "source fields : ",getattr(obj.segment_id.customers_file_id, obj.source + "s")
        for cust_id in getattr(obj.segment_id.customers_file_id, obj.source + "s"):
            print "cust_id : ",cust_id
            address_ids.append(cust_id.id)
    else:
        """ if customer workitem """
        address_ids.append(address_id)

    print "address_ids : ", address_ids

    step_id = obj.step_id.id
    pool = pooler.get_pool(cr.dbname)
    dm_doc_obj = pool.get('dm.offer.document') 
    report_xml = pool.get('ir.actions.report.xml')
    r_type = report_type
    if report_type=='html2html':
        r_type = 'html'
    for address_id in address_ids:
        camp_id = obj.segment_id.proposition_id.camp_id.id
        type_id = pool.get('dm.campaign.document.type').search(cr,uid,[('code','=',r_type)])
        camp_mail_service_obj = pool.get('dm.campaign.mail_service')
        camp_mail_service_id = camp_mail_service_obj.search(cr,uid,[('campaign_id','=',camp_id),('offer_step_id','=',step_id)])
        print "camp_mail_service_id",camp_mail_service_id
        camp_mail_service = camp_mail_service_obj.browse(cr,uid,camp_mail_service_id)[0]
        print "camp_mail_service.mail_service_id",camp_mail_service.mail_service_id.time_mode
        if camp_mail_service.mail_service_id.time_mode=='interval' :
            kwargs =  {(camp_mail_service.mail_service_id.unit_interval):camp_mail_service.mail_service_id.action_interval}
            delivery_time = datetime.datetime.now() + datetime.timedelta(**kwargs)
        elif camp_mail_service.mail_service_id.time_mode=='date' :
            delivery_time = camp_mail_service.mail_service_id.action_date
        elif camp_mail_service.mail_service_id.time_mode=='hour' :
            temp_time = str(camp_mail_service.mail_service_id.action_hour)
            if time.strftime('%H.%M:') > temp_time:
                date = datetime.datetime.now() + datetime.timedelta(days=1).strftime('%Y-%m-%d')
            else : 
                date = time.strftime('%Y-%m-%d')
            delivery_time = date+' '+temp_time.replace('.',':')+':00'
        else :
            delivery_time=time.strftime('%Y-%m-%d %H:%M:%S')
        print "delivery_time",delivery_time

        document_id = dm_doc_obj.search(cr,uid,[('step_id','=',obj.step_id.id),('category_id','=','Production')])
        # TO ADD : Check if no docs 
        print "Doc id : ",document_id
        print report_type

        vals={  'segment_id': obj.segment_id.id,
            'name': obj.step_id.code + "_" +str(address_id),
            'type_id': type_id[0],
            'mail_service_id':camp_mail_service.mail_service_id.id,
            'delivery_time' : delivery_time,
            'document_id' : document_id[0],
            'address_id' : obj.address_id.id
            }
        camp_doc  = pool.get('dm.campaign.document').create(cr,uid,vals)
        print "camp_doc",camp_doc

        if document_id :
            report_ids = report_xml.search(cr,uid,[('document_id','=',document_id[0]),('report_type','=',report_type)])
            print "report_ids : ",report_ids
            print dm_doc_obj.read(cr,uid,document_id,['name','editor','content','subject'])[0]

            document_data = dm_doc_obj.read(cr,uid,document_id,['name','editor','content','subject'])[0]
            print "Doc name : ",document_data['name']
            context['address_id'] = address_id
            context['document_id'] = document_id[0]
            attachment_obj = pool.get('ir.attachment')
            if report_type=='html' and document_data['editor'] and document_data['editor']=='internal' and document_data['content']:
                report_data = internal_html_report +str(document_data['content'])+"</BODY></HTML>"
                report_data = merge_message(cr, uid, report_data, context)
                attach_vals={'name' : document_data['name'] + "_" + str(address_id),
                            'datas_fname' : 'report_test' + report_type ,
                            'res_model' : 'dm.campaign.document',
                            'res_id' : camp_doc,
                            'datas': base64.encodestring(report_data),
                            'file_type':'html'
                            }
                attach_id = attachment_obj.create(cr,uid,attach_vals)
                print "Attachment id and campaign doc id" , attach_id,camp_doc
            if report_ids :
                for report in pool.get('ir.actions.report.xml').browse(cr, uid, report_ids) :
                    srv = netsvc.LocalService('report.' + report.report_name)
                    report_data,report_type = srv.create(cr, uid, [], {},context)
                    attach_vals={'name' : document_data['name'] + "_" + str(address_id)+str(report.id),
                                 'datas_fname' : 'report.' + report.report_name + '.' + report_type ,
                                 'res_model' : 'dm.campaign.document',
                                 'res_id' : camp_doc,
                                 'datas': base64.encodestring(report_data),
                                 'file_type':report_type
                                 }
                    attach_id = attachment_obj.create(cr,uid,attach_vals)
                    print "Attachement : ",attach_id

def generate_plugin_value(cr, uid,**args):
    if not 'doc_id' in args and not args['doc_id'] :
        return False
    if not 'addr_id' in args and not args['addr_id'] :
        return False
    if not 'wi_id' in args and not args['wi_id'] :
        return False
    vals = {}
    localcontext = {'cr':cr,'uid':uid}
    localcontext.update(args)

    pool = pooler.get_pool(cr.dbname)
    def compute_customer_plugin(cr, uid, **args):
        res  = pool.get('ir.model').browse(cr, uid, args['plugin_obj'].model_id.id)    
        args['model_name'] = res.model
        args['field_name'] = str(args['plugin_obj'].field_id.name)
        args['field_type'] = str(args['plugin_obj'].field_id.ttype)
        args['field_relation'] = str(args['plugin_obj'].field_id.relation)
        return customer_function(cr, uid, **args)

    dm_document = pool.get('dm.offer.document')
    dm_plugins_value = pool.get('dm.plugins.value')

    plugins = dm_document.browse(cr, uid, args['doc_id'], ['document_template_plugin_ids' ])

    for plugin_obj in plugins['document_template_plugin_ids'] :
        localcontext['plugin_obj'] = plugin_obj
        plugin_args = {}
        if plugin_obj.python_code : 
            exec plugin_obj.python_code in localcontext
            plugin_value = localcontext['plugin_value']
        elif plugin_obj.type in ('fields','image'):
            plugin_value = compute_customer_plugin(cr, uid, plugin_obj = plugin_obj, addr_id = args['addr_id'], wi_id = args['wi_id'])
        else :
            arg_ids = pool.get('dm.plugin.argument').search(cr,uid,[('plugin_id','=',plugin_obj.id)])
            for arg in pool.get('dm.plugin.argument').browse(cr,uid,arg_ids):
                if not arg.stored_plugin :
                    plugin_args[str(arg.name)]=arg.value
                else :
                    value = compute_customer_plugin(cr, uid, plugin_obj = arg.custome_plugin_id, addr_id=args['addr_id'], wi_id=args['wi_id'])
                    plugin_args[str(arg.custome_plugin_id.code)] = value
            if plugin_obj.type == 'dynamic_text' :
                plugin_args['ref_text_id'] = plugin_obj.ref_text_id.id
                args.update(plugin_args)
                plugin_value = dynamic_text(cr, uid, **args)
            elif plugin_obj.type == 'url' :
                plugin_args['encode'] = plugin_obj.encode
                plugin_value = php_url(cr, uid,**plugin_args)
            else :
                path = os.path.join(os.getcwd(), "addons/dm/dm_dtp_plugins", cr.dbname)
                plugin_name = plugin_obj.file_fname.split('.')[0]
                sys.path.append(path)
                X =  __import__(plugin_name)
                plugin_func = getattr(X, plugin_name)
                plugin_value = plugin_func(cr, uid,**args)

        if plugin_obj.store_value :
            dm_plugins_value.create(cr, uid,{'date':time.strftime('%Y-%m-%d'),
                                             'address_id':args['addr_id'],
                                             'plugin_id':plugin_obj.id,
                                             'value' : plugin_value})
        vals[str(plugin_obj.code)] = plugin_value
    return vals



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
