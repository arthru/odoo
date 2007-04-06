import uno
import string
import unohelper
from com.sun.star.task import XJobExecutor
from lib.gui import *
import xmlrpclib
    #-----------------------------------------------------
    #  Implementaion of DBModalDialog Class
    #-----------------------------------------------------
class Repeatln:
    def __init__(self):
        self.win = DBModalDialog(60, 50, 140, 250, "Field Builder")

        self.win.addFixedText("lblVariable", 18, 12, 30, 15, "Variable :")

        self.win.addComboBox("cmbVariable", 45, 10, 90, 15,True,
                             itemListenerProc=self.cmbVariable_selected)

        self.win.addFixedText("lblName", 5, 32, 40, 15, "Object Name :")

        self.win.addEdit("txtName", 45, 30, 90, 15,)

        self.insVariable = self.win.getControl( "cmbVariable" )

        self.win.addFixedText("lblFields", 25, 52, 25, 15, "Fields :")

        self.win.addComboListBox("lstFields", 45, 50, 90, 150, False)

        self.insField = self.win.getControl( "lstFields" )

        sock = xmlrpclib.ServerProxy('http://localhost:8069/xmlrpc/object')

        #self.getModule(sock)

        self.sObj=None

        self.win.addButton('btnOK',-5 ,-25,45,15,'Ok'
                      ,actionListenerProc = self.btnOkOrCancel_clicked )

        self.win.addButton('btnCancel',-5 - 45 - 5 ,-25,45,15,'Cancel'
                      ,actionListenerProc = self.btnOkOrCancel_clicked )

        # Get the object of current document
        desktop=getDesktop()

        doc =desktop.getCurrentComponent()

        docinfo=doc.getDocumentInfo()

        if not docinfo.getUserFieldValue(3) == "":
            self.count=0
            vOpenSearch = doc.createSearchDescriptor()
            vCloseSearch = doc.createSearchDescriptor()
            # Set the text for which to search and other
            vOpenSearch.SearchString = "repeatIn"
            vCloseSearch.SearchString = "')"
            # Find the first open delimiter
            vOpenFound = doc.findFirst(vOpenSearch)
            while not vOpenFound==None:
                #Search for the closing delimiter starting from the open delimiter
                vCloseFound = doc.findNext( vOpenFound.End, vCloseSearch)
                if vCloseFound==None:
                    print "Found an opening bracket but no closing bracket!"
                    break
                else:
                    vOpenFound.gotoRange(vCloseFound, True)
                    self.count += 1
                    vOpenFound = doc.findNext( vOpenFound.End, vOpenSearch)
                #End If
            #End while Loop
            self.insVariable.addItem("Objects(" + docinfo.getUserFieldValue(3) + ")",1)
            self.win.doModalDialog()


        else:

            print "Insert Field-4"

            self.win.endExecute()

    def getDesktop(self):

        localContext = uno.getComponentContext()

        resolver = localContext.ServiceManager.createInstanceWithContext(
                        "com.sun.star.bridge.UnoUrlResolver", localContext )

        smgr = resolver.resolve( "uno:socket,host=localhost,port=2002;urp;StarOffice.ServiceManager" )

        remoteContext = smgr.getPropertyValue( "DefaultContext" )

        desktop = smgr.createInstanceWithContext( "com.sun.star.frame.Desktop",remoteContext)

        return desktop


    def cmbVariable_selected(self,oItemEvent):
        if self.count > 0 :

            sock = xmlrpclib.ServerProxy('http://localhost:8069/xmlrpc/object')

            desktop=getDesktop()

            doc =desktop.getCurrentComponent()

            docinfo=doc.getDocumentInfo()

            self.win.removeListBoxItems("lstFields", 0, self.win.getListBoxItemCount("lstFields"))

            self.genTree(docinfo.getUserFieldValue(3),0,ending=['one2many','many2many'], recur=['many2one'])
        else:

            self.insField.addItem("objects",self.win.getListBoxItemCount("lstFields"))

        #self.genTree(self.win.getComboBoxSelectedText("cmbVariable"),2, , recur=['many2one'])  ending_excl=['many2one'],

    def btnOkOrCancel_clicked( self, oActionEvent ):
        #Called when the OK or Cancel button is clicked.

        if oActionEvent.Source.getModel().Name == "btnOK":

            self.bOkay = True

            desktop=getDesktop()

            doc = desktop.getCurrentComponent()

            text = doc.Text

            cursor = doc.getCurrentController().getViewCursor()


            if self.win.getListBoxSelectedItem("lstFields") != "" and self.win.getEditText("txtName") != "" :
                    sObjName=""
                    if self.win.getListBoxSelectedItem("lstFields") == "objects":

                        text.insertString(cursor,"[[ repeatIn(" + self.win.getListBoxSelectedItem("lstFields") + ",'" + self.win.getEditText("txtName") + "') ]]" , 0 )

                    else:

                        vOpenSearch = doc.createSearchDescriptor()

                        vCloseSearch = doc.createSearchDescriptor()

                        # Set the text for which to search and other
                        vOpenSearch.SearchString = "(objects,'"

                        vCloseSearch.SearchString = "')"
                        print "abc"
                        # Find the first open delimiter
                        vOpenFound = doc.findFirst(vOpenSearch)

                        while not vOpenFound==None:
                            #Search for the closing delimiter starting from the open delimiter

                            vCloseFound = doc.findNext( vOpenFound.End, vCloseSearch)

                            if vCloseFound==None:
                                print "Found an opening bracket but no closing bracket!"
                                break
                            else:
                                vOpenFound.gotoRange(vCloseFound, True)
                                sObjName=vOpenFound.getString()
                                vOpenFound = doc.findNext( vOpenFound.End, vOpenSearch)
                            #End If
                        #End while Loop
                        sObjName=sObjName.__getslice__(10,sObjName.find("')"))

                        if cursor.TextTable==None:
                            text.insertString(cursor,"[[ repeatIn(" + sObjName + self.win.getListBoxSelectedItem("lstFields").replace("/",".") + ",'" + self.win.getEditText("txtName") +"') ]]" , 0 )
                        else:
                            oTable = cursor.TextTable
                            oCurCell = cursor.Cell
                            tableText = oTable.getCellByName( oCurCell.CellName )
                            cursor = tableText.createTextCursor()
                            cursor.gotoEndOfParagraph(True)
                            tableText.setString( "[[ repeatIn(" + sObjName + self.win.getListBoxSelectedItem("lstFields").replace("/",".") + ",'" + self.win.getEditText("txtName") +"') ]]" )


        elif oActionEvent.Source.getModel().Name == "btnCancel":

            self.win.endExecute()
    # this method will featch data from the database and place it in the combobox
    def genTree(self,object,level=3, ending=[], ending_excl=[], recur=[], root=''):

        sock = xmlrpclib.ServerProxy('http://localhost:8069/xmlrpc/object')

        res = sock.execute('terp', 3, 'admin', object , 'fields_get')

        key = res.keys()

        key.sort()

        for k in key:

            if (not ending or res[k]['type'] in ending) and ((not ending_excl) or not (res[k]['type'] in ending_excl)):

                self.insField.addItem(root+'/'+k,self.win.getListBoxItemCount("lstFields"))

            if (res[k]['type'] in recur):
                self.insField.addItem(root+'/'+k,self.win.getListBoxItemCount("lstFields"))

            if (res[k]['type'] in recur) and (level>0):

                self.genTree(res[k]['relation'], level-1, ending, ending_excl, recur, root+'/'+k)

    def getModule(self,oSocket):

        res = oSocket.execute('terp', 3, 'admin', 'ir.model', 'read',
                              [58, 13, 94, 40, 67, 12, 5, 32, 9, 21, 97, 30, 18, 112, 2, 46, 62, 3,
                               19, 92, 8, 1, 105, 49, 70, 96, 50, 47, 53, 42, 95, 43, 71, 72, 64, 73,
                               102, 103, 7, 75, 107, 76, 77, 74, 17, 79, 78, 80, 63, 81, 82, 14, 83,
                               84, 85, 86, 87, 26, 39, 88, 11, 69, 91, 57, 16, 89, 10, 101, 36, 66, 45,
                               54, 106, 38, 44, 60, 55, 25, 4, 51, 65, 109, 34, 33, 52, 61, 28, 41, 59,
                               108, 110, 31, 99, 104, 93, 56, 35, 37, 27, 98, 24, 100, 6, 15, 48, 90,
                               111, 20, 22, 23, 29, 68], ['name','model'],
                               {'active_ids': [57], 'active_id': 57})

        nIndex = 0

        while nIndex <= res.__len__()-1:

            self.insVariable.addItem(res[nIndex]['model'],0)

            nIndex += 1


Repeatln()
