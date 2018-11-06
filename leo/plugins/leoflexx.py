# -*- coding: utf-8 -*-
#@+leo-ver=5-thin
#@+node:ekr.20181103094900.1: * @file leoflexx.py
#@@first
#@@language python
#@@tabwidth -4
'''
A Stand-alone prototype for Leo using flexx.
'''
import os
from flexx import flx
lean_python = False
base_class = flx.PyComponent if lean_python else flx.Widget
#@+others
#@+node:ekr.20181105154956.1: **  functions
#@+node:ekr.20181103151350.1: *3* init
def init():
    # At present, leoflexx is not a true plugin.
    # I am executing leoflexx.py from an external script.
    return False
#@+node:ekr.20181105091545.1: *3* open_bridge
def open_bridge():
    '''Can't be in JS.'''
    import leo.core.leoBridge as leoBridge
    bridge = leoBridge.controller(gui = None,
        loadPlugins = False,
        readSettings = False,
        silent = False,
        tracePlugins = False,
        verbose = False, # True: prints log messages.
    )
    if not bridge.isOpen():
        print('Error opening leoBridge')
        return
    g = bridge.globals()
    path = g.os_path_finalize_join(g.app.loadDir, '..', 'core', 'LeoPy.leo')
    if not os.path.exists(path):
        print('open_bridge: does not exist:', path)
        return
    c = bridge.openLeoFile(path)
    ### runUnitTests(c, g)
    return c, g
#@+node:ekr.20181105160448.1: *3* find_body
def find_body(c):
    for p in c.p.self_and_siblings():
        if p.b.strip():
            return p.b
    return ''
#@+node:ekr.20181105095150.1: *3* make_outline_list
def make_outline_list(c):
    result = []
    for p in c.all_positions():
        result.append((p.archivedPosition(), p.h),)
    return result
#@+node:ekr.20181104082144.1: ** class LeoBody
base_url = 'https://cdnjs.cloudflare.com/ajax/libs/ace/1.2.6/'
flx.assets.associate_asset(__name__, base_url + 'ace.js')
flx.assets.associate_asset(__name__, base_url + 'mode-python.js')
flx.assets.associate_asset(__name__, base_url + 'theme-solarized_dark.js')

class LeoBody(base_class):
    
    """ A CodeEditor widget based on Ace.
    """

    CSS = """
    .flx-CodeEditor > .ace {
        width: 100%;
        height: 100%;
    }
    """
    if lean_python:
        
        def init(self):
            flx.Widget(flex=1).apply_style('background: blue')
    else:
        
        def init(self):
            global body, window
            self.ace = window.ace.edit(self.node, "editor")
            self.ace.setValue(body)
            self.ace.navigateFileEnd()  # otherwise all lines highlighted
            self.ace.setTheme("ace/theme/solarized_dark")
            self.ace.getSession().setMode("ace/mode/python")

        @flx.reaction('size')
        def __on_size(self, *events):
            self.ace.resize()
#@+node:ekr.20181104174357.1: ** class LeoGui (stub)
class LeoGui (object):
    
    def runMainLoop(self):
        '''The main loop for the flexx gui.'''

       
#@+node:ekr.20181104082149.1: ** class LeoLog
class LeoLog(base_class):

    CSS = """
    .flx-CodeEditor > .ace {
        width: 100%;
        height: 100%;
    }
    """
    if lean_python:
        # def init(self):
            # flx.Widget(flex=1).apply_style('background: red') # 'overflow-y: scroll;'
        def init(self):
            # global window
            from pscript import window
            # print('WINDOW', repr(window))
            # https://ace.c9.io/#nav=api
            self.ace = window.ace.edit(self.node, "editor")
            ### self.ace.setValue("import os\n\ndirs = os.walk")
            self.ace.navigateFileEnd()  # otherwise all lines highlighted
            self.ace.setTheme("ace/theme/solarized_dark")
            ### self.ace.getSession().setMode("ace/mode/python")
    else:
        def init(self):
            global window
            # https://ace.c9.io/#nav=api
            self.ace = window.ace.edit(self.node, "editor")
            ### self.ace.setValue("import os\n\ndirs = os.walk")
            self.ace.navigateFileEnd()  # otherwise all lines highlighted
            self.ace.setTheme("ace/theme/solarized_dark")
            ### self.ace.getSession().setMode("ace/mode/python")

        @flx.reaction('size')
        def __on_size(self, *events):
            self.ace.resize()
#@+node:ekr.20181104082130.1: ** class LeoMainWindow
class LeoMainWindow(base_class):
    
    def init(self):
        global main_window
        main_window = self
        if lean_python:
            # flex is not a valid kwarg for PyComponents.
            with flx.VBox():
                with flx.HBox(flex=1):
                    self.tree = LeoTree()
                    self.log = LeoLog()
                self.body = LeoBody()
                self.minibuffer = LeoMiniBuffer()
                self.status_line = LeoStatusLine()
        else:
            with flx.VBox():
                with flx.HBox(flex=1):
                    self.tree = LeoTree(flex=1)
                    self.log = LeoLog(flex=1)
                self.body = LeoBody(flex=1)
                self.minibuffer = LeoMiniBuffer()
                self.status_line = LeoStatusLine()
#@+node:ekr.20181104082154.1: ** class LeoMiniBuffer
class LeoMiniBuffer(base_class):
    
    def init(self): 
        with flx.HBox():
            flx.Label(text='Minibuffer')
            self.widget = flx.LineEdit(
                flex=1, placeholder_text='Enter command')
        self.widget.apply_style('background: yellow')
#@+node:ekr.20181104082201.1: ** class LeoStatusLine
class LeoStatusLine(base_class):
    
    def init(self):
        with flx.HBox():
            flx.Label(text='Status Line')
            self.widget = flx.LineEdit(flex=1, placeholder_text='Status')
        self.widget.apply_style('background: green')
#@+node:ekr.20181104082138.1: ** class LeoTree
class LeoTree(base_class):

    CSS = '''
    .flx-TreeWidget {
        background: #000;
        color: white;
        /* background: #ffffec; */
        /* Leo Yellow */
        /* color: #afa; */
    }
    '''
    def init(self):
        with flx.TreeWidget(flex=1, max_selected=1) as self.tree:
            self.make()

    #@+others
    #@+node:ekr.20181105045657.1: *3* tree.make
    def make(self):
        
        global outline_list
        stack = []
        for archived_position, h in outline_list:
            n = len(archived_position)
            if n == 1:
                item = flx.TreeItem(text=h, checked=None, collapsed=True)
                stack = [item]
            elif n in (2, 3):
                # Fully expanding the stack takes too long.
                stack = stack[:n-1]
                with stack[-1]:
                    item = flx.TreeItem(text=h, checked=None, collapsed=True)
                    stack.append(item)
    #@+node:ekr.20181104080854.3: *3* tree.on_event
    if not lean_python:

        @flx.reaction(
            'tree.children**.checked',
            'tree.children**.selected',
            'tree.children**.collapsed',
        )
        def on_event(self, *events):
            for ev in events:
                id_ = ev.source.title or ev.source.text
                kind = '' if ev.new_value else 'un-'
                text = '%10s: %s' % (id_, kind + ev.type)
                assert text
                ### self.label.set_html(text + '<br />' + self.label.html)
    #@-others
#@-others
if __name__ == '__main__':
    # Define globals in Python.
    c, g = open_bridge()
    outline_list = make_outline_list(c)
    body = find_body(c)
    main_window = None
    # Start the JS code. c not allowed.
    flx.launch(LeoMainWindow, runtime='firefox-browser')
    flx.run()
#@-leo
