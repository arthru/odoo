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

import ir
import pooler
from report.interface import report_rml
from report.interface import toxml

from tools.translate import _


#FIXME: we should use toxml
class report_custom(report_rml):
    def create_xml(self, cr, uid, ids, datas, context={}):
        number = (datas.get('form', False) and datas['form']['number']) or 1
        pool = pooler.get_pool(cr.dbname)
        product_pool = pool.get('product.product')
        product_uom_pool = pool.get('product.uom')
        supplier_info_pool = pool.get('product.supplierinfo')
        workcenter_pool = pool.get('mrp.workcenter')
        user_pool = pool.get('res.users')
        bom_pool = pool.get('mrp.bom')
        def process_bom(bom, currency_id, factor=1):
            xml = '<row>'
            sum = 0
            sum_strd = 0
            prod = product_pool.browse(cr, uid, bom['product_id'])

            prod_name = bom['name']
            prod_qtty = factor * bom['product_qty']
            product_uom = product_uom_pool.browse(cr, uid, bom['product_uom'], context=context)
            level = 1
            main_sp_price, main_sp_name , main_strd_price = '','',''
            sellers, sellers_price = '',''

            if prod.seller_id:
                main_sp_name = "<b>%s</b>\r\n" %(prod.seller_id.name)
                price = supplier_info_pool.price_get(cr, uid, prod.seller_id.id, prod.id, number*prod_qtty)[prod.seller_id.id]
                price = product_uom_pool._compute_price(cr, uid, prod.uom_id.id, price, to_uom_id=product_uom.id)
                main_sp_price = '<b>%s</b>\r\n' %(str(price))
                sum += prod_qtty*price
            std_price = product_uom_pool._compute_price(cr, uid, prod.uom_id.id, prod.standard_price, to_uom_id=product_uom.id)
            main_strd_price = str(std_price) + '\r\n'
            sum_strd = prod_qtty*std_price

            for seller_id in prod.seller_ids:
                sellers +=  '- <i>'+ seller_id.name.name +'</i>\r\n'
                price = supplier_info_pool.price_get(cr, uid, seller_id.name.id, prod.id, number*prod_qtty)[seller_id.name.id]
                price = product_uom_pool._compute_price(cr, uid, prod.uom_id.id, price, to_uom_id=product_uom.id)
                sellers_price += '<i>' + str(price) + '</i>\r\n'

            xml += "<col para='yes'>" + prod_name + '</col>'
            xml += "<col para='yes'>" + main_sp_name +  sellers + '</col>'
            xml += "<col f='yes'>" + str(prod_qtty) + '</col>'
            xml += "<col f='yes'>" + product_uom.name + '</col>'
            xml += "<col f='yes'>" + main_strd_price + '</col>'
            xml += "<col f='yes'>" + main_sp_price +  sellers_price + '</col>'


            xml += '</row>'
            return xml, sum, sum_strd

        def process_workcenter(wrk):
            workcenter = workcenter_pool.browse(cr, uid, wrk['workcenter_id'])
            cost_cycle = wrk['cycle']*workcenter.costs_cycle
            cost_hour = wrk['hour']*workcenter.costs_hour
            total = cost_cycle + cost_hour
            xml = '<row>'
            xml += "<col para='yes'>" + workcenter.name + '</col>'
            xml += "<col/>"
            xml += "<col/>"
            xml += "<col f='yes'>" + str(cost_cycle) + '</col>'
            xml += "<col f='yes'>" + str(cost_hour) + '</col>'
            xml += "<col f='yes'>" + str(cost_hour + cost_cycle) + '</col>'
            xml += '</row>'

            return xml, total


        xml = ''
        config_start = """
        <config>
            <date>09/09/2005</date>
            <PageSize>210.00mm,297.00mm</PageSize>
            <PageWidth>595.27</PageWidth>
            <PageHeight>841.88</PageHeight>
            <tableSize>55.00mm,55.00mm, 20.00mm, 22.00mm, 22.00mm, 25.00mm</tableSize>
            """
        config_stop = """
            <report-footer>Generated by OpenERP</report-footer>
        </config>
        """

        workcenter_header = """
            <lines style='header'>
                <row>
                    <col>%s</col>
                    <col/>
                    <col t='yes'/>
                    <col t='yes'>%s</col>
                    <col t='yes'>%s</col>
                    <col t='yes'>%s</col>
                </row>
            </lines>
        """ % (_('Work Center name'), _('Cycles Cost'), _('Hourly Cost'),_('Work Cost'))
        prod_header = """
                <row>
                    <col>%s</col>
                    <col>%s</col>
                    <col t='yes'>%s</col>
                    <col t='yes'>%s</col>
                    <col t='yes'>%s</col>
                    <col t='yes'>%s</col>
                </row>
        """ % (_('Component'), _('Component suppliers'), _('Quantity'), _('Uom'), _('Cost Price per Uom'), _('Supplier Price per Uom'))

        company_currency = user_pool.browse(cr, uid, uid).company_id.currency_id.id
        for product in product_pool.browse(cr, uid, ids, context=context):
            bom_id = bom_pool._bom_find(cr, uid, product.id, product.uom_id.id)
            title = "<title>%s</title>" %(_("Cost Structure"))
            title += "<title>%s</title>" %product.name
            xml += "<lines style='header'>" + title + prod_header + "</lines>"
            if not bom_id:
                total_strd = number * product.standard_price
                total = number * product_pool.price_get(cr, uid, [product.id], 'standard_price')[product.id]
                xml += """<lines style='lines'><row>
                    <col para='yes'>-</col>
                    <col para='yes'>-</col>
                    <col para='yes'>-</col>
                    <col para='yes'>-</col>
                    <col para='yes'>-</col>
                    <col para='yes'>-</col>
                    </row></lines>"""
                xml += """<lines style='total'> <row>
                    <col>%s %s %s %s : </col>
                    <col/>
                    <col/>
                    <col f='yes'/>
                    <col f='yes'>%s</col>
                    <col f='yes'>%s</col>
                    </row></lines>'"""%(_('Total Cost'), _('of'), str(number), product.uom_id.name, str(total_strd), str(total))
            else:
                bom = bom_pool.browse(cr, uid, bom_id, context=context)
                factor = number * product.uom_id.factor / bom.product_uom.factor
                sub_boms = bom_pool._bom_explode(cr, uid, bom, factor / bom.product_qty)
                total = 0
                total_strd = 0
                parent_bom = {
                        'product_qty': bom.product_qty,
                        'name': bom.product_id.name,
                        'product_uom': bom.product_uom.id,
                        'product_id': bom.product_id.id
                }
                xml_tmp = ''
                for sub_bom in (sub_boms and sub_boms[0]) or [parent_bom]:
                    txt, sum, sum_strd = process_bom(sub_bom, company_currency)
                    xml_tmp +=  txt
                    total += sum
                    total_strd += sum_strd

                xml += "<lines style='lines'>" + xml_tmp + '</lines>'
                xml += """<lines style='sub_total'> <row>
                    <col>%s %s %s %s : </col>
                    <col/>
                    <col/>
                    <col t='yes'/>
                    <col t='yes'>%s</col>
                    <col t='yes'>%s</col>
                    </row></lines>'"""%(_('Cost'), _('of'), str(number), product.uom_id.name, str(total_strd), str(total))

                total2 = 0
                xml_tmp = ''
                for wrk in (sub_boms and sub_boms[1]):
                    txt, sum = process_workcenter(wrk)
                    xml_tmp += txt
                    total2 += sum
                if xml_tmp:
                    xml += workcenter_header
                    xml += "<lines style='lines'>" + xml_tmp + '</lines>'
                    xml += """<lines style='sub_total'> <row>
                    <col>%s %s %s %s : </col>
                    <col/>
                    <col/>
                    <col/>
                    <col/>
                    <col t='yes'>%s</col>
                    </row></lines>'"""%(_('Work Cost'), _('of'), str(number), product.uom_id.name, str(total2))
                xml += """<lines style='total'> <row>
                    <col>%s %s %s %s : </col>
                    <col/>
                    <col/>
                    <col t='yes'/>
                    <col t='yes'>%s</col>
                    <col t='yes'>%s</col>
                    </row></lines>'"""%(_('Total Cost'), _('of'), str(number), product.uom_id.name, str(total_strd+total2), str(total+total2))

        xml = '<?xml version="1.0" ?><report>' + config_start + config_stop + xml + '</report>'

        return xml

report_custom('report.product.price', 'product.product', '', 'addons/mrp/report/price.xsl')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

