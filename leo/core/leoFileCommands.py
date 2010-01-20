#@+leo-ver=4-thin
#@+node:ekr.20031218072017.3018:@thin leoFileCommands.py
#@@language python
#@@tabwidth -4
#@@pagewidth 80

#@<< imports >>
#@+node:ekr.20050405141130:<< imports >> (leoFileCommands)
import leo.core.leoGlobals as g

if g.app and g.app.use_psyco:
    # g.pr("enabled psyco classes",__file__)
    try: from psyco.classes import *
    except ImportError: pass

import leo.core.leoNodes as leoNodes

import binascii

if g.isPython3:
    import io # Python 3.x
    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:
    import cStringIO # Python 2.x
    StringIO = cStringIO.StringIO

import os
import pickle
import string
import sys
import tempfile
import types
import zipfile

try:
    # IronPython has problems with this.
    import xml.sax
    import xml.sax.saxutils
except Exception:
    pass

# The following is sometimes used.
# import time
#@-node:ekr.20050405141130:<< imports >> (leoFileCommands)
#@nl

#@<< define exception classes >>
#@+node:ekr.20060918164811:<< define exception classes >>
class BadLeoFile(Exception):
    def __init__(self, message):
        self.message = message
        Exception.__init__(self,message) # Init the base class.
    def __str__(self):
        return "Bad Leo File:" + self.message

class invalidPaste(Exception):
    pass
#@nonl
#@-node:ekr.20060918164811:<< define exception classes >>
#@nl

if sys.platform != 'cli':
    #@    << define sax classes >>
    #@+node:ekr.20060919145406:<< define sax classes >>
    #@+others
    #@+node:ekr.20060919110638.19:class saxContentHandler (XMLGenerator)
    class saxContentHandler (xml.sax.saxutils.XMLGenerator):

        '''A sax content handler class that reads Leo files.'''

        #@    @+others
        #@+node:ekr.20060919110638.20: __init__ & helpers
        def __init__ (self,c,fileName,silent,inClipboard):

            self.c = c
            self.fileName = fileName
            self.silent = silent
            self.inClipboard = inClipboard

            # Init the base class.
            xml.sax.saxutils.XMLGenerator.__init__(self)

            #@    << define dispatch dict >>
            #@+node:ekr.20060919110638.21:<< define dispatch dict >>
            # There is no need for an 'end' method if all info is carried in attributes.

            self.dispatchDict = {
                'change_string':               (None,None),
                'find_panel_settings':         (None,None),
                'find_string':                 (None,None),
                'globals':                     (self.startGlobals,None),
                'global_log_window_position':  (None,None), # The position of the log window is no longer used.
                'global_window_position':      (self.startWinPos,None),
                'leo_file':                    (None,None),
                'leo_header':                  (self.startLeoHeader,None),
                'preferences':                 (None,None),
                't':                           (self.startTnode,self.endTnode),
                'tnodes':                      (None,None),
                'v':                           (self.startVnode,self.endVnode),
                'vh':                          (self.startVH,self.endVH),
                'vnodes':                      (self.startVnodes,None), # Causes window to appear.
            }
            #@nonl
            #@-node:ekr.20060919110638.21:<< define dispatch dict >>
            #@nl

            self.printElements = [] # 'all', 'v'

            # Global attributes of the .leo file...
            # self.body_outline_ratio = '0.5'
            self.global_window_position = {}
            self.encoding = 'utf-8' 

            # Semantics...
            self.content = None
            self.elementStack = []
            self.errors = 0
            self.tnxToListDict = {} # Keys are tnx's (strings), values are *lists* of saxNodeClass objects.
            self.level = 0
            self.node = None
            self.nodeList = [] # List of saxNodeClass objects with the present vnode.
            self.nodeStack = []
            self.rootNode = None # a sax node.
        #@nonl
        #@-node:ekr.20060919110638.20: __init__ & helpers
        #@+node:ekr.20060919110638.29: Do nothing
        def endElementNS(self,unused_name,unused_qname):
            g.trace(unused_name)

        def endDocument(self):
            pass

        def ignorableWhitespace(self,unused_whitespace):
            pass

        def skippedEntity(self,name):
            g.trace(name)

        def startElementNS(self,unused_name,unused_qname,unused_attrs):
            g.trace(unused_name)

        def startDocument(self):
            pass
        #@nonl
        #@-node:ekr.20060919110638.29: Do nothing
        #@+node:ekr.20060919134313: Utils
        #@+node:ekr.20060919110638.23:attrsToList
        def attrsToList (self,attrs):

            '''Convert the attributes to a list of g.Bunches.

            attrs: an Attributes item passed to startElement.'''

            # if 0: # check for non-unicode attributes.
                # for name in attrs.getNames():
                    # val = attrs.getValue(name)
                    # if type(val) != type(u''):
                    #    g.trace('Non-unicode attribute',name,val)

            # g.trace(g.listToString([repr(z) for z in attrs.getNames()]))

            return [
                g.Bunch(name=name,val=attrs.getValue(name))
                    for name in attrs.getNames()]
        #@nonl
        #@-node:ekr.20060919110638.23:attrsToList
        #@+node:ekr.20060919110638.26:error
        def error (self, message):

            g.pr('\n\nXML error: %s\n' % (message))

            self.errors += 1
        #@nonl
        #@-node:ekr.20060919110638.26:error
        #@+node:ekr.20060919110638.27:inElement
        def inElement (self,name):

            return self.elementStack and name in self.elementStack
        #@nonl
        #@-node:ekr.20060919110638.27:inElement
        #@+node:ekr.20060919110638.28:printStartElement
        def printStartElement(self,name,attrs):

            indent = '\t' * self.level or ''

            if attrs.getLength() > 0:
                g.pr('%s<%s %s>' % (
                    indent,
                    self.clean(name).strip(),
                    self.attrsToString(attrs,sep=' ')),
                    newline=False)
            else:
                g.pr('%s<%s>' % (
                    indent,
                    self.clean(name).strip()),
                    newline=False)

            if name.lower() in ['v','t','vnodes','tnodes',]:
                g.pr('')
        #@nonl
        #@+node:ekr.20060919110638.24:attrsToString
        def attrsToString (self,attrs,sep='\n'):

            '''Convert the attributes to a string.

            attrs: an Attributes item passed to startElement.

            sep: the separator charater between attributes.'''

            result = [
                '%s="%s"' % (bunch.name,bunch.val)
                for bunch in self.attrsToList(attrs)
            ]

            return sep.join(result)
        #@nonl
        #@-node:ekr.20060919110638.24:attrsToString
        #@+node:ekr.20060919110638.25:clean
        def clean(self,s):

            return g.toEncodedString(s,"ascii")
        #@nonl
        #@-node:ekr.20060919110638.25:clean
        #@-node:ekr.20060919110638.28:printStartElement
        #@-node:ekr.20060919134313: Utils
        #@+node:ekr.20060919110638.30:characters
        def characters(self,content):

            if g.isPython3:
                if content and type(content) != type('a'):
                    g.trace('Non-unicode content',repr(content))
            else:
                if content and type(content) != types.UnicodeType:
                    g.trace('Non-unicode content',repr(content))

            content = content.replace('\r','')
            if not content: return

            elementName = self.elementStack and self.elementStack[-1].lower() or '<no element name>'

            if elementName in ('t','vh'):
                # if elementName == 'vh': g.trace(elementName,repr(content))
                self.content.append(content)

            elif content.strip():
                g.pr('unexpected content:',elementName,repr(content))
        #@-node:ekr.20060919110638.30:characters
        #@+node:ekr.20060919110638.31:endElement & helpers
        def endElement(self,name):

            name = name.lower()

            if name in self.printElements or 'all' in self.printElements:
                indent = '\t' * (self.level-1) or ''
                g.pr('%s</%s>' % (indent,self.clean(name).strip()))

            data = self.dispatchDict.get(name)

            if data is None:
                if 1: g.trace('unknown end element',name)
            else:
                junk,func = data
                if func:
                    func()

            name2 = self.elementStack.pop()
            assert name == name2
        #@nonl
        #@+node:ekr.20060919110638.32:endTnode
        def endTnode (self):

            for sax_node in self.nodeList:
                sax_node.bodyString = ''.join(self.content)

            self.content = []
        #@nonl
        #@-node:ekr.20060919110638.32:endTnode
        #@+node:ekr.20060919110638.33:endVnode
        def endVnode (self):

            self.level -= 1
            self.node = self.nodeStack.pop()
        #@nonl
        #@-node:ekr.20060919110638.33:endVnode
        #@+node:ekr.20060919110638.34:endVH
        def endVH (self):

            if self.node:
                self.node.headString = ''.join(self.content)
                # g.trace(self.node.headString)

            self.content = []
        #@nonl
        #@-node:ekr.20060919110638.34:endVH
        #@-node:ekr.20060919110638.31:endElement & helpers
        #@+node:ekr.20060919110638.45:getRootNode
        def getRootNode (self):
            return self.rootNode
        #@-node:ekr.20060919110638.45:getRootNode
        #@+node:ekr.20061004054323:processingInstruction (stylesheet)
        def processingInstruction (self,target,data):

            if target == 'xml-stylesheet':
                self.c.frame.stylesheet = data
                if False and not self.silent:
                    g.es('','%s: %s' % (target,data),color='blue')
            else:
                g.trace(target,data)
        #@nonl
        #@-node:ekr.20061004054323:processingInstruction (stylesheet)
        #@+node:ekr.20060919110638.35:startElement & helpers
        def startElement(self,name,attrs):

            name = name.lower()

            if name in self.printElements or 'all' in self.printElements:
                self.printStartElement(name,attrs)

            self.elementStack.append(name)

            data = self.dispatchDict.get(name)

            if data is None:
                if 1: g.trace('unknown start element',name)
            else:
                func,junk = data
                if func:
                    func(attrs)
        #@nonl
        #@+node:ekr.20060919110638.36:getPositionAttributes
        def getPositionAttributes (self,attrs):

            trace = False and not g.unitTesting
            c = self.c

            if trace: g.trace(len(list(c.db.keys())),c.mFileName,self.fileName)

            d = {}

            if g.enableDB and c.db and c.mFileName:
                key = c.atFileCommands._contentHashFile(c.mFileName,'globals')
                data = c.db.get('window_position_%s' % (key))
                if data:
                    top,left,height,width = data
                    top,left,height,width = int(top),int(left),int(height),int(width)
                    d = {'top':top,'left':left,'height':height,'width':width}

            if not d and c.fixed and c.fixedWindowPosition:
                width,height,left,top = c.fixedWindowPosition
                d = {'top':top,'left':left,'width':width,'height':height}

            if not d:
                for bunch in self.attrsToList(attrs):
                    name = bunch.name ; val = bunch.val
                    if name in ('top','left','width','height'):
                        try:
                            d[name] = int(val)
                        except ValueError:
                            d[name] = 100 # A reasonable default.
                    else:
                        g.trace(name,len(val))

            # if trace: g.trace(d)
            return d
        #@-node:ekr.20060919110638.36:getPositionAttributes
        #@+node:ekr.20060919110638.37:startGlobals
        def startGlobals (self,attrs):

            trace = False and not g.unitTesting
            c = self.c

            if self.inClipboard:
                return

            c.frame.ratio,c.frame.secondary_ratio = 0.5,0.5 # Set defaults.

            if trace: g.trace(len(list(c.db.keys())),c.mFileName)

            if g.enableDB and c.db and c.mFileName:
                key = c.atFileCommands._contentHashFile(c.mFileName,'globals')
                c.frame.ratio = float(c.db.get(
                    'body_outline_ratio_%s' % (key),'0.5'))
                c.frame.secondary_ratio = float(c.db.get(
                    'body_secondary_ratio_%s' % (key),'0.5'))
                if trace: g.trace('key',key,
                    '%1.2f %1.2f' % (c.frame.ratio,c.frame.secondary_ratio))
            else:
                try:
                    for bunch in self.attrsToList(attrs):
                        name = bunch.name ; val = bunch.val
                        if name == 'body_outline_ratio':
                            c.frame.ratio = float(val) # 2010/01/11
                        elif name == 'body_secondary_ratio':
                            c.frame.secondary_ratio = float(val) # 2010/01/11
                    if trace: g.trace('** no c.db:','%1.2f %1.2f' % (
                        c.frame.ratio,c.frame.secondary_ratio))
                except Exception:
                    pass
        #@-node:ekr.20060919110638.37:startGlobals
        #@+node:ekr.20060919110638.38:startWinPos
        def startWinPos (self,attrs):

            self.global_window_position = self.getPositionAttributes(attrs)
        #@-node:ekr.20060919110638.38:startWinPos
        #@+node:ekr.20060919110638.39:startLeoHeader
        def startLeoHeader (self,unused_attrs):

            self.tnxToListDict = {}
        #@-node:ekr.20060919110638.39:startLeoHeader
        #@+node:ekr.20060919110638.40:startVH
        def startVH (self,unused_attrs):

            self.content = []
        #@nonl
        #@-node:ekr.20060919110638.40:startVH
        #@+node:ekr.20060919112118:startVnodes
        def startVnodes (self,unused_attrs):

            if self.inClipboard:
                return # No need to do anything to the main window.

            c = self.c ; d = self.global_window_position

            w = d.get('width',700)
            h = d.get('height',500)
            x = d.get('left',50)
            y = d.get('top',50)
            # g.trace(d,w,h,x,y)

            # Redraw the window before writing into it.
            c.frame.setTopGeometry(w,h,x,y)
            c.frame.deiconify()
            c.frame.lift()
            c.frame.update()

            # Causes window to appear.
            # g.trace('ratio',c.frame.ratio,c)
            c.frame.resizePanesToRatio(c.frame.ratio,c.frame.secondary_ratio)
            if not self.silent and not g.unitTesting:
                g.es("reading:",self.fileName)
        #@-node:ekr.20060919112118:startVnodes
        #@+node:ekr.20060919110638.41:startTnode
        def startTnode (self,attrs):

            if not self.inElement('tnodes'):
                self.error('<t> outside <tnodes>')

            self.content = []

            self.tnodeAttributes(attrs)
        #@nonl
        #@+node:ekr.20060919110638.42:tnodeAttributes
        def tnodeAttributes (self,attrs):

            # The vnode must have a tx attribute to associate content
            # with the proper node.

            trace = False and not g.unitTesting
            verbose = False
            node = self.node
            self.nodeList = []
            val = None

            # Step one: find the tx attribute
            for bunch in self.attrsToList(attrs):
                name = bunch.name ; val = bunch.val
                if name == 'tx':
                    if g.unitTesting:
                        self.nodeList = [saxNodeClass()] # For pylint.
                    else:
                        self.nodeList = self.tnxToListDict.get(val,[])
                    if trace and verbose: g.trace('tx',self.nodeList)
                    break

            if not self.nodeList:
                self.error('Bad leo file: no node for <t tx=%s>' % (val))
                return

            # Step two: find all the other attributes:
            for bunch in self.attrsToList(attrs):
                name = bunch.name ; val = bunch.val
                if name != 'tx':
                    # Huge bug fix: 2009/7/1: was node == self.node.
                    for node in self.nodeList:
                        if trace: g.trace('%s %s=%s...' % (node,name,val[:20]))
                        node.tnodeAttributes[name] = val

            # if not self.nodeList:
                # self.error('Bad leo file: no tx attribute for vnode')
        #@+node:ekr.20090702072557.6449:@test tnodeAttributes
        if g.unitTesting:

            import leo.core.leoFileCommands as leoFileCommands
            c,p = g.getTestVars()

            class saxAttrsClass:
                '''Simulating sax attributes'''
                def __init__(self):
                    self.attrs = {
                        'tx':'ekr.123','testAttr':'abc',
                    }
                def getNames(self):
                    return list(self.attrs.keys())
                def getValue(self,key):
                    return self.attrs.get(key)

            handler = leoFileCommands.saxContentHandler(
                c,fileName='<test file>',
                silent=True,inClipboard=False)
            attributes = saxAttrsClass()
            handler.tnodeAttributes(attributes)
            aList = handler.nodeList
            assert len(aList) == 1,len(aList)
            b = aList[0]
            d = b.tnodeAttributes
            assert d.get('testAttr')=='abc',d.get('testAttr')
        #@nonl
        #@-node:ekr.20090702072557.6449:@test tnodeAttributes
        #@-node:ekr.20060919110638.42:tnodeAttributes
        #@-node:ekr.20060919110638.41:startTnode
        #@+node:ekr.20060919110638.43:startVnode
        def startVnode (self,attrs):

            if not self.inElement('vnodes'):
                self.error('<v> outside <vnodes>')

            if self.rootNode:
                parent = self.node
            else:
                self.rootNode = parent = saxNodeClass() # The dummy parent node.
                parent.headString = 'dummyNode'

            self.node = saxNodeClass()

            parent.children.append(self.node)
            self.vnodeAttributes(attrs)
            self.nodeStack.append(parent)

            return parent
        #@nonl
        #@+node:ekr.20060919110638.44:vnodeAttributes
        # The native attributes of <v> elements are a, t, vtag, tnodeList,
        # marks, expanded and descendentTnodeUnknownAttributes.

        def vnodeAttributes (self,attrs):

            node = self.node

            for bunch in self.attrsToList(attrs):
                name = bunch.name ; val = bunch.val
                if name == 't':
                    aList = self.tnxToListDict.get(val,[])
                    aList.append(self.node)
                    self.tnxToListDict[val] = aList
                    node.tnx = str(val) # nodeIndices.toString returns a string.
                else:
                    node.attributes[name] = val
        #@nonl
        #@-node:ekr.20060919110638.44:vnodeAttributes
        #@-node:ekr.20060919110638.43:startVnode
        #@-node:ekr.20060919110638.35:startElement & helpers
        #@-others
    #@nonl
    #@-node:ekr.20060919110638.19:class saxContentHandler (XMLGenerator)
    #@+node:ekr.20060919110638.15:class saxNodeClass
    class saxNodeClass:

        '''A class representing one <v> element.

        Use getters to access the attributes, properties and rules of this mode.'''

        #@    @+others
        #@+node:ekr.20060919110638.16: node.__init__
        def __init__ (self):

            self.attributes = {}
            self.bodyString = ''
            self.headString = ''
            self.children = []
            self.tnodeAttributes = {}
            self.tnodeList = []
            self.tnx = None
        #@nonl
        #@-node:ekr.20060919110638.16: node.__init__
        #@+node:ekr.20060919110638.17: node.__str__ & __repr__
        def __str__ (self):

            return '<v: %s>' % self.headString

        __repr__ = __str__
        #@nonl
        #@-node:ekr.20060919110638.17: node.__str__ & __repr__
        #@+node:ekr.20060919110638.18:node.dump
        def dump (self):

            g.pr('\nnode: tnx: %s len(body): %d %s' % (
                self.tnx,len(self.bodyString),self.headString))
            g.pr('children:',g.listToString(self.children))
            g.pr('attrs:',list(self.attributes.values()))
        #@nonl
        #@-node:ekr.20060919110638.18:node.dump
        #@-others
    #@nonl
    #@-node:ekr.20060919110638.15:class saxNodeClass
    #@-others
    #@nonl
    #@-node:ekr.20060919145406:<< define sax classes >>
    #@nl

class baseFileCommands:
    """A base class for the fileCommands subcommander."""
    #@    @+others
    #@+node:ekr.20090218115025.4:Birth
    #@+node:ekr.20031218072017.3019:leoFileCommands._init_
    def __init__(self,c):

        # g.trace("__init__", "fileCommands.__init__")
        self.c = c
        self.frame = c.frame

        self.nativeTnodeAttributes = ('tx',)
        self.nativeVnodeAttributes = (
            'a',
            'descendentTnodeUnknownAttributes',
            'descendentVnodeUnknownAttributes', # New in Leo 4.5.
            'expanded','marks','t','tnodeList',
            # 'vtag',
        )

        self.checkOutlineBeforeSave = c.config.getBool(
            'check_outline_before_save',default=False)

        self.initIvars()
    #@-node:ekr.20031218072017.3019:leoFileCommands._init_
    #@+node:ekr.20090218115025.5:initIvars
    def initIvars(self):

        # General
        c = self.c
        self.mFileName = ""
        self.fileDate = -1
        self.leo_file_encoding = c.config.new_leo_file_encoding

        # The bin param doesn't exist in Python 2.3;
        # the protocol param doesn't exist in earlier versions of Python.
        version = '.'.join([str(sys.version_info[i]) for i in (0,1)])
        # self.python23 = g.CheckVersion(version,'2.3')

        # For reading
        self.checking = False # True: checking only: do *not* alter the outline.
        self.descendentExpandedList = []
        self.descendentMarksList = []
        self.forbiddenTnodes = []
        self.descendentTnodeUaDictList = []
        self.descendentVnodeUaDictList = []
        self.ratio = 0.5

        self.currentVnode = None
        self.rootVnode = None

        # For writing
        self.read_only = False
        self.rootPosition = None
        self.outputFile = None
        self.openDirectory = None
        self.putCount = 0
        # self.topVnode = None
        self.toString = False
        self.usingClipboard = False
        self.currentPosition = None
        # New in 3.12
        self.copiedTree = None
        self.gnxDict = {}
            # keys are gnx strings as returned by canonicalTnodeIndex.
            # Values are gnx's.
        self.vnodesDict = {}
            # keys are gnx strings; values are ignored
    #@-node:ekr.20090218115025.5:initIvars
    #@-node:ekr.20090218115025.4:Birth
    #@+node:ekr.20031218072017.3020:Reading
    #@+node:ekr.20060919104836: Top-level
    #@+node:ekr.20070919133659.1:checkLeoFile (fileCommands)
    def checkLeoFile (self,event=None):

        '''The check-leo-file command.'''

        fc = self ; c = fc.c ; p = c.p

        # Put the body (minus the @nocolor) into the file buffer.
        s = p.b ; tag = '@nocolor\n'
        if s.startswith(tag): s = s[len(tag):]

        # Do a trial read.
        self.checking = True
        self.initReadIvars()
        c.loading = True # disable c.changed
        try:
            try:
                # self.getAllLeoElements(fileName='check-leo-file',silent=False)
                theFile,isZipped = g.openLeoOrZipFile(c.mFileName)
                self.readSaxFile(
                    theFile,fileName='check-leo-file',
                    silent=False,inClipboard=False,reassignIndices=False)
                g.es_print('check-leo-file passed',color='blue')
            except Exception:
                junk, message, junk = sys.exc_info()
                # g.es_exception()
                g.es_print('check-leo-file failed:',str(message),color='red')
        finally:
            self.checking = False
            c.loading = False # reenable c.changed
    #@-node:ekr.20070919133659.1:checkLeoFile (fileCommands)
    #@+node:ekr.20031218072017.1559:getLeoOutlineFromClipboard & helpers
    def getLeoOutlineFromClipboard (self,s,reassignIndices=True):

        '''Read a Leo outline from string s in clipboard format.'''

        trace = False and not g.unitTesting
        verbose = False
        c = self.c ; current = c.p ; check = not reassignIndices
        checkAfterRead = False or c.config.getBool('check_outline_after_read')

        # Save the hidden root's children.
        children = c.hiddenRootNode.children

        # Always recreate the gnxDict
        self.gnxDict = {}
        if not reassignIndices:
            x = g.app.nodeIndices
            for v in c.all_unique_nodes():
                index = x.toString(v.fileIndex)
                self.gnxDict[index] = v

        self.usingClipboard = True
        try:
            # This encoding must match the encoding used in putLeoOutline.
            s = g.toEncodedString(s,self.leo_file_encoding,reportErrors=True)

            # readSaxFile modifies the hidden root.
            v = self.readSaxFile(
                theFile=None, fileName='<clipboard>',
                silent=True, # don't tell about stylesheet elements.
                inClipboard=True,reassignIndices=reassignIndices,s=s)
            if not v:
                return g.es("the clipboard is not valid ",color="blue")
        finally:
            self.usingClipboard = False

        # Restore the hidden root's children
        c.hiddenRootNode.children = children

        # Unlink v from the hidden root.
        v.parents.remove(c.hiddenRootNode)

        p = leoNodes.position(v)

        # Important: we must not adjust links when linking v
        # into the outline.  The read code has already done that.
        if current.hasChildren() and current.isExpanded():
            if check and not self.checkPaste(current,p):
                return None
            p._linkAsNthChild(current,0,adjust=False)
        else:
            if check and not self.checkPaste(current.parent(),p):
                return None
            p._linkAfter(current,adjust=False)

        if reassignIndices:
            for p2 in p.self_and_subtree():
                p2.v.fileIndex = g.app.nodeIndices.getNewIndex()

        if trace and verbose:
            g.trace('**** dumping outline...')
            c.dumpOutline()

        if checkAfterRead:
            g.trace('checking outline after paste',color='blue')
            c.checkOutline(event=None,verbose=True,unittest=False,full=True)

        c.selectPosition(p)
        return p

    getLeoOutline = getLeoOutlineFromClipboard # for compatibility
    #@+node:ekr.20080410115129.1:checkPaste
    def checkPaste (self,parent,p):

        '''Return True if p may be pasted as a child of parent.'''

        if not parent: return True

        parents = [z.copy() for z in parent.self_and_parents()]

        for p in p.self_and_subtree():
            for z in parents:
                # g.trace(p.h,id(p.v),id(z.v))
                if p.v == z.v:
                    g.es('Invalid paste: nodes may not descend from themselves',color="blue")
                    return False

        return True
    #@-node:ekr.20080410115129.1:checkPaste
    #@-node:ekr.20031218072017.1559:getLeoOutlineFromClipboard & helpers
    #@+node:ekr.20031218072017.1553:getLeoFile & helpers
    # The caller should follow this with a call to c.redraw().

    def getLeoFile (self,theFile,fileName,readAtFileNodesFlag=True,silent=False):

        c = self.c
        c.setChanged(False) # May be set when reading @file nodes.
        self.warnOnReadOnlyFiles(fileName)
        self.checking = False
        self.mFileName = c.mFileName
        self.initReadIvars()

        try:
            c.loading = True # disable c.changed
            ok = self.getLeoFileHelper(theFile,fileName,silent)

            # Do this before reading derived files.
            self.resolveTnodeLists()

            if ok and readAtFileNodesFlag:
                # Redraw before reading the @file nodes so the screen isn't blank.
                # This is important for big files like LeoPy.leo.
                c.redraw()
                c.setFileTimeStamp(fileName)
                c.atFileCommands.readAll(c.rootVnode(),partialFlag=False)

            # Do this after reading derived files.
            if readAtFileNodesFlag:
                # The descendent nodes won't exist unless we have read the @thin nodes!
                self.restoreDescendentAttributes()

            self.setPositionsFromVnodes()
            c.selectVnode(c.p) # load body pane
            if c.config.getBool('check_outline_after_read'):
                c.checkOutline(event=None,verbose=True,unittest=False,full=True)
        finally:
            c.loading = False # reenable c.changed

        c.setChanged(c.changed) # Refresh the changed marker.
        self.initReadIvars()
        return ok, c.frame.ratio
    #@+node:ekr.20090526081836.5841:getLeoFileHelper
    def getLeoFileHelper(self,theFile,fileName,silent):

        '''Read the .leo file and create the outline.'''

        c = self.c

        try:
            ok = True
            v = self.readSaxFile(theFile,fileName,silent,inClipboard=False,reassignIndices=False)
            if v: # v is None for minimal .leo files.
                c.setRootVnode(v)
                self.rootVnode = v
            else:
                v = leoNodes.vnode(context=c)
                v.setHeadString('created root node')
                p = leoNodes.position(v)
                p._linkAsRoot(oldRoot=None)
                self.rootVnode = v
                c.setRootPosition(p)
                c.changed = False
        except BadLeoFile:
            junk, message, junk = sys.exc_info()
            if not silent:
                g.es_exception()
                g.alert(self.mFileName + " is not a valid Leo file: " + str(message))
            ok = False

        return ok
    #@-node:ekr.20090526081836.5841:getLeoFileHelper
    #@+node:ekr.20031218072017.1554:warnOnReadOnlyFiles
    def warnOnReadOnlyFiles (self,fileName):

        # os.access may not exist on all platforms.

        try:
            self.read_only = not os.access(fileName,os.W_OK)
        except AttributeError:
            self.read_only = False
        except UnicodeError:
            self.read_only = False

        if self.read_only and not g.unitTesting:
            g.es("read only:",fileName,color="red")
    #@+node:ekr.20090526102407.10049:@test g.warnOnReadOnlyFile
    if g.unitTesting:

        import os,stat
        c,p = g.getTestVars()
        fc = c.fileCommands

        path = g.os_path_finalize_join(g.app.loadDir,'..','test','test-read-only.txt')
        if os.path.exists(path):
            os.chmod(path, stat.S_IREAD)
            fc.warnOnReadOnlyFiles(path)
            assert fc.read_only
        else:
            fc.warnOnReadOnlyFiles(path)
    #@-node:ekr.20090526102407.10049:@test g.warnOnReadOnlyFile
    #@-node:ekr.20031218072017.1554:warnOnReadOnlyFiles
    #@-node:ekr.20031218072017.1553:getLeoFile & helpers
    #@+node:ekr.20031218072017.3029:readAtFileNodes (fileCommands)
    def readAtFileNodes (self):

        c = self.c ; p = c.p

        c.endEditing()
        c.atFileCommands.readAll(p,partialFlag=True)
        c.redraw()

        # Force an update of the body pane.
        c.setBodyString(p,p.b)
        c.frame.body.onBodyChanged(undoType=None)
    #@-node:ekr.20031218072017.3029:readAtFileNodes (fileCommands)
    #@+node:ekr.20031218072017.2297:open (leoFileCommands)
    def open(self,theFile,fileName,readAtFileNodesFlag=True,silent=False):

        c = self.c ; frame = c.frame

        # Set c.openDirectory
        theDir = g.os_path_dirname(fileName)
        if theDir:
            c.openDirectory = c.frame.openDirectory = theDir

        ok, ratio = self.getLeoFile(
            theFile,fileName,
            readAtFileNodesFlag=readAtFileNodesFlag,
            silent=silent)

        if ok:
            frame.resizePanesToRatio(ratio,frame.secondary_ratio)

        return ok
    #@-node:ekr.20031218072017.2297:open (leoFileCommands)
    #@+node:ekr.20031218072017.3030:readOutlineOnly
    def readOutlineOnly (self,theFile,fileName):

        c = self.c

        #@    << Set the default directory >>
        #@+node:ekr.20071211134300:<< Set the default directory >>
        #@+at
        # The most natural default directory is the directory containing the 
        # .leo file
        # that we are about to open. If the user has specified the "Default 
        # Directory"
        # preference that will over-ride what we are about to set.
        #@-at
        #@@c

        theDir = g.os_path_dirname(fileName)

        if len(theDir) > 0:
            c.openDirectory = c.frame.openDirectory = theDir
        #@-node:ekr.20071211134300:<< Set the default directory >>
        #@nl
        ok, ratio = self.getLeoFile(theFile,fileName,readAtFileNodesFlag=False)
        c.redraw()

        c.frame.deiconify()
        junk,junk,secondary_ratio = self.frame.initialRatios()
        c.frame.resizePanesToRatio(ratio,secondary_ratio)

        return ok
    #@-node:ekr.20031218072017.3030:readOutlineOnly
    #@-node:ekr.20060919104836: Top-level
    #@+node:ekr.20060919133249:Common
    # Methods common to both the sax and non-sax code.
    #@nonl
    #@+node:ekr.20031218072017.2004:canonicalTnodeIndex
    def canonicalTnodeIndex(self,index):

        """Convert Tnnn to nnn, leaving gnx's unchanged."""

        # index might be Tnnn, nnn, or gnx.
        if index is None:
            g.trace('Can not happen: index is None')
            return None

        junk,theTime,junk = g.app.nodeIndices.scanGnx(index,0)
        if theTime == None: # A pre-4.1 file index.
            if index[0] == "T":
                index = index[1:]

        return index
    #@-node:ekr.20031218072017.2004:canonicalTnodeIndex
    #@+node:ekr.20040701065235.1:getDescendentAttributes
    def getDescendentAttributes (self,s,tag=""):

        '''s is a list of gnx's, separated by commas from a <v> or <t> element.
        Parses s into a list.

        This is used to record marked and expanded nodes.
        '''

        gnxs = s.split(',')
        result = [gnx for gnx in gnxs if len(gnx) > 0]
        # g.trace(tag,result)
        return result
    #@-node:ekr.20040701065235.1:getDescendentAttributes
    #@+node:EKR.20040627114602:getDescendentUnknownAttributes
    # Pre Leo 4.5 Only @thin vnodes had the descendentTnodeUnknownAttributes field.
    # New in Leo 4.5: @thin & @shadow vnodes have descendentVnodeUnknownAttributes field.

    def getDescendentUnknownAttributes (self,s):

        '''Unhexlify and unpickle t/v.descendentUnknownAttribute field.'''

        try:
            bin = binascii.unhexlify(s) # Throws a TypeError if val is not a hex string.
            val = pickle.loads(bin)
            return val

        except:
            g.es_exception()
            g.trace('Can not unpickle',s)
            return None
    #@-node:EKR.20040627114602:getDescendentUnknownAttributes
    #@+node:ekr.20060919142200.1:initReadIvars
    def initReadIvars (self):

        self.descendentTnodeUaDictList = []
        self.descendentVnodeUaDictList = []
        self.descendentExpandedList = []
        self.descendentMarksList = []
        self.gnxDict = {}
    #@nonl
    #@-node:ekr.20060919142200.1:initReadIvars
    #@+node:EKR.20040627120120:restoreDescendentAttributes
    def restoreDescendentAttributes (self):

        c = self.c ; trace = False ; verbose = True and not g.unitTesting

        for resultDict in self.descendentTnodeUaDictList:
            if trace: g.trace('t.dict',resultDict)
            for gnx in resultDict:
                tref = self.canonicalTnodeIndex(gnx)
                v = self.gnxDict.get(tref)
                if v:
                    v.unknownAttributes = resultDict[gnx]
                    v._p_changed = 1
                elif verbose:
                    g.trace('can not find vnode (duA): gnx = %s' % (gnx),color='red')

        # New in Leo 4.5: keys are archivedPositions, values are attributes.
        for root_v,resultDict in self.descendentVnodeUaDictList:
            if trace: g.trace('v.dict',resultDict)
            for key in resultDict:
                v = self.resolveArchivedPosition(key,root_v)
                if v:
                    v.unknownAttributes = resultDict[key]
                    v._p_changed = 1
                elif verbose:
                    g.trace('can not find vnode (duA): archivedPosition: %s, root_v: %s' % (
                        key,root_v),color='red')

        marks = {} ; expanded = {}
        for gnx in self.descendentExpandedList:
            tref = self.canonicalTnodeIndex(gnx)
            v = self.gnxDict.get(gnx)
            if v: expanded[v]=v
            elif verbose:
                g.trace('can not find vnode (expanded): gnx = %s, tref: %s' % (gnx,tref),color='red')

        for gnx in self.descendentMarksList:
            tref = self.canonicalTnodeIndex(gnx)
            v = self.gnxDict.get(gnx)
            if v: marks[v]=v
            elif verbose:
                g.trace('can not find vnode (marks): gnx = %s tref: %s' % (gnx,tref),color='red')

        if marks or expanded:
            # g.trace('marks',len(marks),'expanded',len(expanded))
            for p in c.all_unique_positions():
                if marks.get(p.v):
                    p.v.initMarkedBit()
                        # This was the problem: was p.setMark.
                        # There was a big performance bug in the mark hook in the Node Navigator plugin.
                if expanded.get(p.v):
                    p.expand()
    #@-node:EKR.20040627120120:restoreDescendentAttributes
    #@-node:ekr.20060919133249:Common
    #@+node:ekr.20060919104530:Sax (reading)
    #@+node:ekr.20090525144314.6526:cleanSaxInputString & test
    def cleanSaxInputString(self,s):

        '''Clean control characters from s.
        s may be a bytes or a (unicode) string.'''

        # Note: form-feed ('\f') is 12 decimal.
        badchars = [chr(ch) for ch in range(32)]
        badchars.remove('\t')
        badchars.remove('\r')
        badchars.remove('\n')

        flatten = ''.join(badchars)
        pad = ' ' * len(flatten)

        if g.isPython3:
            flatten = bytes(flatten,'utf-8')
            pad = bytes(pad,'utf-8')
            transtable = bytes.maketrans(flatten,pad)
        else:
            transtable = string.maketrans(flatten,pad)

        return s.translate(transtable)

    # for i in range(32): print i,repr(chr(i))
    #@+node:ekr.20090525144314.6527:@test cleanSaxInputString
    if g.unitTesting:

        c,p = g.getTestVars()

        s = 'test%cthis' % 27

        assert c.fileCommands.cleanSaxInputString(s) == 'test this'
    #@-node:ekr.20090525144314.6527:@test cleanSaxInputString
    #@-node:ekr.20090525144314.6526:cleanSaxInputString & test
    #@+node:ekr.20060919110638.5:createSaxChildren & helpers
    def createSaxChildren (self, sax_node, parent_v):

        c = self.c
        trace = False and not g.unitTesting # and c.shortFileName().find('small') > -1
        children = []

        for sax_child in sax_node.children:
            tnx = sax_child.tnx
            v = self.gnxDict.get(tnx)

            if v: # A clone.
                if trace: g.trace('**clone',v)
                v = self.createSaxVnode(sax_child,parent_v,v=v)   
            else:
                v = self.createSaxVnode(sax_child,parent_v)
                self.createSaxChildren(sax_child,v)

            children.append(v)

        parent_v.children = children
        for child in children:
            child.parents.append(parent_v)
            if trace: g.trace(
                '*** added parent',parent_v,'to',child,
                'len(child.parents)',len(child.parents))

        return children
    #@+node:ekr.20060919110638.7:createSaxVnode & helpers
    def createSaxVnode (self,sax_node,parent_v,v=None):

        c = self.c
        trace = False and not g.unitTesting # and c.shortFileName().find('small') > -1
        h = sax_node.headString
        b = sax_node.bodyString

        if v:
            # The body of the later node overrides the earlier.
            # Don't set t.h: h is always empty.
            v.b = b 
        else:
            v = leoNodes.vnode(context=c)
            v.setBodyString(b)
            v.setHeadString(h)

            if sax_node.tnx:
                v.fileIndex = g.app.nodeIndices.scanGnx(sax_node.tnx,0)

        index = self.canonicalTnodeIndex(sax_node.tnx)
        self.gnxDict [index] = v

        if trace: g.trace(
            'tnx','%-22s' % (index),'v',id(v),
            'len(body)','%-4d' % (len(b)),h)

        self.handleVnodeSaxAttributes(sax_node,v)
        self.handleTnodeSaxAttributes(sax_node,v)

        return v
    #@+node:ekr.20060919110638.8:handleTnodeSaxAttributes
    def handleTnodeSaxAttributes (self,sax_node,v):

        trace = False and not g.unitTesting
        d = sax_node.tnodeAttributes
        if trace and d: g.trace(sax_node,list(d.keys()))

        aDict = {}
        for key in d:
            val = d.get(key)
            val2 = self.getSaxUa(key,val)
            # g.trace(key,val,val2)
            aDict[key] = val2

        if aDict:
            if trace: g.trace('uA',v,list(aDict.keys()))
            v.unknownAttributes = aDict
    #@+node:ekr.20090702070510.6028:@test handleTnodeSaxAttributes
    if g.unitTesting:

        c,p = g.getTestVars()

        sax_node = g.bunch(
            tnodeAttributes={
    # The 'tx' attribute is handled by contentHandler.tnodeAttributes.
    # 'tx':"ekr.20090701133940.1767",
    'lineYOffset':"4b032e",
    # A real icon attribute, see the tests below for what we expect
    'icons':"5d7100287d71012855026f6e71025505746e6f6465710355047479\
    70657104550466696c6571055507796f666673657471064b006805583700000\
    0433a5c6c656f2e7265706f5c7472756e6b5c6c656f5c49636f6e735c54616e\
    676f5c31367831365c616374696f6e735c6164642e706e67710755047870616\
    471084b01550577686572657109550e6265666f7265486561646c696e65710a\
    5507786f6666736574710b4b02550772656c50617468710c581b00000054616\
    e676f5c31367831365c616374696f6e735c6164642e706e67710d757d710e28\
    55026f6e710f68035504747970657110550466696c6571115507796f6666736\
    57471124b006811583a000000433a5c6c656f2e7265706f5c7472756e6b5c6c\
    656f5c49636f6e735c54616e676f5c31367831365c616374696f6e735c626f7\
    4746f6d2e706e67711355047870616471144b01550577686572657115550e62\
    65666f7265486561646c696e6571165507786f666673657471174b025507726\
    56c506174687118581e00000054616e676f5c31367831365c616374696f6e73\
    5c626f74746f6d2e706e67711975652e"
    })
        try:
            p2 = p.insertAsLastChild()
            v = p2.v
            c.fileCommands.handleTnodeSaxAttributes(sax_node,v)
            # print v,v.u
            d = v.u
            for attr in ('lineYOffset','icons'):
                assert d.get(attr),attr
            for attr in ('tx','a'):
                assert d.get(attr) is None,attr # A known attribute.
        finally:
            if 1:
                while p.hasChildren():
                    # print('deleting',p.firstChild())
                    p.firstChild().doDelete()
    #@-node:ekr.20090702070510.6028:@test handleTnodeSaxAttributes
    #@-node:ekr.20060919110638.8:handleTnodeSaxAttributes
    #@+node:ekr.20061004053644:handleVnodeSaxAttributes
    # The native attributes of <v> elements are a, t, vtag, tnodeList,
    # marks, expanded, and descendentTnodeUnknownAttributes.
    # New in Leo 4.5: added descendentVnodeUnknownAttributes to native attributes.

    def handleVnodeSaxAttributes (self,sax_node,v):

        trace = False and not g.unitTesting
        d = sax_node.attributes
        # if trace and d: g.trace(d)

        s = d.get('a')
        if s:
            # g.trace('%s a=%s %s' % (id(sax_node),s,v.headString()))
            # 'C' (clone) and 'D' bits are not used.
            if 'M' in s: v.setMarked()
            if 'E' in s: v.expand()
            if 'O' in s: v.setOrphan()
            # if 'T' in s: self.topVnode = v
            if 'V' in s:
                # g.trace('setting currentVnode',v,color='red')
                self.currentVnode = v

        s = d.get('tnodeList','')
        tnodeList = s and s.split(',')
        if tnodeList:
            # This tnodeList will be resolved later.
            if trace: g.trace('found tnodeList',v.headString(),tnodeList)
            v.tempTnodeList = tnodeList

        s = d.get('descendentTnodeUnknownAttributes')
        if s: 
            aDict = self.getDescendentUnknownAttributes(s)
            if aDict:
                # g.trace('descendentTnodeUaDictList',aDict)
                self.descendentTnodeUaDictList.append(aDict)

        s = d.get('descendentVnodeUnknownAttributes')
        if s: 
            aDict = self.getDescendentUnknownAttributes(s)
            if aDict:
                # g.trace('descendentVnodeUaDictList',aDict)
                self.descendentVnodeUaDictList.append((v,aDict),)

        s = d.get('expanded')
        if s:
            aList = self.getDescendentAttributes(s,tag="expanded")
            # g.trace('expanded list',len(aList))
            self.descendentExpandedList.extend(aList)

        s = d.get('marks')
        if s:
            aList = self.getDescendentAttributes(s,tag="marks")
            # g.trace('marks list',len(aList))
            self.descendentMarksList.extend(aList)

        aDict = {}
        for key in d:
            if key in self.nativeVnodeAttributes:
                # This is not a bug.
                if False and trace: g.trace(
                    '****ignoring***',key,d.get(key))
            else:
                val = d.get(key)
                val2 = self.getSaxUa(key,val)
                aDict[key] = val2
                # g.trace(key,val,val2)
        if aDict:
            # if trace: g.trace('uA',v,aDict)
            v.unknownAttributes = aDict
    #@+node:ekr.20090702072557.6420:@test handleVnodeSaxAttributes
    if g.unitTesting:

        c,p = g.getTestVars()
        sax_node = g.bunch(
            attributes={
    'a':'M',
    'lineYOffset':"4b032e",
    # A real icon attribute, see the tests below for what we expect
    'icons':"5d7100287d71012855026f6e71025505746e6f6465710355047479\
    70657104550466696c6571055507796f666673657471064b006805583700000\
    0433a5c6c656f2e7265706f5c7472756e6b5c6c656f5c49636f6e735c54616e\
    676f5c31367831365c616374696f6e735c6164642e706e67710755047870616\
    471084b01550577686572657109550e6265666f7265486561646c696e65710a\
    5507786f6666736574710b4b02550772656c50617468710c581b00000054616\
    e676f5c31367831365c616374696f6e735c6164642e706e67710d757d710e28\
    55026f6e710f68035504747970657110550466696c6571115507796f6666736\
    57471124b006811583a000000433a5c6c656f2e7265706f5c7472756e6b5c6c\
    656f5c49636f6e735c54616e676f5c31367831365c616374696f6e735c626f7\
    4746f6d2e706e67711355047870616471144b01550577686572657115550e62\
    65666f7265486561646c696e6571165507786f666673657471174b025507726\
    56c506174687118581e00000054616e676f5c31367831365c616374696f6e73\
    5c626f74746f6d2e706e67711975652e"
        })
        try:
            p2 = p.insertAsLastChild()
            v = p2.v
            c.fileCommands.handleVnodeSaxAttributes(sax_node,v)
            # print v,v.u
            d = v.u
            for attr in ('lineYOffset','icons'):
                assert d.get(attr) is not None,attr
            # The a:M attribute should mark the node.
            assert d.get('a') is None
            assert v.isMarked()
            aList = d.get('icons')
            assert aList
            assert len(aList) == 2
            for d2 in aList:
                for key in ('on','where','yoffset','file'):
                    assert d2.get(key) is not None,key
        finally:
            if 1:
                while p.hasChildren():
                    # print('deleting',p.firstChild())
                    p.firstChild().doDelete()
    #@-node:ekr.20090702072557.6420:@test handleVnodeSaxAttributes
    #@-node:ekr.20061004053644:handleVnodeSaxAttributes
    #@-node:ekr.20060919110638.7:createSaxVnode & helpers
    #@-node:ekr.20060919110638.5:createSaxChildren & helpers
    #@+node:ekr.20060919110638.2:dumpSaxTree
    def dumpSaxTree (self,root,dummy):

        if not root:
            g.pr('dumpSaxTree: empty tree')
            return
        if not dummy:
            root.dump()
        for child in root.children:
            self.dumpSaxTree(child,dummy=False)
    #@nonl
    #@-node:ekr.20060919110638.2:dumpSaxTree
    #@+node:ekr.20061003093021:getSaxUa
    def getSaxUa(self,attr,val,kind=None): # Kind is for unit testing.

        """Parse an unknown attribute in a <v> or <t> element.
        The unknown tag has been pickled and hexlify'd.
        """

        try:
            val = str(val)
        except UnicodeError:
            g.es_print('unexpected exception converting hexlified string to string')
            g.es_exception()

        # g.trace(attr,repr(val))

        # New in 4.3: leave string attributes starting with 'str_' alone.
        if attr.startswith('str_') and type(val) == type(''):
            # g.trace(attr,val)
            return val

        # New in 4.3: convert attributes starting with 'b64_' using the base64 conversion.
        if 0: # Not ready yet.
            if attr.startswith('b64_'):
                try: pass
                except Exception: pass

        try:
            binString = binascii.unhexlify(val) # Throws a TypeError if val is not a hex string.
        except Exception:
            # Python 2.x throws TypeError
            # Python 3.x throws binascii.Error
            # Assume that Leo 4.1 wrote the attribute.
            if g.unitTesting:
                assert kind == 'raw','unit test failed: kind=' % repr(kind)
            else:
                g.trace('can not unhexlify %s=%s' % (attr,val))
            return val
        try:
            # No change needed to support protocols.
            val2 = pickle.loads(binString)
            # g.trace('v.3 val:',val2)
            return val2
        except (pickle.UnpicklingError,ImportError,AttributeError,ValueError):
            g.trace('can not unpickle %s=%s' % (attr,val))
            return val
    #@+node:ekr.20090702072557.6495:@test getSaxUa
    if g.unitTesting:

        c,p = g.getTestVars()

        expectedIconDictList = [
        {
            'on': 'tnode',
            'where': 'beforeHeadline',
            'yoffset': 0,
            # 'file': u'C:\\leo.repo\\trunk\\leo\\Icons\\Tango\\16x16\\actions\\add.png',
            'file': 'C:\\leo.repo\\trunk\\leo\\Icons\\Tango\\16x16\\actions\\add.png',
            'xpad': 1,
            'type': 'file',
            'xoffset': 2,
            # 'relPath': u'Tango\\16x16\\actions\\add.png',
            'relPath': 'Tango\\16x16\\actions\\add.png',
        },
        {
            'on': 'tnode',
            'where': 'beforeHeadline',
            'yoffset': 0,
            # 'file': u'C:\\leo.repo\\trunk\\leo\\Icons\\Tango\\16x16\\actions\\bottom.png',
            'file': 'C:\\leo.repo\\trunk\\leo\\Icons\\Tango\\16x16\\actions\\bottom.png',
            'xpad': 1,
            'type': 'file',
            'xoffset': 2,
            # 'relPath': u'Tango\\16x16\\actions\\bottom.png',
            'relPath': 'Tango\\16x16\\actions\\bottom.png',
        }]
        table = (
    ('tx','raw',None,"ekr.20090701133940.1767"),
    ('lineYOffset',None,3,"4b032e"),
    # A real icon
    ('icons',None,expectedIconDictList,
    "5d7100287d71012855026f6e71025505746e6f6465710355047479\
    70657104550466696c6571055507796f666673657471064b006805583700000\
    0433a5c6c656f2e7265706f5c7472756e6b5c6c656f5c49636f6e735c54616e\
    676f5c31367831365c616374696f6e735c6164642e706e67710755047870616\
    471084b01550577686572657109550e6265666f7265486561646c696e65710a\
    5507786f6666736574710b4b02550772656c50617468710c581b00000054616\
    e676f5c31367831365c616374696f6e735c6164642e706e67710d757d710e28\
    55026f6e710f68035504747970657110550466696c6571115507796f6666736\
    57471124b006811583a000000433a5c6c656f2e7265706f5c7472756e6b5c6c\
    656f5c49636f6e735c54616e676f5c31367831365c616374696f6e735c626f7\
    4746f6d2e706e67711355047870616471144b01550577686572657115550e62\
    65666f7265486561646c696e6571165507786f666673657471174b025507726\
    56c506174687118581e00000054616e676f5c31367831365c616374696f6e73\
    5c626f74746f6d2e706e67711975652e"),
    )
        for attr,kind,expected,val in table:
            result = c.fileCommands.getSaxUa(attr,val,kind=kind)
            if expected is None: expected = val
            assert expected==result,'expected %s got %s' % (
                expected,result)
    #@nonl
    #@-node:ekr.20090702072557.6495:@test getSaxUa
    #@-node:ekr.20061003093021:getSaxUa
    #@+node:ekr.20060919110638.14:parse_leo_file
    def parse_leo_file (self,theFile,inputFileName,silent,inClipboard,s=None):

        c = self.c
        try:
            if g.isPython3:
                if theFile:
                    # Use the open binary file, opened by g.openLeoOrZipFile.
                    s = theFile.read() # type(s) is bytes.
                    s = self.cleanSaxInputString(s)
                    theFile = BytesIO(s)
                else:
                    s = str(s,encoding='utf-8') ####
                    s = self.cleanSaxInputString(s)
                    theFile = StringIO(s)
            else:
                if theFile: s = theFile.read()
                s = self.cleanSaxInputString(s)
                theFile = cStringIO.StringIO(s)
            parser = xml.sax.make_parser()
            parser.setFeature(xml.sax.handler.feature_external_ges,1)
                # Include external general entities, esp. xml-stylesheet lines.
            if 0: # Expat does not read external features.
                parser.setFeature(xml.sax.handler.feature_external_pes,1)
                    # Include all external parameter entities
                    # Hopefully the parser can figure out the encoding from the <?xml> element.
            handler = saxContentHandler(c,inputFileName,silent,inClipboard)
            parser.setContentHandler(handler)
            parser.parse(theFile) # expat does not support parseString
            # g.trace('parsing done')
            sax_node = handler.getRootNode()
        except xml.sax.SAXParseException:
            g.es_print('error parsing',inputFileName,color='red')
            g.es_exception()
            sax_node = None
        except Exception:
            g.es_print('unexpected exception parsing',inputFileName,color='red')
            g.es_exception()
            sax_node = None

        return sax_node
    #@-node:ekr.20060919110638.14:parse_leo_file
    #@+node:ekr.20060919110638.3:readSaxFile
    def readSaxFile (self,theFile,fileName,silent,inClipboard,reassignIndices,s=None):

        dump = False and not g.unitTesting
        at = self ; c = self.c

        # Pass one: create the intermediate nodes.
        saxRoot = self.parse_leo_file(theFile,fileName,
            silent=silent,inClipboard=inClipboard,s=s)

        if dump: self.dumpSaxTree(saxRoot,dummy=True)

        # Pass two: create the tree of vnodes and tnodes from the intermediate nodes.
        if saxRoot:
            parent_v = c.hiddenRootNode
            children = at.createSaxChildren(saxRoot,parent_v)
            assert c.hiddenRootNode.children == children
            v = children and children[0] or None
            return v
        else:
            return None
    #@-node:ekr.20060919110638.3:readSaxFile
    #@+node:ekr.20060919110638.11:resolveTnodeLists
    def resolveTnodeLists (self):

        trace = False and not g.unitTesting
        c = self.c

        for p in c.all_unique_positions():
            if hasattr(p.v,'tempTnodeList'):
                # g.trace(p.v.headString())
                result = []
                for tnx in p.v.tempTnodeList:
                    index = self.canonicalTnodeIndex(tnx)
                    v = self.gnxDict.get(index)
                    if v:
                        if trace: g.trace(tnx,v)
                        result.append(v)
                    else:
                        g.trace('*** No vnode for %s' % tnx)
                p.v.tnodeList = result
                delattr(p.v,'tempTnodeList')
    #@nonl
    #@-node:ekr.20060919110638.11:resolveTnodeLists
    #@+node:ekr.20080805132422.3:resolveArchivedPosition  (New in Leo 4.5)
    def resolveArchivedPosition(self,archivedPosition,root_v):

        '''Return a vnode corresponding to the archived position relative to root node root_v.'''

        def oops (message):
            if not g.app.unitTesting:
                g.es_print('bad archived position: %s' % (message),color='red')

        try:
            aList = [int(z) for z in archivedPosition.split('.')]
            aList.reverse()
        except Exception:
            return oops('"%s"' % archivedPosition)

        if not aList:
            return oops('empty')

        last_v = root_v
        n = aList.pop()
        if n != 0:
            return oops('root index="%s"' % n )

        while aList:
            n = aList.pop()
            children = last_v.children
            if n < len(children):
                last_v = children[n]
            else:
                return oops('bad index="%s", len(children)="%s"' % (n,len(children)))

        return last_v
    #@nonl
    #@-node:ekr.20080805132422.3:resolveArchivedPosition  (New in Leo 4.5)
    #@+node:ekr.20060919110638.13:setPositionsFromVnodes & helper
    def setPositionsFromVnodes (self):

        c = self.c ; p = c.rootPosition()

        current = None
        d = hasattr(p.v,'unknownAttributes') and p.v.unknownAttributes
        if d:
            s = d.get('str_leo_pos')
            if s:
                current = self.archivedPositionToPosition(s)

        c.setCurrentPosition(current or c.rootPosition())
    #@nonl
    #@+node:ekr.20061006104837.1:archivedPositionToPosition
    def archivedPositionToPosition (self,s):

        c = self.c
        aList = s.split(',')
        try:
            aList = [int(z) for z in aList]
        except Exception:
            # g.trace('oops: bad archived position. not an int:',aList,c)
            aList = None
        if not aList: return None
        p = c.rootPosition() ; level = 0
        while level < len(aList):
            i = aList[level]
            while i > 0:
                if p.hasNext():
                    p.moveToNext()
                    i -= 1
                else:
                    # g.trace('oops: bad archived position. no sibling:',aList,p.h,c)
                    return None
            level += 1
            if level < len(aList):
                p.moveToFirstChild()
                # g.trace('level',level,'index',aList[level],p.h)
        return p
    #@nonl
    #@-node:ekr.20061006104837.1:archivedPositionToPosition
    #@-node:ekr.20060919110638.13:setPositionsFromVnodes & helper
    #@-node:ekr.20060919104530:Sax (reading)
    #@-node:ekr.20031218072017.3020:Reading
    #@+node:ekr.20031218072017.3032:Writing
    #@+node:ekr.20070413045221.2: Top-level  (leoFileCommands)
    #@+node:ekr.20031218072017.1720:save (fileCommands)
    def save(self,fileName):

        c = self.c ; v = c.currentVnode()

        # New in 4.2.  Return ok flag so shutdown logic knows if all went well.
        ok = g.doHook("save1",c=c,p=v,v=v,fileName=fileName)

        if ok is None:
            c.endEditing() # Set the current headline text.
            self.setDefaultDirectoryForNewFiles(fileName)
            ok = c.checkFileTimeStamp(fileName)
            if ok:
                ok = self.write_Leo_file(fileName,False) # outlineOnlyFlag
            if ok:
                self.putSavedMessage(fileName)
                c.setChanged(False) # Clears all dirty bits.
                if c.config.save_clears_undo_buffer:
                    g.es("clearing undo")
                    c.undoer.clearUndoState()

            c.redraw_after_icons_changed()

        g.doHook("save2",c=c,p=v,v=v,fileName=fileName)
        return ok
    #@-node:ekr.20031218072017.1720:save (fileCommands)
    #@+node:ekr.20031218072017.3043:saveAs
    def saveAs(self,fileName):

        c = self.c ; v = c.currentVnode()

        if not g.doHook("save1",c=c,p=v,v=v,fileName=fileName):
            c.endEditing() # Set the current headline text.
            self.setDefaultDirectoryForNewFiles(fileName)
            if self.write_Leo_file(fileName,False): # outlineOnlyFlag
                c.setChanged(False) # Clears all dirty bits.
                self.putSavedMessage(fileName)

            c.redraw_after_icons_changed()

        g.doHook("save2",c=c,p=v,v=v,fileName=fileName)
    #@-node:ekr.20031218072017.3043:saveAs
    #@+node:ekr.20031218072017.3044:saveTo
    def saveTo (self,fileName):

        c = self.c ; v = c.currentVnode()

        if not g.doHook("save1",c=c,p=v,v=v,fileName=fileName):
            c.endEditing()# Set the current headline text.
            self.setDefaultDirectoryForNewFiles(fileName)
            self.write_Leo_file(fileName,False) # outlineOnlyFlag
            self.putSavedMessage(fileName)

            c.redraw_after_icons_changed()

        g.doHook("save2",c=c,p=v,v=v,fileName=fileName)
    #@-node:ekr.20031218072017.3044:saveTo
    #@+node:ekr.20070413061552:putSavedMessage
    def putSavedMessage (self,fileName):

        c = self.c

        zipMark = g.choose(c.isZipped,'[zipped] ','')

        g.es("saved:","%s%s" % (zipMark,g.shortFileName(fileName)))
    #@nonl
    #@-node:ekr.20070413061552:putSavedMessage
    #@-node:ekr.20070413045221.2: Top-level  (leoFileCommands)
    #@+node:ekr.20050404190914.2:deleteFileWithMessage
    def deleteFileWithMessage(self,fileName,unused_kind):

        try:
            os.remove(fileName)

        except Exception:
            if self.read_only:
                g.es("read only",color="red")
            if not g.unitTesting:
                g.es("exception deleting backup file:",fileName)
                g.es_exception(full=False)
            return False
    #@-node:ekr.20050404190914.2:deleteFileWithMessage
    #@+node:ekr.20031218072017.1470:put
    def put (self,s):

        '''Put string s to self.outputFile. All output eventually comes here.'''

        # Improved code: self.outputFile (a cStringIO object) always exists.
        if s:
            self.putCount += 1
            if g.isPython3:
                pass
            else:
                s = g.toEncodedString(s,self.leo_file_encoding,reportErrors=True)
            self.outputFile.write(s)

    def put_dquote (self):
        self.put('"')

    def put_dquoted_bool (self,b):
        if b: self.put('"1"')
        else: self.put('"0"')

    def put_flag (self,a,b):
        if a:
            self.put(" ") ; self.put(b) ; self.put('="1"')

    def put_in_dquotes (self,a):
        self.put('"')
        if a: self.put(a) # will always be True if we use backquotes.
        else: self.put('0')
        self.put('"')

    def put_nl (self):
        self.put("\n")

    def put_tab (self):
        self.put("\t")

    def put_tabs (self,n):
        while n > 0:
            self.put("\t")
            n -= 1
    #@nonl
    #@-node:ekr.20031218072017.1470:put
    #@+node:ekr.20031218072017.1971:putClipboardHeader
    def putClipboardHeader (self):

        c = self.c ; tnodes = 0

        if 1: # Put the minimum header for sax.
            self.put('<leo_header file_format="2"/>\n')

        else: # Put the header for the old read code.
            #@        << count the number of tnodes >>
            #@+node:ekr.20031218072017.1972:<< count the number of tnodes >>
            c.clearAllVisited()

            for p in c.p.self_and_subtree():
                v = p.v
                if v and not v.isWriteBit():
                    v.setWriteBit()
                    tnodes += 1
            #@-node:ekr.20031218072017.1972:<< count the number of tnodes >>
            #@nl
            self.put('<leo_header file_format="1" tnodes=')
            self.put_in_dquotes(str(tnodes))
            self.put(" max_tnode_index=")
            self.put_in_dquotes(str(tnodes))
            self.put("/>") ; self.put_nl()

            # New in Leo 4.4.3: Add dummy elements so copied nodes form a valid .leo file.
            self.put('<globals/>\n')
            self.put('<preferences/>\n')
            self.put('<find_panel_settings/>\n')
    #@-node:ekr.20031218072017.1971:putClipboardHeader
    #@+node:ekr.20040324080819.1:putLeoFile & helpers
    def putLeoFile (self):

        self.updateFixedStatus()
        self.putProlog()
        self.putHeader()
        self.putGlobals()
        self.putPrefs()
        self.putFindSettings()
        #start = g.getTime()
        self.putVnodes()
        #start = g.printDiffTime("vnodes ",start)
        self.putTnodes()
        #start = g.printDiffTime("tnodes ",start)
        self.putPostlog()
    #@+node:ekr.20031218072017.3035:putFindSettings
    def putFindSettings (self):

        # New in 4.3:  These settings never get written to the .leo file.
        self.put("<find_panel_settings/>")
        self.put_nl()
    #@-node:ekr.20031218072017.3035:putFindSettings
    #@+node:ekr.20031218072017.3037:putGlobals
    # Changed for Leo 4.0.

    def putGlobals (self):

        trace = False and not g.unitTesting
        c = self.c

        use_db = g.enableDB and c.db and c.mFileName

        if use_db:
            key = c.atFileCommands._contentHashFile(c.mFileName,'globals')
            if trace: g.trace(len(list(c.db.keys())),c.mFileName,key)
            #@        << put all data to c.db >>
            #@+node:ekr.20100112095623.6267:<< put all data to c.db >>
            c.db['body_outline_ratio_%s' % key] = str(c.frame.ratio)
            c.db['body_secondary_ratio_%s' % key] = str(c.frame.secondary_ratio)

            if trace: g.trace('ratios: %1.2f %1.2f' % (
                c.frame.ratio,c.frame.secondary_ratio))

            width,height,left,top = c.frame.get_window_info()

            c.db['window_position_%s' % key] = (
                str(top),str(left),str(height),str(width))

            if trace: g.trace('top',top,'left',left,'height',height,'width',width)
            #@-node:ekr.20100112095623.6267:<< put all data to c.db >>
            #@nl

        # Always put postions, to trigger sax methods.
        self.put("<globals")
        #@    << put the body/outline ratios >>
        #@+node:ekr.20031218072017.3038:<< put the body/outline ratios >>
        self.put(" body_outline_ratio=")
        self.put_in_dquotes(g.choose(c.fixed or use_db,"0.5","%1.2f" % (
            c.frame.ratio)))

        self.put(" body_secondary_ratio=")
        self.put_in_dquotes(g.choose(c.fixed or use_db,"0.5","%1.2f" % (
            c.frame.secondary_ratio)))

        if trace: g.trace('fixed or use_db',c.fixed or use_db,
            '%1.2f %1.2f' % (c.frame.ratio,c.frame.secondary_ratio))
        #@-node:ekr.20031218072017.3038:<< put the body/outline ratios >>
        #@nl
        self.put(">") ; self.put_nl()
        #@    << put the position of this frame >>
        #@+node:ekr.20031218072017.3039:<< put the position of this frame >>
        # New in Leo 4.5: support fixed .leo files.

        if c.fixed or use_db:
            width,height,left,top = 700,500,50,50
                # Put fixed, immutable, reasonable defaults.
                # Leo 4.5 and later will ignore these when reading.
                # These should be reasonable defaults so that the
                # file will be opened properly by older versions
                # of Leo that do not support fixed .leo files.
        else:
            width,height,left,top = c.frame.get_window_info()

        # g.trace(width,height,left,top)

        self.put_tab()
        self.put("<global_window_position")
        self.put(" top=") ; self.put_in_dquotes(str(top))
        self.put(" left=") ; self.put_in_dquotes(str(left))
        self.put(" height=") ; self.put_in_dquotes(str(height))
        self.put(" width=") ; self.put_in_dquotes(str(width))
        self.put("/>") ; self.put_nl()
        #@-node:ekr.20031218072017.3039:<< put the position of this frame >>
        #@nl
        #@    << put the position of the log window >>
        #@+node:ekr.20031218072017.3040:<< put the position of the log window >>
        top = left = height = width = 0 # no longer used

        self.put_tab()
        self.put("<global_log_window_position")
        self.put(" top=") ; self.put_in_dquotes(str(top))
        self.put(" left=") ; self.put_in_dquotes(str(left))
        self.put(" height=") ; self.put_in_dquotes(str(height))
        self.put(" width=") ; self.put_in_dquotes(str(width))
        self.put("/>") ; self.put_nl()
        #@-node:ekr.20031218072017.3040:<< put the position of the log window >>
        #@nl
        self.put("</globals>") ; self.put_nl()
    #@-node:ekr.20031218072017.3037:putGlobals
    #@+node:ekr.20031218072017.3041:putHeader
    def putHeader (self):

        tnodes = 0 ; clone_windows = 0 # Always zero in Leo2.

        if 1: # For compatibility with versions before Leo 4.5.
            self.put("<leo_header")
            self.put(" file_format=") ; self.put_in_dquotes("2")
            self.put(" tnodes=") ; self.put_in_dquotes(str(tnodes))
            self.put(" max_tnode_index=") ; self.put_in_dquotes(str(0))
            self.put(" clone_windows=") ; self.put_in_dquotes(str(clone_windows))
            self.put("/>") ; self.put_nl()

        else:
            self.put('<leo_header file_format="2"/>\n')
    #@-node:ekr.20031218072017.3041:putHeader
    #@+node:ekr.20031218072017.3042:putPostlog
    def putPostlog (self):

        self.put("</leo_file>") ; self.put_nl()
    #@-node:ekr.20031218072017.3042:putPostlog
    #@+node:ekr.20031218072017.2066:putPrefs
    def putPrefs (self):

        # New in 4.3:  These settings never get written to the .leo file.
        self.put("<preferences/>")
        self.put_nl()
    #@-node:ekr.20031218072017.2066:putPrefs
    #@+node:ekr.20031218072017.1246:putProlog
    def putProlog (self):

        c = self.c

        self.putXMLLine()

        if c.config.stylesheet or c.frame.stylesheet:
            self.putStyleSheetLine()

        self.put("<leo_file>") ; self.put_nl()
    #@-node:ekr.20031218072017.1246:putProlog
    #@+node:ekr.20031218072017.1248:putStyleSheetLine
    def putStyleSheetLine (self):

        c = self.c

        # The stylesheet in the .leo file takes precedence over the default stylesheet.
        self.put("<?xml-stylesheet ")
        self.put(c.frame.stylesheet or c.config.stylesheet)
        self.put("?>")
        self.put_nl()
    #@nonl
    #@-node:ekr.20031218072017.1248:putStyleSheetLine
    #@+node:ekr.20031218072017.1577:putTnode
    def putTnode (self,v):

        # Call put just once.
        gnx = g.app.nodeIndices.toString(v.fileIndex)
        ua = hasattr(v,'unknownAttributes') and self.putUnknownAttributes(v) or ''
        b = v.b
        if b:
            body = xml.sax.saxutils.escape(b)
        else:
            body = ''

        self.put('<t tx="%s"%s>%s</t>\n' % (gnx,ua,body))
    #@-node:ekr.20031218072017.1577:putTnode
    #@+node:ekr.20031218072017.1575:putTnodes
    def putTnodes (self):

        """Puts all tnodes as required for copy or save commands"""

        c = self.c

        self.put("<tnodes>\n")
        #@    << write only those tnodes that were referenced >>
        #@+node:ekr.20031218072017.1576:<< write only those tnodes that were referenced >>
        if self.usingClipboard: # write the current tree.
            theIter = c.p.self_and_subtree()
        else: # write everything
            theIter = c.all_unique_positions()

        # Populate tnodes
        tnodes = {}
        nodeIndices = g.app.nodeIndices
        for p in theIter:
            # Make *sure* the file index has the proper form.
            # g.trace(p.v.fileIndex)
            try:
                theId,t,n = p.v.fileIndex
            except ValueError:
                try:
                    theId,t,n = p.v.fileIndex,''
                except Exception:
                    raise BadLeoFile('bad p.v.fileIndex' % repr(p.v.fileIndex))

            if n is None:
                n = g.u('0')
            elif g.isPython3:
                n = str(n)
            else:
                n = unicode(n)
            index = theId,t,n
            tnodes[index] = p.v

        # Put all tnodes in index order.
        for index in sorted(tnodes):
            # g.trace(index)
            v = tnodes.get(index)
            if v:
                # Write only those tnodes whose vnodes were written.
                if v.isWriteBit():
                    self.putTnode(v)
            else:
                g.trace('can not happen: no vnode for',repr(index))
                # This prevents the file from being written.
                raise BadLeoFile('no vnode for %s' % repr(index))
        #@-node:ekr.20031218072017.1576:<< write only those tnodes that were referenced >>
        #@nl
        self.put("</tnodes>\n")
    #@-node:ekr.20031218072017.1575:putTnodes
    #@+node:ekr.20031218072017.1863:putVnode
    def putVnode (self,p,isIgnore=False):

        """Write a <v> element corresponding to a vnode."""

        fc = self ; c = fc.c ; v = p.v
        isAuto = p.isAtAutoNode() and p.atAutoNodeName().strip()
        isEdit = p.isAtEditNode() and p.atEditNodeName().strip()
        isShadow = p.isAtShadowFileNode()
        isThin = p.isAtThinFileNode()
        isOrphan = p.isOrphan()
        if not isIgnore: isIgnore = p.isAtIgnoreNode()

        if   isIgnore: forceWrite = True      # Always write full @ignore trees.
        elif isAuto:   forceWrite = False     # Never write non-ignored @auto trees.
        elif isEdit:   forceWrite = False     # Never write non-ignored @edit trees.
        elif isShadow: forceWrite = False     # Never write non-ignored @shadow trees.
        elif isThin:   forceWrite = isOrphan  # Only write orphan @thin trees.
        else:          forceWrite = True      # Write all other @file trees.

        #@    << Set gnx = vnode index >>
        #@+node:ekr.20031218072017.1864:<< Set gnx = vnode index >>
        gnx = g.app.nodeIndices.toString(v.fileIndex)

        if forceWrite or self.usingClipboard:
            v.setWriteBit() # 4.2: Indicate we wrote the body text.
        #@-node:ekr.20031218072017.1864:<< Set gnx = vnode index >>
        #@nl
        attrs = []
        #@    << Append attribute bits to attrs >>
        #@+node:ekr.20031218072017.1865:<< Append attribute bits to attrs >>
        # These string catenations are benign because they rarely happen.
        attr = ""
        # New in Leo 4.5: support fixed .leo files.
        if not c.fixed:
            if v.isExpanded() and v.hasChildren(): attr += "E"
            if v.isMarked():   attr += "M"
            if v.isOrphan():   attr += "O"

            # No longer a bottleneck now that we use p.equal rather than p.__cmp__
            # Almost 30% of the entire writing time came from here!!!
            # if not self.use_sax:
                # if p.equal(self.topPosition):     attr += "T" # was a bottleneck
                # if p.equal(self.currentPosition): attr += "V" # was a bottleneck

            if attr:
                attrs.append(' a="%s"' % attr)

        # Put the archived *current* position in the *root* positions <v> element.
        if p == self.rootPosition:
            aList = [str(z) for z in self.currentPosition.archivedPosition()]
            d = hasattr(v,'unKnownAttributes') and v.unknownAttributes or {}
            if not c.fixed:
                d['str_leo_pos'] = ','.join(aList)
            # g.trace(aList,d)
            v.unknownAttributes = d
        elif hasattr(v,"unknownAttributes"):
            d = v.unknownAttributes
            if d and not c.fixed and d.get('str_leo_pos'):
                # g.trace("clearing str_leo_pos",v)
                del d['str_leo_pos']
                v.unknownAttributes = d
        #@-node:ekr.20031218072017.1865:<< Append attribute bits to attrs >>
        #@nl
        #@    << Append tnodeList and unKnownAttributes to attrs >>
        #@+node:ekr.20040324082713:<< Append tnodeList and unKnownAttributes to attrs>> fc.put
        # Write the tnodeList only for @file nodes.
        if hasattr(v,"tnodeList") and len(v.tnodeList) > 0 and v.isAnyAtFileNode():
            if isThin or isShadow or isAuto:  # Bug fix: 2008/8/7.
                if isThin or isShadow: # Never issue warning for @auto.
                    if g.app.unitTesting:
                        g.app.unitTestDict["warning"] = True
                    g.es("deleting tnodeList for",p.h,color="blue")
                # This is safe: cloning can't change the type of this node!
                delattr(v,"tnodeList")
            else:
                attrs.append(fc.putTnodeList(v)) # New in 4.0

        if False: # These are now put in <t> elements.
            if hasattr(v,"unknownAttributes"): # New in 4.0
                # g.trace('v',v,'v.uA',v.unknownAttributes)
                attrs.append(self.putUnknownAttributes(v))

        if p.hasChildren() and not forceWrite and not self.usingClipboard:
            # We put the entire tree when using the clipboard, so no need for this.
            if not isAuto: # Bug fix: 2008/8/7.
                attrs.append(self.putDescendentVnodeUas(p)) # New in Leo 4.5.
                attrs.append(self.putDescendentAttributes(p))
        #@nonl
        #@-node:ekr.20040324082713:<< Append tnodeList and unKnownAttributes to attrs>> fc.put
        #@nl
        attrs = ''.join(attrs)
        v_head = '<v t="%s"%s>' % (gnx,attrs)
        if gnx in fc.vnodesDict:
            fc.put(v_head+'</v>\n')
        else:
            fc.vnodesDict[gnx]=True
            v_head += '<vh>%s</vh>' % (xml.sax.saxutils.escape(p.v.headString()or''))
            # The string catentation is faster than repeated calls to fc.put.
            if not self.usingClipboard:
                #@            << issue informational messages >>
                #@+node:ekr.20040702085529:<< issue informational messages >>
                if isOrphan and isThin:
                    g.es("writing erroneous:",p.h,color="blue")
                    p.clearOrphan()
                #@-node:ekr.20040702085529:<< issue informational messages >>
                #@nl
            # New in 4.2: don't write child nodes of @file-thin trees (except when writing to clipboard)
            if p.hasChildren() and (forceWrite or self.usingClipboard):
                fc.put('%s\n' % v_head)
                # This optimization eliminates all "recursive" copies.
                p.moveToFirstChild()
                while 1:
                    fc.putVnode(p,isIgnore)
                    if p.hasNext(): p.moveToNext()
                    else:           break
                p.moveToParent() # Restore p in the caller.
                fc.put('</v>\n')
            else:
                fc.put('%s</v>\n' % v_head) # Call put only once.
    #@-node:ekr.20031218072017.1863:putVnode
    #@+node:ekr.20031218072017.1579:putVnodes
    def putVnodes (self):

        """Puts all <v> elements in the order in which they appear in the outline."""

        c = self.c
        c.clearAllVisited()

        self.put("<vnodes>\n")

        # Make only one copy for all calls.
        self.currentPosition = c.p 
        self.rootPosition    = c.rootPosition()
        # self.topPosition     = c.topPosition()
        self.vnodesDict = {}

        if self.usingClipboard:
            self.putVnode(self.currentPosition) # Write only current tree.
        else:
            for p in c.rootPosition().self_and_siblings():
                # New in Leo 4.4.2 b2 An optimization:
                self.putVnode(p,isIgnore=p.isAtIgnoreNode()) # Write the next top-level node.

        self.put("</vnodes>\n")
    #@nonl
    #@-node:ekr.20031218072017.1579:putVnodes
    #@+node:ekr.20031218072017.1247:putXMLLine
    def putXMLLine (self):

        '''Put the **properly encoded** <?xml> element.'''

        # Use self.leo_file_encoding encoding.
        self.put('%s"%s"%s\n' % (
            g.app.prolog_prefix_string,
            self.leo_file_encoding,
            g.app.prolog_postfix_string))
    #@nonl
    #@-node:ekr.20031218072017.1247:putXMLLine
    #@-node:ekr.20040324080819.1:putLeoFile & helpers
    #@+node:ekr.20031218072017.1573:putLeoOutline (to clipboard)
    def putLeoOutline (self):

        '''Return a string, *not unicode*, encoded with self.leo_file_encoding,
        suitable for pasting to the clipboard.'''

        self.outputFile = g.fileLikeObject()
        self.usingClipboard = True

        self.putProlog()
        self.putClipboardHeader()
        self.putVnodes()
        self.putTnodes()
        self.putPostlog()

        s = self.outputFile.getvalue()
        self.outputFile = None
        self.usingClipboard = False
        return s
    #@-node:ekr.20031218072017.1573:putLeoOutline (to clipboard)
    #@+node:ekr.20060919064401:putToOPML
    # All elements and attributes prefixed by ':' are leo-specific.
    # All other elements and attributes are specified by the OPML 1 spec.

    def putToOPML (self):

        '''Should be overridden by the opml plugin.'''

        return None
    #@nonl
    #@-node:ekr.20060919064401:putToOPML
    #@+node:ekr.20031218072017.3046:write_Leo_file & helpers
    def write_Leo_file(self,fileName,outlineOnlyFlag,toString=False,toOPML=False):

        c = self.c
        if self.checkOutlineBeforeSave and not self.checkOutline():
            return False
        if not outlineOnlyFlag or toOPML:
            g.app.config.writeRecentFilesFile(c)
            self.writeAllAtFileNodesHelper() # Ignore any errors.
        if self.isReadOnly(fileName):
            return False
        try:
            self.putCount = 0 ; self.toString = toString
            if toString:
                ok = self.writeToStringHelper(fileName)
            else:
                ok = self.writeToFileHelper(fileName,toOPML)
        finally:
            self.outputFile = None
            self.toString = False
        return ok

    write_LEO_file = write_Leo_file # For compatibility with old plugins.
    #@nonl
    #@+node:ekr.20100119145629.6109:checkOutline
    def checkOutline (self):

        c = self.c

        g.trace('@bool check_outline_before_save = True',color='blue')

        errors = c.checkOutline(event=None,verbose=True,unittest=False,full=True)
        ok = errors == 0
        if not ok:
            g.es_print('outline not written',color='red')

        return ok
    #@-node:ekr.20100119145629.6109:checkOutline
    #@+node:ekr.20040324080359.1:isReadOnly
    def isReadOnly (self,fileName):

        # self.read_only is not valid for Save As and Save To commands.

        if g.os_path_exists(fileName):
            try:
                if not os.access(fileName,os.W_OK):
                    g.es("can not write: read only:",fileName,color="red")
                    return True
            except Exception:
                pass # os.access() may not exist on all platforms.

        return False
    #@-node:ekr.20040324080359.1:isReadOnly
    #@+node:ekr.20100119145629.6114:writeAllAtFileNodesHelper
    def writeAllAtFileNodesHelper (self):

        '''Write all @file nodes and set orphan bits.
        '''

        c = self.c

        try:
            # 2010/01/19: Do *not* signal failure here.
            # This allows Leo to quit properly.
            c.atFileCommands.writeAll()
            return True
        except Exception:
            g.es_error("exception writing derived files")
            g.es_exception()
            return False
    #@-node:ekr.20100119145629.6114:writeAllAtFileNodesHelper
    #@+node:ekr.20100119145629.6111:writeToFileHelper & helpers
    def writeToFileHelper (self,fileName,toOPML):

        c = self.c ; toZip = c.isZipped
        ok,backupName = self.createBackupFile(fileName)
        if not ok: return False
        fileName,theActualFile = self.createActualFile(fileName,toOPML,toZip)
        self.mFileName = fileName
        self.outputFile = StringIO() # Always write to a string.

        try:
            if toOPML:
                self.putToOPML()
            else:
                self.putLeoFile()
            s = self.outputFile.getvalue()
            g.app.write_Leo_file_string = s # 2010/01/19: always set this.
            if toZip:
                self.writeZipFile(s)
            else:
                theActualFile.write(s)
                theActualFile.close()
                c.setFileTimeStamp(fileName)
                # raise AttributeError # To test handleWriteLeoFileException.
                # Delete backup file.
                if backupName and g.os_path_exists(backupName):
                    self.deleteFileWithMessage(backupName,'backup')
            return True
        except Exception:
            self.handleWriteLeoFileException(
                fileName,backupName,theActualFile)
            return False
    #@+node:ekr.20100119145629.6106:createActualFile
    def createActualFile (self,fileName,toOPML,toZip):

        c = self.c

        if toOPML and not self.mFileName.endswith('opml'):
            fileName = self.mFileName + '.opml'

        if toZip:
            self.toString = True
            theActualFile = None
        else:
            mode = g.choose(g.isPython3,'w','wb')
            try:
                theActualFile = open(fileName,mode)
            except IOError:
                theActualFile = None

        return fileName,theActualFile
    #@-node:ekr.20100119145629.6106:createActualFile
    #@+node:ekr.20031218072017.3047:createBackupFile
    def createBackupFile (self,fileName):

        '''Create a closed backup file and copy fileName to it.
        '''

        c = self.c
        fd,backupName = tempfile.mkstemp(text=False)
        os.close(fd)
        ok = g.utils_rename(c,fileName,backupName)

        if not ok and self.read_only:
            g.es("read only",color="red")

        return ok,backupName
    #@-node:ekr.20031218072017.3047:createBackupFile
    #@+node:ekr.20100119145629.6108:handleWriteLeoFileException
    def handleWriteLeoFileException(self,fileName,backupName,theActualFile):

        c = self.c

        g.es("exception writing:",fileName)
        g.es_exception(full=True)

        if theActualFile:
            theActualFile.close()

        # Delete fileName.
        if fileName and g.os_path_exists(fileName):
            self.deleteFileWithMessage(fileName,'')

        # Rename backupName to fileName.
        if backupName and g.os_path_exists(backupName):
            g.es("restoring",fileName,"from",backupName)
            g.utils_rename(c,backupName,fileName)
        else:
            g.es_print('does not exist!',backupName)

    #@-node:ekr.20100119145629.6108:handleWriteLeoFileException
    #@-node:ekr.20100119145629.6111:writeToFileHelper & helpers
    #@+node:ekr.20100119145629.6110:writeToStringHelper
    def writeToStringHelper (self,fileName):

        try:
            self.mFileName = fileName
            self.outputFile = StringIO()
            self.putLeoFile()
            s = self.outputFile.getvalue()
            g.app.write_Leo_file_string = s
            return True
        except Exception:
            g.es("exception writing:",fileName)
            g.es_exception(full=True)
            g.app.write_Leo_file_string = ''
            return False
    #@-node:ekr.20100119145629.6110:writeToStringHelper
    #@+node:ekr.20070412095520:writeZipFile
    def writeZipFile (self,s):

        # The name of the file in the archive.
        contentsName = g.toEncodedString(
            g.shortFileName(self.mFileName),
            self.leo_file_encoding,reportErrors=True)

        # The name of the archive itself.
        fileName = g.toEncodedString(
            self.mFileName,
            self.leo_file_encoding,reportErrors=True)

        # Write the archive.
        theFile = zipfile.ZipFile(fileName,'w',zipfile.ZIP_DEFLATED)
        theFile.writestr(contentsName,s)
        theFile.close()
    #@-node:ekr.20070412095520:writeZipFile
    #@-node:ekr.20031218072017.3046:write_Leo_file & helpers
    #@+node:ekr.20031218072017.2012:writeAtFileNodes (fileCommands)
    def writeAtFileNodes (self,event=None):

        '''Write all @file nodes in the selected outline.'''

        c = self.c

        changedFiles,atOk = c.atFileCommands.writeAll(writeAtFileNodesFlag=True)

        if changedFiles:
            g.es("auto-saving outline",color="blue")
            c.save() # Must be done to set or clear tnodeList.
    #@-node:ekr.20031218072017.2012:writeAtFileNodes (fileCommands)
    #@+node:ekr.20080801071227.5:writeAtShadowNodes (fileCommands)
    def writeAtShadowNodes (self,event=None):

        '''Write all @file nodes in the selected outline.'''

        c = self.c

        changedFiles,atOk = c.atFileCommands.writeAll(writeAtFileNodesFlag=True)

        if changedFiles:
            g.es("auto-saving outline",color="blue")
            c.save() # Must be done to set or clear tnodeList.
    #@-node:ekr.20080801071227.5:writeAtShadowNodes (fileCommands)
    #@+node:ekr.20031218072017.1666:writeDirtyAtFileNodes (fileCommands)
    def writeDirtyAtFileNodes (self,event=None):

        '''Write all changed @file Nodes.'''

        c = self.c

        changedFiles,atOk = c.atFileCommands.writeAll(writeDirtyAtFileNodesFlag=True)

        if changedFiles:
            g.es("auto-saving outline",color="blue")
            c.save() # Must be done to set or clear tnodeList.
    #@-node:ekr.20031218072017.1666:writeDirtyAtFileNodes (fileCommands)
    #@+node:ekr.20080801071227.6:writeDirtyAtShadowNodes (fileCommands)
    def writeDirtyAtShadowNodes (self,event=None):

        '''Write all changed @shadow Nodes.'''

        c = self.c ; at = c.atFileCommands

        changed = at.writeDirtyAtShadowNodes()

        if changed:
            g.es("auto-saving outline",color="blue")
            c.save() # Must be done to set or clear tnodeList.
    #@-node:ekr.20080801071227.6:writeDirtyAtShadowNodes (fileCommands)
    #@+node:ekr.20031218072017.2013:writeMissingAtFileNodes
    def writeMissingAtFileNodes (self,event=None):

        '''Write all missing @file nodes.'''

        c = self.c ; at = c.atFileCommands ; p = c.p

        if p:
            changedFiles = at.writeMissing(p)
            if changedFiles:
                g.es("auto-saving outline",color="blue")
                c.save() # Must be done to set or clear tnodeList.
    #@-node:ekr.20031218072017.2013:writeMissingAtFileNodes
    #@+node:ekr.20031218072017.3050:writeOutlineOnly
    def writeOutlineOnly (self,event=None):

        '''Write the entire outline without writing any derived files.'''

        c = self.c
        c.endEditing()
        self.write_Leo_file(self.mFileName,outlineOnlyFlag=True)
        g.es('done',color='blue')
    #@-node:ekr.20031218072017.3050:writeOutlineOnly
    #@-node:ekr.20031218072017.3032:Writing
    #@+node:ekr.20080805114146.2:Utils
    #@+node:ekr.20031218072017.1570:assignFileIndices & compactFileIndices
    def assignFileIndices (self):

        """Assign a file index to all tnodes"""

        pass # No longer needed: we assign indices as needed.

    # Indices are now immutable, so there is no longer any difference between these two routines.
    compactFileIndices = assignFileIndices
    #@-node:ekr.20031218072017.1570:assignFileIndices & compactFileIndices
    #@+node:ekr.20080805085257.1:createUaList
    def createUaList (self,aList):

        '''Given aList of pairs (p,torv), return a list of pairs (torv,d)
        where d contains all picklable items of torv.unknownAttributes.'''

        result = []

        for p,torv in aList:
            if type(torv.unknownAttributes) != type({}):
                g.es("ignoring non-dictionary uA for",p,color="blue")
            else:
                # Create a new dict containing only entries that can be pickled.
                d = dict(torv.unknownAttributes) # Copy the dict.

                for key in d:
                    # Just see if val can be pickled.  Suppress any error.
                    ok = self.pickle(torv=torv,val=d.get(key),tag=None)
                    if not ok:
                        del d[key]
                        g.es("ignoring bad unknownAttributes key",key,"in",p.h,color="blue")

                if d:
                    result.append((torv,d),)

        return result
    #@-node:ekr.20080805085257.1:createUaList
    #@+node:ekr.20080805085257.2:pickle
    def pickle (self,torv,val,tag):

        '''Pickle val and return the hexlified result.'''

        trace = False and g.unitTesting
        try:
            s = pickle.dumps(val,protocol=1)
            s2 = binascii.hexlify(s)
            s3 = g.ue(s2,'utf-8')
            if trace: g.trace('\n',
                type(val),val,'\n',type(s),repr(s),'\n',
                type(s2),s2,'\n',type(s3),s3)
            field = ' %s="%s"' % (tag,s3)
            return field

        except pickle.PicklingError:
            if tag: # The caller will print the error if tag is None.
                g.es_print("ignoring non-pickleable value",val,"in",torv,color="blue")
            return ''

        except Exception:
            g.es("fc.pickle: unexpected exception in",torv,color='red')
            g.es_exception()
            return ''
    #@-node:ekr.20080805085257.2:pickle
    #@+node:ekr.20040701065235.2:putDescendentAttributes
    def putDescendentAttributes (self,p):

        nodeIndices = g.app.nodeIndices

        # Create lists of all tnodes whose vnodes are marked or expanded.
        marks = [] ; expanded = []
        for p in p.subtree():
            v = p.v
            if p.isMarked() and p.v not in marks:
                marks.append(v)
            if p.hasChildren() and p.isExpanded() and v not in expanded:
                expanded.append(v)

        result = []
        for theList,tag in ((marks,"marks"),(expanded,"expanded")):
            if theList:
                sList = []
                for v in theList:
                    sList.append("%s," % nodeIndices.toString(v.fileIndex))
                s = ''.join(sList)
                # g.trace(tag,[str(p.h) for p in theList])
                result.append('\n%s="%s"' % (tag,s))

        return ''.join(result)
    #@-node:ekr.20040701065235.2:putDescendentAttributes
    #@+node:ekr.20080805071954.2:putDescendentVnodeUas
    def putDescendentVnodeUas (self,p):

        '''Return the a uA field for descendent vnode attributes,
        suitable for reconstituting uA's for anonymous vnodes.'''

        trace = False
        if trace: g.trace(p.h)

        # Create aList of tuples (p,v) having a valid unknownAttributes dict.
        # Create dictionary: keys are vnodes, values are corresonding archived positions.
        pDict = {} ; aList = []
        for p2 in p.self_and_subtree():
            if hasattr(p2.v,"unknownAttributes"):
                aList.append((p2.copy(),p2.v),)
                pDict[p2.v] = p2.archivedPosition(root_p=p)

        # Create aList of pairs (v,d) where d contains only pickleable entries.
        if aList: aList = self.createUaList(aList)
        if not aList: return ''

        # Create d, an enclosing dict to hold all the inner dicts.
        d = {}
        for v,d2 in aList:
            aList2 = [str(z) for z in pDict.get(v)]
            # g.trace(aList2)
            key = '.'.join(aList2)
            d[key]=d2

        if trace: g.trace(p.h,g.dictToString(d))

        # Pickle and hexlify d
        return d and self.pickle(
            torv=p.v,val=d,tag='descendentVnodeUnknownAttributes') or ''
    #@-node:ekr.20080805071954.2:putDescendentVnodeUas
    #@+node:ekr.20031218072017.2002:putTnodeList
    def putTnodeList (self,v):

        """Put the tnodeList attribute of a vnode."""

        # Remember: entries in the tnodeList correspond to @+node sentinels, _not_ to tnodes!
        nodeIndices = g.app.nodeIndices
        tnodeList = v.tnodeList

        if tnodeList:
            s = ','.join([nodeIndices.toString(v.fileIndex) for v in tnodeList])
            return ' tnodeList="%s"' % (s)
        else:
            return ''
    #@nonl
    #@-node:ekr.20031218072017.2002:putTnodeList
    #@+node:ekr.20050418161620.2:putUaHelper
    def putUaHelper (self,torv,key,val):

        '''Put attribute whose name is key and value is val to the output stream.'''

        # g.trace(key,repr(val),g.callers())

        # New in 4.3: leave string attributes starting with 'str_' alone.
        if key.startswith('str_'):
            if type(val) == type(''):
                attr = ' %s="%s"' % (key,xml.sax.saxutils.escape(val))
                return attr
            else:
                g.es("ignoring non-string attribute",key,"in",torv,color="blue")
                return ''
        else:
            return self.pickle(torv=torv,val=val,tag=key)
    #@-node:ekr.20050418161620.2:putUaHelper
    #@+node:EKR.20040526202501:putUnknownAttributes
    def putUnknownAttributes (self,torv):

        """Put pickleable values for all keys in torv.unknownAttributes dictionary."""

        attrDict = torv.unknownAttributes
        if type(attrDict) != type({}):
            g.es("ignoring non-dictionary unknownAttributes for",torv,color="blue")
            return ''
        else:
            val = ''.join([self.putUaHelper(torv,key,val) for key,val in attrDict.items()])
            # g.trace(torv,attrDict)
            return val
    #@-node:EKR.20040526202501:putUnknownAttributes
    #@+node:ekr.20031218072017.3045:setDefaultDirectoryForNewFiles
    def setDefaultDirectoryForNewFiles (self,fileName):

        """Set c.openDirectory for new files for the benefit of leoAtFile.scanAllDirectives."""

        c = self.c

        if not c.openDirectory:
            theDir = g.os_path_dirname(fileName)
            if theDir and g.os_path_isabs(theDir) and g.os_path_exists(theDir):
                c.openDirectory = c.frame.openDirectory = theDir
    #@-node:ekr.20031218072017.3045:setDefaultDirectoryForNewFiles
    #@+node:ekr.20080412172151.2:updateFixedStatus
    def updateFixedStatus (self):

        c = self.c
        p = g.app.config.findSettingsPosition(c,'@bool fixedWindow')
        if p:
            import leo.core.leoConfig as leoConfig
            parser = leoConfig.settingsTreeParser(c)
            kind,name,val = parser.parseHeadline(p.h)
            if val and val.lower() in ('true','1'):
                val = True
            else:
                val = False
            c.fixed = val

        # g.trace('c.fixed',c.fixed)
    #@-node:ekr.20080412172151.2:updateFixedStatus
    #@-node:ekr.20080805114146.2:Utils
    #@-others

class fileCommands (baseFileCommands):
    """A class creating the fileCommands subcommander."""
    pass
#@nonl
#@-node:ekr.20031218072017.3018:@thin leoFileCommands.py
#@-leo
