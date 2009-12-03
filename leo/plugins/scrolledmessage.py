
#@+leo-ver=4-thin
#@+node:leohag.20081204085551.1:@thin scrolledmessage.py
#@@first

#@<< docstring >>
#@+node:leohag.20081203143921.2:<< docstring >>
"""
Scrolled Message Dialog
=======================

Provides a Scrolled Message Dialog service for Qt based guis/plugins.

The plugin can display messages supplied as plain text or formated as html. In addition the plugin can accept messages in rst format and convert them to be displayed as html.

The displayed format can be controlled by the user via check boxes, so rst messages may be viewed either as text or as html. Html messages can also be viwed as raw text, which will be a good debug feature when creating complex dynamically generated html messages.

The user interface is provided by a ScrolledMessage.ui file which is dynamically loaded each time a new dialog is loaded.

The dialog is not modal and many dialogs can exist at one time. Dialogs can be named and output directed to a dialog with a specific name.  

The plugin is invoked like this:

    g.doHook('scrolledMessage', c=c, msg='message', title='title',  ...etc    )

or
    g.app.gui.runScrolledMessageDialog(c=c, ...etc)

all parameters are optional except c.

Parameters
----------
    msg:
        The text to be displayed (html, rst, plain).

        If the text starts with 'rst:' it is assumed to be rst text and
        is converted to html for display, (after the rst: prefix has been removed.

        If the text starts with '<' it is assumed to be html.

        These auto detection features can be overridden by 'flags'.

    label:
        The text to appear in a label above the display. If it is '', the label is hidden.

    title:
        The title to appear on the window or dock.

    flags:
        Says what kind of message eg: 'rst', 'text', 'html'. This overrides auto-detection.

        Flags can be combined, eg 'rst html' causes the message to be interpreted as rst and
        displayed as html.

To Do
-----
    - Add parameters to control position, size, closing, hiding etc.

    - Save or print files from the dialog.

    - Add an option to put the dialog in leo's log notebook.

    - Add \@settings to control default behaviour

    - Provide a menu of plugins that allows their docstring to be displayed.

    - Provide a menu of @rst nodes in the current outline, automatically track changes
      if it is set to display any of these nodes.

"""
#@-node:leohag.20081203143921.2:<< docstring >>
#@nl

#@@language python
#@@tabwidth -4
#@@pagewidth 80

controllers = {}
globalPrinter = None

#@<< imports >>
#@+node:leohag.20081203143921.3:<< imports >>
import inspect 

import leo.core.leoGlobals as g
import leo.core.leoPlugins as leoPlugins

try:
    from PyQt4 import QtCore, QtGui, uic
    Qt = QtCore.Qt
except ImportError:
    Qt = None

#@+others
#@-others
#@-node:leohag.20081203143921.3:<< imports >>
#@nl

#@+others
#@+node:leohag.20081203143921.4:init
def init():

    ok = g.app.gui.guiName().startswith("qt")
    if ok:
        leoPlugins.registerHandler(('open2','new'), onCreate)
        leoPlugins.registerHandler('scrolledMessage', scrolledMessageHandler)
        leoPlugins.registerHandler('scrolledMessage', selectHandler)

        g.plugin_signon(__name__)

    return ok
#@-node:leohag.20081203143921.4:init
#@+node:leohag.20081203143921.5:onCreate
def onCreate (tag,key):

    c = key.get('c')
    if c and c.exists and c not in controllers:
        controllers[c] = ScrolledMessageController(c) 

#@-node:leohag.20081203143921.5:onCreate
#@+node:leohag.20081206052547.20:globalGetPrinter
def getGlobalPrinter():
    global globalPrinter

    if not globalPrinter:
        globalPrinter = QtGui.QPrinter()
    return globalPrinter
#@-node:leohag.20081206052547.20:globalGetPrinter
#@+node:leohag.20081203143921.6:scrolledMessageHandler
def scrolledMessageHandler(tag, keywords):

    c = keywords.get('c')
    if  c in controllers:
        return controllers[c].scrolledMessageHandler(tag, keywords)
#@nonl
#@-node:leohag.20081203143921.6:scrolledMessageHandler
#@+node:leohag.20081207032616.20:selectHandler
def selectHandler(tag, keywords):

    c = keywords.get('c')
    if  c in controllers:
        return controllers[c].selectHandler(tag, keywords)
#@nonl
#@-node:leohag.20081207032616.20:selectHandler
#@+node:leohag.20081207032616.18:safe
def safe(msg):
    return msg.replace('&','&amp;').replace('<', '&lt;').replace('>', '&gt;')
#@nonl
#@-node:leohag.20081207032616.18:safe
#@+node:leohag.20081203143921.9:class ScrolledMessageDialog
class ScrolledMessageDialog(object):

    # 'labels' with no sub menu are the names of actions without the 'action' prefix
    # eg ('Save', None) refers to actionSave

    menuList = [
        ('File', [
            ('Save', None),
            ('', None),
            ('PageSetup', None),
            ('PrintPreview', None),
            ('PrintDialog', None),
        ]),
        ('Outline',[
            ('OutlineShow', None),
            ('RST3', None),
            ('', None),
            ('OutlineThisNode', None),
            ('OutlineExpandFollowsTree', None),
            ('OutlineIncludeBody', None),
        ]),
        ('Help', [
            ('About', None),
        ])
    ]

    #@    @+others
    #@+node:leohag.20081203210510.1:__init__
    def __init__(self, parent, kw ):

        self.parent = parent
        self.c = parent.c
        self.ui = self.getGui()(self)

        self.createMenuBar()

        top = self.c.frame.top
        self.dock = dock = QtGui.QDockWidget("Scrolled Message Dialog", top)
        dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        dock.setWidget(self.ui)
        dock.resize(400, 500)

        top.addDockWidget(Qt.RightDockWidgetArea, dock)

        dock.setFloating(False)

        self.controls = {}
        self.controlFlags = {}

        self.findChkControls()
        self.chkBtnChanged(silent=True)

        self.updateDialog(kw)
        self.ui.show()
    #@-node:leohag.20081203210510.1:__init__
    #@+node:leohag.20081206052547.14:Action Handlers (slots)
    #@+node:leohag.20081206052547.35:File Menu
    #@+node:leohag.20081206052547.19:_print
    def _print(self, printer):
        g.trace( printer)
        self.ui.leo_webView.print_(printer)

    #@-node:leohag.20081206052547.19:_print
    #@+node:leohag.20081206052547.21:PageSetup
    def doActionPageSetup(self, checked):

        dialog = QtGui.QPageSetupDialog(getGlobalPrinter(), self.ui)
        dialog.exec_()


    #@-node:leohag.20081206052547.21:PageSetup
    #@+node:leohag.20081206052547.15:Print
    def doActionPrint(self, checked):
        self._print(getGlobalPrinter())
    #@nonl
    #@-node:leohag.20081206052547.15:Print
    #@+node:leohag.20081206052547.24:PrintDialog
    def doActionPrintDialog(self, checked):
        #g.trace()
        dialog = QtGui.QPrintDialog(getGlobalPrinter(),self.ui)
        if dialog.exec_() == QtGui.QDialog.Accepted:
            self._print(getGlobalPrinter())
    #@nonl
    #@-node:leohag.20081206052547.24:PrintDialog
    #@+node:leohag.20081206052547.23:PrintPreview
    def doActionPrintPreview(self, checked):
        g.trace()
        dialog = QtGui.QPrintPreviewDialog(getGlobalPrinter(),self.ui)
        dialog.connect(dialog, QtCore.SIGNAL('paintRequested(QPrinter*)'), self._print )
        dialog.exec_()
    #@-node:leohag.20081206052547.23:PrintPreview
    #@+node:leohag.20081206052547.16:Save
    def doActionSave(self):
        g.trace()

        result = g.app.gui.runSaveFileDialog()
        g.es(result)
        if result:
            f = open(result, 'wb')
            f.write(self.convertMessage().encode('utf-8'))
            f.close()

    #@-node:leohag.20081206052547.16:Save
    #@-node:leohag.20081206052547.35:File Menu
    #@+node:leohag.20081206052547.27:Outline Menu
    #@+node:leohag.20081206052547.28:Show
    def doActionOutlineShow(self, checked):

        import leo.plugins.leo_to_html as html

        node = self.ui.actionOutlineThisNode.isChecked()
        self._includeBody = self.ui.actionOutlineIncludeBody.isChecked()
        self._expandFollowsTree  = self.ui.actionOutlineExpandFollowsTree.isChecked()

        html = []

        html.append('<ol>')

        if node:
            root = self.c.currentPosition()
            self.doNextLevel(root, html)
        else:
            root = self.c.rootPosition()
            for pp in root.following_siblings():
                self.doNextLevel(pp, html)

        html.append('</ol>')

        #@    << msg = html carcass>>
        #@+node:leohag.20081207032616.16:<< msg = html carcass>>
        msg = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
        <head>
        <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
        <title>
            %s
        </title>
        </head>
        <body>
        %s
        </body></html>
        """
        #@-node:leohag.20081207032616.16:<< msg = html carcass>>
        #@nl
        #@    << label = filename >>
        #@+node:leohag.20081207032616.19:<< label = filename >>
        label = self.c.frame.shortFileName()
        if not label:
            label = 'untitiled'
        #@nonl
        #@-node:leohag.20081207032616.19:<< label = filename >>
        #@nl

        msg = msg % (label, '\n'.join(html))

        g.doHook('scrolledMessage', c=self.c, name=self.name, msg=msg, label=label, flags='html')
    #@+node:leohag.20081207032616.17:doNextLevel
    def doNextLevel(self, p, html):
        """" Recursivley proccess an outline node into an html list."""

        html.append('<li>')
        html.append(safe(p.headString())) 

        if self._includeBody:
            html.append('<div><pre>%s</pre></div>'%safe(p.bodyString()))

        if p.hasChildren() and (p.isExpanded() or not self._expandFollowsTree):

            html.append('<ol>')
            for item in p.children():
                self.doNextLevel(item, html)
            html.append('</ol>')

        html.append('</li>')


    #@-node:leohag.20081207032616.17:doNextLevel
    #@-node:leohag.20081206052547.28:Show
    #@-node:leohag.20081206052547.27:Outline Menu
    #@+node:leohag.20081206052547.36:Help Menu
    #@+node:leohag.20081206052547.17:About
    def doActionAbout(self, checked):
        g.trace()
        pass
    #@nonl
    #@-node:leohag.20081206052547.17:About
    #@-node:leohag.20081206052547.36:Help Menu
    #@+node:leohag.20081207032616.24:RST3
    def doActionRST3(self, checked):

        rst3 = leoPlugins.getPluginModule('rst3')

        if not rst3:
            rst3 = leoPlugins.loadOnePlugin('rst3',verbose=True)
            if rst3:
                g.es('rst3 loaded')
                rst3.onCreate('tag',{'c':self.c})

        if rst3:
            controller = rst3.controllers.get(self.c)
            if controller:
                g.doHook('scrolledMessage', c=self.c, msg='loading..', flags='text')
                p,s = controller.writeNodeToString(ext='.html')
                g.doHook('scrolledMessage', c=self.c, msg=s, flags='html')
    #@-node:leohag.20081207032616.24:RST3
    #@-node:leohag.20081206052547.14:Action Handlers (slots)
    #@+node:leohag.20081206052547.12:Menu Bar
    #@+node:leohag.20081206052547.34:createMenuBar
    def createMenuBar(self):

        self.menubar = mb = QtGui.QMenuBar(self.ui)

        for title, subMenu in self.menuList:
            menu = self.createSubMenu(mb, title, subMenu)
            mb.addMenu(menu)

        self.ui.leo_menubar_frame.layout().insertWidget(0, mb)
        mb.show()

    #@-node:leohag.20081206052547.34:createMenuBar
    #@+node:leohag.20081206052547.13:createSubMenu
    def createSubMenu(self, parent, title, menuList):

        #g.trace(title, menuList)

        menu = QtGui.QMenu(title, parent)
        for subTitle, subList in menuList:

            if subList:
                submenu = self.createSubMenu(menu, subTitle, subList)
                menu.addMenu(submenu)
            elif subTitle:
                #< < find and bind action >>

                action = getattr(self.ui, 'action%s'%subTitle, None)
                if action:
                    method = getattr(self, 'doAction%s'%subTitle, None)
                    if method: 
                        action.connect(action, QtCore.SIGNAL('triggered(bool)'), method)
                    menu.addAction(action)
            else:
                menu.addSeparator()

        return menu
    #@-node:leohag.20081206052547.13:createSubMenu
    #@-node:leohag.20081206052547.12:Menu Bar
    #@+node:leohag.20081203143921.24:getUiPath
    def getUiPath(self):

        return g.os_path_join(g.app.loadDir,'..','plugins', 'ScrolledMessage.ui')
    #@nonl
    #@-node:leohag.20081203143921.24:getUiPath
    #@+node:leohag.20081203143921.22:Create User Interface
    def getGui(self):

        form_class, base_class = uic.loadUiType(self.getUiPath())
        #@    << define class Base_UI>>
        #@+node:leohag.20081203143921.23:<<define class Base_UI>>
        class Base_UI(QtGui.QWidget, form_class):
            """Class to wrap QDesigner ui object and provide glue code to make it work."""

            def __init__(self, parent, *args):
                QtGui.QWidget.__init__(self, *args)
                self.leoParent = parent
                #@        << inject action callbacks >>
                #@+node:leohag.20081206052547.18:<< inject action callbacks >>
                #@+at
                # for name, method in inspect.getmembers(self.leoParent):
                #     if name.startswith('doAction'):
                #         def doAction(self, name=name):
                #             getattr(self.leoParent, name)()
                #         setattr(self.__class__, name, doAction)
                # 
                #@-at
                #@-node:leohag.20081206052547.18:<< inject action callbacks >>
                #@nl
                self.setupUi(self)

            def chkBtnChanged(self):
                self.leoParent.chkBtnChanged()

            def closeEvent(self, event):
                self.leoParent.closeMe(event)
        #@-node:leohag.20081203143921.23:<<define class Base_UI>>
        #@nl
        return Base_UI
    #@-node:leohag.20081203143921.22:Create User Interface
    #@+node:leohag.20081203205020.1:closeMe
    def closeMe(self, visible):
            self.parent.onDialogClosing(self)
            self.dock.destroy()

            print(self.dock)
            print(self.ui)

    #@-node:leohag.20081203205020.1:closeMe
    #@+node:leohag.20081203143921.10:findChkControls
    def findChkControls(self):
        s = 'leo_chk_'; ls = len(s)
        for k, v in self.ui.__dict__.iteritems():
            if k.startswith(s):
                self.controls[k[ls:]] = v

    #@-node:leohag.20081203143921.10:findChkControls
    #@+node:leohag.20081203143921.11:setFlagsFromControls
    def setFlagsFromControls(self):
        for flag, control in self.controls.iteritems():
            self.controlFlags[flag] = bool(control.isChecked())

    #@-node:leohag.20081203143921.11:setFlagsFromControls
    #@+node:leohag.20081203143921.12:setControlsFromFlags
    def setControlsFromFlags(self):
        for flag, value in self.controlFlags.iteritems():
            self.controls[flag].setChecked(bool(value))

    #@-node:leohag.20081203143921.12:setControlsFromFlags
    #@+node:leohag.20081203143921.13:chkBtnClhanged
    def  chkBtnChanged(self,silent=False):
        self.setFlagsFromControls()
        if not silent:
            self.showMessage()

    #@-node:leohag.20081203143921.13:chkBtnClhanged
    #@+node:leohag.20081203143921.14:showMessage
    def showMessage(self, show=True):

        html = self.convertMessage()

        self.ui.leo_webView.setHtml(html)

        if show:
            self.dock.show()
            toggle = self.dock.toggleViewAction()
            toggle.setChecked(True)
    #@-node:leohag.20081203143921.14:showMessage
    #@+node:leohag.20081206052547.37:convertMessage
    def convertMessage(self):

        msg = self.msg
        f = self.controlFlags
        if f['html']:
            if f['rst']:
                msg = self.rstToHtml(msg)
            if f['text']:
                msg = self.textToHtml(msg)
        else:
            msg = self.textToHtml(msg)

        return msg

    #@-node:leohag.20081206052547.37:convertMessage
    #@+node:leohag.20081203143921.15:rstToHtml
    def rstToHtml( self, rst):

        try:
            from docutils import core
        except ImportError:
            g.es('scrolledMessage: Can not import docutils', color='blue')
            return self.textToHtml(rst)

        overrides = {
            'doctitle_xform': False,
            'initial_header_level': 1
        }

        try:
            parts = core.publish_parts(
                source= rst,
                writer_name='html',
                settings_overrides=overrides
            )
        except Exception:
            g.es('scrolledMessage: rst conversion error', color='blue')
            return self.textToHtml(rst)

        return parts['whole']

    #@-node:leohag.20081203143921.15:rstToHtml
    #@+node:leohag.20081203143921.16:textToHtml
    def textToHtml(self, msg):

        return '<pre>%s<pre>'%safe(msg)



    #@-node:leohag.20081203143921.16:textToHtml
    #@+node:leohag.20081203143921.17:updateDialog
    def updateDialog(self, kw):

        # update ivars
        for k in list(kw.keys()):
            setattr(self, k, kw[k])

        if not isinstance(self.msg, basestring):
            self.msg = '<h2 style="color:red" >Illegal! Message must be string.</h2>'
            self.flags = 'html'

        # auto detect message type
        if not self.flags.strip():
            self.flags = 'text'
            if self.msg.startswith('rst:'):
                self.flags = 'rst html'
                self.msg = self.msg[4:]
            elif self.msg.startswith('<'):
                self.flags = 'html'

        flags = self.flags.split(' ')
        if 'rst' in flags and 'text' not in flags:
            flags.append('html')

        # update the ui check box controls
        ff = self.controlFlags 

        for flag in list(ff.keys()):
            if flag in flags:
                ff[flag] = True
            else:
                ff[flag] = False

        self.setControlsFromFlags()

        # update label
        w = self.ui.leo_topLabel
        if self.label:
            w.setText(self.label)
            w.show()
        else:
            w.hide()

        #update title
        self.dock.setWindowTitle(self.title)

        self.showMessage()
    #@-node:leohag.20081203143921.17:updateDialog
    #@+node:leohag.20081207032616.23:afterDrawHandler
    def afterDrawHandler():

        pass
        #if self.ui.actionFollowOutline
    #@-node:leohag.20081207032616.23:afterDrawHandler
    #@+node:leohag.20081203143921.18:show
    def show(self):
        self.ui.show()
    #@nonl
    #@-node:leohag.20081203143921.18:show
    #@-others

#@-node:leohag.20081203143921.9:class ScrolledMessageDialog
#@+node:leohag.20081203143921.19:class ScrolledMessageController
class ScrolledMessageController(object):


    kwDefaults = {'msg':'', 'flags':'', 'name':'', 'title':'Leo Message', 'label':''}

    #@    @+others
    #@+node:leohag.20081206052547.1:__init__
    def __init__(self, c):

        self.dialogs = {}
        self.usedNames = set()

        self.c = c
    #@-node:leohag.20081206052547.1:__init__
    #@+node:leohag.20081203143921.20:updateDialog
    def updateDialog(self, kw):

        # print(self.c, self.dialogs)

        if  not kw['name']:
            # name = self.getUniqueName()
            name = 'leo_system'
            kw['name'] = name

        if kw['name'] not in self.dialogs:
            self.createDialog(kw)
        else:
            self.dialogs[kw['name']].updateDialog(kw)

    #@-node:leohag.20081203143921.20:updateDialog
    #@+node:leohag.20081203143921.21:createDialog
    def createDialog(self, kw):

        self.dialogs[kw['name']] = ScrolledMessageDialog(self, kw)
        self.usedNames.add(kw['name'])

    #@-node:leohag.20081203143921.21:createDialog
    #@+node:leohag.20081203143921.25:getUniqueName
    def getUniqueName(self):

        count = 0
        while True:
            count += 1
            name = 'ScrolledMessage_%s'%count
            if name not in self.usedNames:
                return name


    #@-node:leohag.20081203143921.25:getUniqueName
    #@+node:leohag.20081203143921.26:scrolledMessageHandler
    def scrolledMessageHandler(self, tag, keywords):   

        for k, v in self.kwDefaults.iteritems():
            if k not in keywords:
                keywords[k] = v 

        #g.trace(keywords)
        self.updateDialog(keywords)

        return keywords

    #@-node:leohag.20081203143921.26:scrolledMessageHandler
    #@+node:leohag.20081207032616.21:afterRedrawHandler
    def afterRedrawHandler(self, tag, keywords):   

        for name, dialog in dialogs:
            self.afterRedrawHandler()
    #@-node:leohag.20081207032616.21:afterRedrawHandler
    #@+node:leohag.20081203210510.3:onDialogClosing
    def onDialogClosing(self, dialog):

        del self.dialogs[dialog.name]

    #@-node:leohag.20081203210510.3:onDialogClosing
    #@-others

#@-node:leohag.20081203143921.19:class ScrolledMessageController
#@-others
#@-node:leohag.20081204085551.1:@thin scrolledmessage.py
#@-leo
