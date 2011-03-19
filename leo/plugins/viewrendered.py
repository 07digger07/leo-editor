#@+leo-ver=5-thin
#@+node:tbrown.20100318101414.5990: * @file viewrendered.py
#@+<< docstring >>
#@+node:tbrown.20100318101414.5991: ** << docstring >>
''' Creates a window for *live* rendering of rst, html, etc.  (Qt only).

viewrendered.py creates the following (``Alt-X``) commands:

``viewrendered``
    opens a new window where the current body text is rendered as HTML
    (if it starts with '<'), or otherwise reStructuredText.
``viewrendered-big``
    as above, but zoomed in, useful for presentations
``viewrendered-html``
    displays the html source generated from reStructuredText, useful for
    debugging

``viewrendered`` sets the process current directory (os.chdir()) to the path
to the node being rendered, to allow relative paths to work in
``.. image::`` directives.

reStructuredText errors and warnings may be shown.  For example, both::

    Heading
    -------

    `This` is **really** a line of text.

and::

    <h1>Heading<h1>

    <tt>This</tt> is <b>really</b> a line of text.

will look something like:

**Heading**

`This` is **really** a line of text.

'''
#@-<< docstring >>

__version__ = '0.1'

#@+<< imports >>
#@+node:tbrown.20100318101414.5993: ** << imports >>
import leo.core.leoGlobals as g

g.assertUi('qt')

import sys
import os
import webbrowser

try:
    from docutils.core import publish_string
    from docutils.utils import SystemMessage
    got_docutils = True
except ImportError:
    got_docutils = False

from PyQt4.QtCore import (QSize, QVariant, Qt, SIGNAL, QTimer)
from PyQt4.QtGui import (QAction, QApplication, QColor, QFont,
        QFontMetrics, QIcon, QKeySequence, QMenu, QPixmap, QTextCursor,
        QTextCharFormat, QTextBlockFormat, QTextListFormat,QTextEdit,
        QPlainTextEdit, QInputDialog)
#@-<< imports >>
#@+<< define stylesheet >>
#@+node:ekr.20110317024548.14377: ** << define stylesheet >>
stickynote_stylesheet = """
/* The body pane */
QPlainTextEdit {
    background-color: #fdf5f5; /* A kind of pink. */
    selection-color: white;
    selection-background-color: lightgrey;
    font-family: DejaVu Sans Mono;
    /* font-family: Courier New; */
    font-size: 12px;
    font-weight: normal; /* normal,bold,100,..,900 */
    font-style: normal; /* normal,italic,oblique */
}
"""
#@-<< define stylesheet >>

#@+at
# To do:
# - Create rendering pane automatically on startup, loading free_layout as needed.
# - Use the rendering pane for plugin docstrings.
# - Make viewrendered-big/html work.
# - Options: viewrendered-create-pane-on-startup, viewrendered-pane-color.
# - Save/restore viewrendered pane size.
# - Generalize: allow registration of other kinds of renderers.
#   In particular, allow different kinds of widgets in the viewrendered pane.
# - Support @html, @graphic, @movie, @networkx.
# - Support uA's that indicate the kind of rendering desired.
# - Eliminate the call to c.frame.equalSizedPanes in create_renderer (in free_layout).
#   That is, be able to specify the pane ratios from user options.
#@@c

controllers = {}
    # Keys are c.hash(): values are PluginControllers

#@+others
#@+node:tbrown.20100318101414.5994: ** decorate_window
def decorate_window(w):
    
    w.setStyleSheet(stickynote_stylesheet)
    w.setWindowIcon(QIcon(g.app.leoDir + "/Icons/leoapp32.png"))    
    w.resize(600, 300)
#@+node:tbrown.20100318101414.5995: ** init
def init ():

    # g.viewrendered_count = 0
    
    g.plugin_signon(__name__)
    g.registerHandler('after-create-leo-frame',onCreate)

    return True
#@+node:ekr.20110317024548.14376: ** onCreate
def onCreate (tag, keys):
    
    global controllers
    
    c = keys.get('c')
    if c:
        controllers[c.hash()] = ViewRenderedController(c)
#@+node:ekr.20110317024548.14375: ** class ViewRenderedController
class ViewRenderedController:
    
    '''A class to control rendering in a rendering pane.'''
    
    #@+others
    #@+node:ekr.20110317080650.14380: *3* ctor
    def __init__ (self,c):
            
        self.c = c
        self.w = w = QTextEdit()
        w.setReadOnly(True)
        
        c.viewrendered = self # For free_layout

        self.active = False
        self.inited = False
        self.gnx = 0
        self.kind = 'normal'
        self.length = 0         # The length of previous p.b.
        self.splitter = None    # The splitter containing the rendering pane.
        self.splitter_index = None  # The index of the rendering pane in the splitter.
    #@+node:ekr.20110317080650.14381: *3* activate
    def activate (self):
        
        pc = self
        
        if pc.inited: return
        
        # if not self.w:
            # ### To be supplied by the free_layout plugin.
            # w = QTextEdit()
            # w.setReadOnly(True)
        
        pc.inited = True
        pc.active = True
        
        g.registerHandler('select2',pc.update)
        g.registerHandler('idle',pc.update)
        
        # Enable the idle-time hook if it has not already been enabled.
        if not g.app.idleTimeHook:
            g.enableIdleTimeHook(idleTimeDelay=1000)
    #@+node:ekr.20110317080650.14382: *3* deactivate
    def deactivate (self):
        
        pc = self
        
        # Never disable the idle-time hook: other plugins may need it.
        g.unregisterHandler('select2',pc.update)
        g.unregisterHandler('idle',pc.update)
        
        pc.active = False
    #@+node:ekr.20110318080425.14394: *3* embed
    def embed (self):
        
        '''Use the free_layout plugin to embed self.w in a splitter.'''
        
        c = self.c
        fl_pc = hasattr(c,'free_layout') and c.free_layout
        if fl_pc:
            fl_pc.create_renderer(self.w)
    #@+node:ekr.20110318080425.14388: *3* has/set_renderer
    def has_renderer (self):
        
        '''Return True if the renderer pane is visible.'''
        
        return self.splitter

    def set_renderer (self,splitter,index):
        
        self.splitter = splitter
        self.splitter_index = index
        g.trace(splitter,index)
    #@+node:ekr.20110317080650.14384: *3* show & hide
    def hide (self):
        
        pc = self ; w = pc.w
        pc.deactivate()
        w.hide()
        
    def show (self,html=False):
        
        pc = self ; w = pc.w
        pc.activate()
        pc.update(tag='view',keywords={'c':self.c,'html':html})
        w.show()
    #@+node:ekr.20101112195628.5426: *3* update
    def update(self,tag,keywords):
        
        # if tag != 'idle': g.trace(tag,keywords)
        pc = self ; c = pc.c ; w = pc.w
        if c != keywords.get('c'): return
        if not pc.active: return

        html = keywords.get('html')
        p = c.currentPosition()
        s = p.b.strip()
        w.setWindowTitle(p.h)

        if self.gnx == p.v.gnx and len(s) == self.length:
            return  # no change

        self.gnx = p.v.gnx
        self.length = len(s)
        msg = ''

        if got_docutils and not s.startswith('<'):

            path = g.scanAllAtPathDirectives(c,p) or c.getNodePath(p)
            if not os.path.isdir(path):
                path = os.path.dirname(path)
            if os.path.isdir(path):
                os.chdir(path)

            try:
                s = publish_string(s,writer_name='html')
                s = g.toUnicode(s) # 2011/03/15
            except SystemMessage as sm:
                if 0:
                    g.trace(sm)
                    print(sm.args)
                if 1:
                    msg = sm.args[0]
                    if 'SEVERE' in msg or 'FATAL' in msg:
                        s = 'RST rendering failed with\n\n  %s\n\n%s' % (msg,s)

        if html or msg:
            w.setPlainText(s)
        else:
            w.setHtml(s)
    #@+node:ekr.20110317024548.14379: *3* view
    def view(self,big=False,html=False):
        
        pc = self
        
        self.embed()
        pc.show(html=html)
        if big:
            pc.w.zoomIn(4)
    #@-others
#@+node:tbrown.20100318101414.5998: ** g.command('viewrendered')
@g.command('viewrendered')
def viewrendered(event):
    """Open render view for commander"""

    c = event.get('c')
    if c:
        # ViewRendered(c)
        pc = controllers.get(c.hash())
        if pc: pc.view()
#@+node:tbrown.20101127112443.14856: ** g.command('viewrendered-html')
@g.command('viewrendered-html')
def viewrendered(event):
    """Open view of html which would be rendered"""

    c = event.get('c')
    if c:
        # ViewRendered(c, view_html=True)
        pc = controllers.get(c.hash())
        if pc: pc.view(html=True)
#@+node:tbrown.20101127112443.14854: ** g.command('viewrendered-big')
@g.command('viewrendered-big')
def viewrendered(event):
    """Open render view for commander, with big text

    (useful for presentations)

    """

    c = event.get('c')
    if c:
        # vr = ViewRendered(c)
        # vr.zoomIn(4)
        pc = controllers.get(c.hash())
        if pc: pc.view(big=True)
#@+node:ekr.20110317080650.14383: ** g.command('hide-rendering-pane')
@g.command('hide-rendering-pane')
def hide_rendering_pane(event):
    
    '''Hide the rendering pane, but do not delete it.'''

    c = event.get('c')
    if c:
        pc = controllers.get(c.hash())
        if pc: pc.hide()
#@+node:ekr.20110317080650.14386: ** g.command('show-rendering-pane')
@g.command('show-rendering-pane')
def show_rendering_pane(event):
    
    '''Hide the rendering pane, but do not delete it.'''

    c = event.get('c')
    if c:
        pc = controllers.get(c.hash())
        if pc: pc.view()
#@-others
#@-leo
