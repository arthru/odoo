# -*- coding: utf-8 -*-
import openobject.templating

class SidebarTemplateEditor(openobject.templating.TemplateEditor):
    templates = ['/openerp/widgets/templates/sidebar.mako']
    ADD_SHARE_BUTTON = u'id="sidebar"'

    def insert_share_link(self, output):
        # Insert the link on the line right after the link to open the
        # attachment form
        form_opener_insertion = output.index(
                '\n',
                output.index(self.ADD_SHARE_BUTTON)) + 1
        output = output[:form_opener_insertion] + \
                 '''<div id="share-wizard" class="sideheader-a"><h2>${_("Sharing")}</h2></div>
                     <ul class="clean-a">
                         <li>
                             <a id="sharing" href="#share">${_("Share")}</a>
                         </li>
                     </ul>
                       <script type="text/javascript">
                           jQuery(document).ready(function() {
                               var $share = jQuery('#sharing').click(function(){
                                   var _domain =  jQuery('#_terp_domain').val();
                                   var _search_domain =  jQuery('#_terp_search_domain').val();
                                   var _context = jQuery('#_terp_context').val();
                                   var _view_name = jQuery('#_terp_string').val();
                                   openLink(openobject.http.getURL('/share', {domain: _domain, search_domain: _search_domain, context: _context, name: _view_name}));
                                   return false;
                               });
                           });
                       </script>
                       \n''' + \
                 output[form_opener_insertion:]
        return output

    def edit(self, template, template_text):
        output = super(SidebarTemplateEditor, self).edit(template, template_text)

        output = self.insert_share_link(output)
        return output
