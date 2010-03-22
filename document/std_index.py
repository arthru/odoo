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

import StringIO
import odt2txt
from subprocess import Popen, PIPE
from content_index import indexer, cntIndex
from subprocess import Popen, PIPE

def _to_unicode(s):
    try:
        return s.decode('utf-8')
    except UnicodeError:
        try:
            return s.decode('latin')
        except UnicodeError:
            try:
                return s.encode('ascii')
            except UnicodeError:
                return s

class TxtIndex(indexer):
    def _getMimeTypes(self):
        return ['text/plain','text/html','text/diff','text/xml', 'text/*', 
        'application/xml']
    
    def _getExtensions(self):
        return ['.txt', '.py']

    def _doIndexContent(self,content):
        return content
        
cntIndex.register(TxtIndex())

class PptxIndex(indexer):
    def _getMimeTypes(self):
        return [ 'application/vnd.openxmlformats-officedocument.presentationml.presentation']
    
    def _getExtensions(self):
        return ['.pptx']

    def _doIndexFile(self,fname):
        # Download pptx2txt package from  http://sourceforge.net/projects/pptx2txt/" link.
        # To install this tool, just copy pptx2txt.pl to appropriate place (e.g. /usr/bin directory)
        fp = Popen(['pptx2txt.pl', fname], shell=False, stdout=PIPE).stdout
        fp.read()
        file_obj = open(str(fname + ".txt"), "r")
        data = file_obj.read()
        return _to_unicode(data)

cntIndex.register(PptxIndex())

class DocIndex(indexer):
    def _getMimeTypes(self):
        return [ 'application/ms-word']
    
    def _getExtensions(self):
        return ['.doc']

    def _doIndexFile(self,fname):
        fp = Popen(['antiword', fname], shell=False, stdout=PIPE).stdout
        return _to_unicode( fp.read())

cntIndex.register(DocIndex())

class DocxIndex(indexer):
    def _getMimeTypes(self):
        return [ 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
    
    def _getExtensions(self):
        return ['.docx']

    def _doIndexFile(self,fname):
        # Download docx2txt package from  "http://sourceforge.net/projects/docx2txt/" link.   
        # In case, you don't want to use Makefile for installation, you can follow these steps for manual installation.
        # Copy docx2txt.pl, docx2txt.sh and docx2txt.config to appropriate place (e.g. /usr/bin directory) . used following command.
        # --> cp docx2txt.pl docx2txt.sh docx2txt.config /usr/bin/

        fp = Popen(['docx2txt.pl', fname], shell=False, stdout=PIPE).stdout
        fp.read()
        file_obj = open(str(fname + ".txt"), "r")
        data = file_obj.read()
        return _to_unicode(data)

cntIndex.register(DocxIndex())

class PdfIndex(indexer):
    def _getMimeTypes(self):
        return [ 'application/pdf']
    
    def _getExtensions(self):
        return ['.pdf']

    def _doIndexFile(self,fname):
        fp = Popen(['pdftotext', '-enc', 'UTF-8', '-nopgbrk', fname, '-'], shell=False, stdout=PIPE).stdout
        return _to_unicode( fp.read())

cntIndex.register(PdfIndex())

class ImageNoIndex(indexer):
    def _getMimeTypes(self):
        return [ 'image/*']
    
    def _getExtensions(self):
        #better return no extension, and let 'file' do its magic
        return []
        #return ['.png','.jpg','.gif','.jpeg','.bmp','.tiff']

    def _doIndexContent(self,content):
        return 'image'


cntIndex.register(ImageNoIndex())

#class Doc(indexer):
    #def _getDefMime(self,ext):

#def content_index(content, filename=None, content_type=None):
    #fname,ext = os.path.splitext(filename)
    #result = ''
    #elif ext in ('.xls','.ods','.odt','.odp'):
        #s = StringIO.StringIO(content)
        #o = odt2txt.OpenDocumentTextFile(s)
        #result = _to_unicode(o.toString())
        #s.close()
    #elif ext in ('.txt','.py','.patch','.html','.csv','.xml'):
        #result = content
    #else:
        #result = content
    #return result

#eof
