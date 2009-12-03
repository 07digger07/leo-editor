#! /usr/bin/env python
#@+leo-ver=4-thin
#@+node:ekr.20031218072017.2605:@thin runLeo.py 
#@@first

"""Entry point for Leo in Python."""

#@@language python
#@@tabwidth -4

#@<< imports and inits >>
#@+node:ekr.20080921091311.1:<< imports and inits >>
# import pdb ; pdb = pdb.set_trace
import optparse
import os
import sys
import traceback

try:
    import Tkinter ; Tkinter.wantobjects = 0
        # An ugly hack for Tk/Tkinter 8.5
        # See http://sourceforge.net/forum/message.php?msg_id=4078577
except ImportError:
    try:
        import tkinter ; tkinter.wantobject = 0
    except ImportError:
        pass

path = os.getcwd()
if path not in sys.path:
    # print('appending %s to sys.path' % path)
    sys.path.append(path)

# Import leoGlobals, but do NOT set g.
import leo.core.leoGlobals as leoGlobals

try:
    # This will fail if True/False are not defined.
    import leo.core.leoGlobals as g
except ImportError:
    print("runLeo.py: can not import leo.core.leoGlobals")
    raise
except Exception:
    print("runLeo.py: unexpected exception: import leo.core.leoGlobals")
    raise

# Set leoGlobals.g here, rather than in leoGlobals.py.
leoGlobals.g = leoGlobals

import leo.core.leoApp as leoApp

# Create the app.
leoGlobals.app = leoApp.LeoApp()

# **now** we can set g.
g = leoGlobals
assert(g.app)

# Do early inits
import leo.core.leoNodes as leoNodes
import leo.core.leoConfig as leoConfig

# There is a circular dependency between leoCommands and leoEditCommands.
import leo.core.leoCommands as leoCommands

# New in Leo 4.5 b3: make sure we call the new leoPlugins.init top-level function.
# This prevents a crash when run is called repeatedly from IPython's lleo extension.
import leo.core.leoPlugins as leoPlugins
leoPlugins.init()

# Do all other imports.
import leo.core.leoGui as leoGui
#@-node:ekr.20080921091311.1:<< imports and inits >>
#@nl

#@+others
#@+node:ekr.20031218072017.1934:run & helpers
def run(fileName=None,pymacs=None,*args,**keywords):

    """Initialize and run Leo"""

    trace = False and not g.unitTesting
    if trace: print ('runLeo.run: sys.argv %s' % sys.argv)

    # Phase 1: before loading plugins.
    # Scan options, set directories and read settings.
    if not isValidPython(): return
    fn,relFn,script,versionFlag = doPrePluginsInit(fileName,pymacs)

    # Phase 2: load plugins.
    g.doHook("start1") # Plugins may create a gui.
    if g.app.killed: return

    # Phase 3: after loading plugins. Create a frame.
    ok = doPostPluginsInit(args,fn,relFn,script,versionFlag)
    if ok and not versionFlag: g.app.gui.runMainLoop()
#@+node:ekr.20090519143741.5915:doPrePluginsInit & helpers
def doPrePluginsInit(fileName,pymacs):

    '''
    Scan options, set directories and read settings.'''

    g.computeStandardDirectories()
    adjustSysPath()
    fileName2,gui,script,versionFlag,windowFlag = scanOptions()
    if fileName2: fileName = fileName2
    # print ('runLeo.run: sys.argv %s' % sys.argv)
    # print ('runLeo.run: fileName %s' % fileName)
    if pymacs: script,windowFlag = None,False
    verbose = script is None
    initApp(verbose)
    fileName,relativeFileName = getFileName(fileName,script)
    reportDirectories(verbose)
    # Read settings *after* setting g.app.config and *before* opening plugins.
    # This means if-gui has effect only in per-file settings.
    g.app.config.readSettingsFiles(fileName,verbose)
    g.app.setEncoding()
    g.app.setGlobalDb()
    if gui is None:
        if script and not windowFlag:
            # Bug fix: 2009/10/1: use null gui for scripts.
            createNullGuiWithScript(script)
        else:
            g.app.createDefaultGui(__file__)
    else:
        createSpecialGui(gui,pymacs,script,windowFlag)
    return fileName,relativeFileName,script,versionFlag
#@+node:ekr.20080921060401.4:createSpecialGui & helper
def createSpecialGui(gui,pymacs,script,windowFlag):

    tag = ''

    if False and g.isPython3:
        # Create the curses gui.
        leoPlugins.loadOnePlugin ('cursesGui',verbose=True)
    elif pymacs:
        createNullGuiWithScript(None)
    # elif jyLeo:
        # import leo.core.leoSwingGui as leoSwingGui
        # g.app.gui = leoSwingGui.swingGui()
    elif script:
        if windowFlag:
            g.app.createTkGui(tag) # Creates global windows.
            g.app.gui.setScript(script)
            sys.args = []
        else:
            createNullGuiWithScript(script)
    elif gui == 'qt':   g.app.createQtGui(tag)
    elif gui == 'tk':   g.app.createTkGui(tag)
    elif gui == 'wx':   g.app.createWxGui(tag)
#@+node:ekr.20031218072017.1938:createNullGuiWithScript
def createNullGuiWithScript (script):

    g.app.batchMode = True
    g.app.gui = leoGui.nullGui("nullGui")
    g.app.gui.setScript(script)
#@-node:ekr.20031218072017.1938:createNullGuiWithScript
#@-node:ekr.20080921060401.4:createSpecialGui & helper
#@+node:ekr.20070306085724:adjustSysPath
def adjustSysPath ():

    '''Adjust sys.path to enable imports as usual with Leo.

    This method is no longer needed:

    1. g.importModule will import from the
       'external' or 'extensions' folders as needed
       without altering sys.path.

    2  Plugins now do fully qualified imports.
    '''

    # leoDirs = ('config','doc','extensions','modes','plugins','core','test')

    # for theDir in leoDirs:
        # path = g.os_path_finalize_join(g.app.loadDir,'..',theDir)
        # if path not in sys.path:
            # sys.path.append(path)
#@nonl
#@-node:ekr.20070306085724:adjustSysPath
#@+node:ekr.20071117060958:getFileName & helper
def getFileName (fileName,script):

    '''Return the filename from sys.argv.'''

    # import pdb ; pdb.set_trace()

    if g.isPython3:
        ### Testing only.
        # fileName = r'c:\leo.repo\trunk\leo\test\test.leo'
        # assert g.os_path_exists(fileName)
        pass
    elif script:
        fileName = None
    elif fileName:
        pass
    else:
        # Bug fix: 2008/10/1
        if sys.platform.startswith('win'):
            if len(sys.argv) > 1:
                fileName = ' '.join(sys.argv[1:])
            else:
                fileName = None
        else:
            fileName = len(sys.argv) > 1 and sys.argv[-1]

    return completeFileName(fileName)
#@+node:ekr.20041124083125:completeFileName
def completeFileName (fileName):

    trace = False
    if trace: print('completeFileName',fileName)

    if not (fileName and fileName.strip()):
        return None,None

    # This does not depend on config settings.
    try:
        if sys.platform.lower().startswith('win'):
            fileName = g.toUnicode(fileName,'mbcs')
        else:
            fileName = g.toUnicode(fileName,'utf-8')
    except Exception: pass

    relativeFileName = fileName
    fileName = g.os_path_finalize(fileName)

    junk,ext = g.os_path_splitext(fileName)

    # Bug fix: don't add .leo to existing files.
    if g.os_path_exists(fileName):
        pass # use the fileName as is.
    elif ext != '.leo':
        fileName = fileName + ".leo"
        relativeFileName = relativeFileName + ".leo"

    if trace: print('completeFileName',fileName)

    return fileName,relativeFileName
#@-node:ekr.20041124083125:completeFileName
#@-node:ekr.20071117060958:getFileName & helper
#@+node:ekr.20080921091311.2:initApp
def initApp (verbose):

    # Force the user to set g.app.leoID.
    g.app.setLeoID(verbose=verbose)
    g.app.config = leoConfig.configClass()
    g.app.nodeIndices = leoNodes.nodeIndices(g.app.leoID)
#@-node:ekr.20080921091311.2:initApp
#@+node:ekr.20041130093254:reportDirectories
def reportDirectories(verbose):

    if verbose:
        for kind,theDir in (
            ("load",g.app.loadDir),
            ("global config",g.app.globalConfigDir),
            ("home",g.app.homeDir),
        ):
            g.es("%s dir:" % (kind),theDir,color="blue")
#@-node:ekr.20041130093254:reportDirectories
#@+node:ekr.20091007103358.6061:scanOptions
def scanOptions():

    '''Handle all options and remove them from sys.argv.'''
    trace = False

    # Note: this automatically implements the --help option.
    parser = optparse.OptionParser()
    parser.add_option('-c', '--config', dest="one_config_path")
    parser.add_option('-f', '--file',   dest="fileName")
    parser.add_option('--gui',          dest="gui",help = 'gui to use (qt/tk/qttabs)')
    #parser.add_option('--help',         action="store_true",dest="help_option")
    parser.add_option('--ipython',      action="store_true",dest="use_ipython")
    parser.add_option('--no-cache',     action="store_true",dest='no_cache')
    parser.add_option('--silent',       action="store_true",dest="silent")
    parser.add_option('--script',       dest="script")
    parser.add_option('--script-window',dest="script_window")
    parser.add_option('--version',      action="store_true",dest="version")

    # Parse the options, and remove them from sys.argv.
    options, args = parser.parse_args()
    sys.argv = [sys.argv[0]] ; sys.argv.extend(args)
    # print('scanOptions',sys.argv)

    # Handle the args...

    # -c or --config
    path = options.one_config_path
    if path:
        path = g.os_path_finalize_join(os.getcwd(),path)
        if g.os_path_exists(path):
            g.app.oneConfigFilename = path
        else:
            g.es_print('Invalid -c option: file not found:',path,color='red')

    # --no-cache
    if options.no_cache:
        g.trace('disabling caching')
        g.enableDB = False

    # -f or --file
    fileName = options.fileName

    # --gui
    gui = options.gui
    g.app.qt_use_tabs = False
    if gui:
        gui = gui.lower()
        if gui == 'qttabs':
            gui = 'qt'
            g.app.qt_use_tabs = True

        if gui not in ('tk','qt','wx'):
            g.trace('unknown gui: %s' % gui)
            gui = None

    # --ipython
    g.app.useIpython = options.use_ipython

    # --script
    script_path = options.script
    script_path_w = options.script_window
    if script_path and script_path_w:
        parser.error("--script and script-window are mutually exclusive")

    script_name = script_path or script_path_w
    if script_name:
        script_name = g.os_path_finalize_join(g.app.loadDir,script_name)
        try:
            f = None
            try:
                if trace: print("scan_options: script: %s" % script_name)
                f = open(script_name,'r')
                script = f.read()
            except IOError:
                print("can not open script file: %s" % script_name)
                script = None
        finally:
            if f: f.close()
    else:
        script = None
        if trace: print('scanOptions: no script')

    # --silent
    g.app.silentMode = options.silent
    # g.trace('silentMode',g.app.silentMode)

    # --version: print the version and exit.
    versionFlag = options.version

    # Compute the return values.
    windowFlag = script and script_path_w
    return fileName,gui,script,versionFlag,windowFlag
#@-node:ekr.20091007103358.6061:scanOptions
#@-node:ekr.20090519143741.5915:doPrePluginsInit & helpers
#@+node:ekr.20090519143741.5917:doPostPluginsInit & helpers
def doPostPluginsInit(args,fileName,relativeFileName,script,versionFlag):

    '''Return True if the frame was created properly.'''

    if g.app.gui == None:
        g.app.createQtGui(fileName='core')

    # We can't print the signon until we know the gui.
    g.app.computeSignon() # Set app.signon/signon2 for commanders.

    if versionFlag:
        print(g.app.signon)
        return

    g.init_sherlock(args)  # Init tracing and statistics.
    if g.app and g.app.use_psyco: startPsyco()

    # Clear g.app.initing _before_ creating the frame.
    g.app.initing = False # "idle" hooks may now call g.app.forceShutdown.

    # Create the main frame.  Show it and all queued messages.
    c,frame = createFrame(fileName,relativeFileName,script)
    if not frame: return False

    # Do the final inits.
    finishInitApp(c)
    p = c.p
    g.app.initComplete = True
    g.doHook("start2",c=c,p=p,v=p,fileName=fileName)
    if c.config.getBool('allow_idle_time_hook'):
        g.enableIdleTimeHook()
    initFocusAndDraw(c,fileName)
    return True
#@+node:ekr.20031218072017.1624:createFrame (runLeo.py)
def createFrame (fileName,relativeFileName,script):

    """Create a LeoFrame during Leo's startup process."""

    # New in Leo 4.6: support for 'default_leo_file' setting.
    defaultFileName = None
    if not fileName and not script:
        fileName = g.app.config.getString(c=None,setting='default_leo_file')
        fileName = g.os_path_finalize(fileName)
        if fileName and g.os_path_exists(fileName):
            g.es_print('opening default_leo_file:',fileName,color='blue')
            defaultFileName = fileName

    # Try to create a frame for the file.
    if fileName and g.os_path_exists(fileName):
        ok, frame = g.openWithFileName(relativeFileName or fileName,None)
        if ok: return frame.c,frame

    # Create a _new_ frame & indicate it is the startup window.
    if not fileName: fileName = defaultFileName

    c,frame = g.app.newLeoCommanderAndFrame(
        fileName=fileName,
        relativeFileName=relativeFileName,
        initEditCommanders=True)

    assert frame.c == c and c.frame == frame
    frame.setInitialWindowGeometry()
    frame.resizePanesToRatio(frame.ratio,frame.secondary_ratio)
    frame.startupWindow = True
    if c.chapterController:
        c.chapterController.finishCreate()
        c.setChanged(False) # Clear the changed flag set when creating the @chapters node.
    # Call the 'new' hook for compatibility with plugins.
    g.doHook("new",old_c=None,c=c,new_c=c)

    g.createMenu(c,fileName)
    g.finishOpen(c) # Calls c.redraw.

    # Report the failure to open the file.
    if fileName:
        g.es_print("file not found:",fileName,color='red')

    return c,frame
#@-node:ekr.20031218072017.1624:createFrame (runLeo.py)
#@+node:ekr.20080921060401.5:finishInitApp (runLeo.py)
def finishInitApp(c):

    g.app.trace_gc          = c.config.getBool('trace_gc')
    g.app.trace_gc_calls    = c.config.getBool('trace_gc_calls')
    g.app.trace_gc_verbose  = c.config.getBool('trace_gc_verbose')

    if g.app.disableSave:
        g.es("disabling save commands",color="red")

#@-node:ekr.20080921060401.5:finishInitApp (runLeo.py)
#@+node:ekr.20080921060401.6:initFocusAndDraw
def initFocusAndDraw(c,fileName):

    w = g.app.gui.get_focus(c)

    if not fileName:
        c.redraw()

    # Respect c's focus wishes if posssible.
    if w != c.frame.body.bodyCtrl and w != c.frame.tree.canvas:
        c.bodyWantsFocus()
        c.k.showStateAndMode(w)

    c.outerUpdate()
#@-node:ekr.20080921060401.6:initFocusAndDraw
#@+node:ekr.20040411081633:startPsyco
def startPsyco ():

    try:
        import psyco
        if 0:
            theFile = r"c:\prog\test\psycoLog.txt"
            g.es("psyco now logging to:",theFile,color="blue")
            psyco.log(theFile)
            psyco.profile()
        psyco.full()
        g.es("psyco now running",color="blue")

    except ImportError:
        g.app.use_psyco = False

    except:
        g.pr("unexpected exception importing psyco")
        g.es_exception()
        g.app.use_psyco = False
#@-node:ekr.20040411081633:startPsyco
#@-node:ekr.20090519143741.5917:doPostPluginsInit & helpers
#@+node:ekr.20031218072017.1936:isValidPython
def isValidPython():

    if sys.platform == 'cli':
        return True

    minimum_python_version = '2.4'

    message = """\
Leo requires Python %s or higher.
You may download Python from
http://python.org/download/
""" % minimum_python_version

    try:
        version = '.'.join([str(sys.version_info[i]) for i in (0,1,2)])
        # ok = g.CheckVersion(version,'2.4.0') # Soon.
        ok = g.CheckVersion(version,minimum_python_version)
        if not ok:
            print(message)
            try:
                # g.app.gui does not exist yet.
                import Tkinter as Tk
                #@                << define emergency dialog class >>
                #@+node:ekr.20080822065427.8:<< define emergency dialog class >>
                class emergencyDialog:

                    """A class that creates an Tkinter dialog with a single OK button."""

                    #@    @+others
                    #@+node:ekr.20080822065427.9:__init__ (emergencyDialog)
                    def __init__(self,title,message):

                        """Constructor for the leoTkinterDialog class."""

                        self.answer = None # Value returned from run()
                        self.title = title
                        self.message=message

                        self.buttonsFrame = None # Frame to hold typical dialog buttons.
                        self.defaultButtonCommand = None  # Command to call when user closes the window by clicking the close box.
                        self.frame = None # The outermost frame.
                        self.root = None # Created in createTopFrame.
                        self.top = None # The toplevel Tk widget.

                        self.createTopFrame()
                        buttons = {"text":"OK","command":self.okButton,"default":True}, # Singleton tuple.
                        self.createButtons(buttons)
                        self.top.bind("<Key>", self.onKey)
                    #@-node:ekr.20080822065427.9:__init__ (emergencyDialog)
                    #@+node:ekr.20080822065427.12:createButtons
                    def createButtons (self,buttons):

                        """Create a row of buttons.

                        buttons is a list of dictionaries containing the properties of each button."""

                        assert(self.frame)
                        self.buttonsFrame = f = Tk.Frame(self.top)
                        f.pack(side="top",padx=30)

                        # Buttons is a list of dictionaries, with an empty dictionary at the end if there is only one entry.
                        buttonList = []
                        for d in buttons:
                            text = d.get("text","<missing button name>")
                            isDefault = d.get("default",False)
                            underline = d.get("underline",0)
                            command = d.get("command",None)
                            bd = g.choose(isDefault,4,2)

                            b = Tk.Button(f,width=6,text=text,bd=bd,underline=underline,command=command)
                            b.pack(side="left",padx=5,pady=10)
                            buttonList.append(b)

                            if isDefault and command:
                                self.defaultButtonCommand = command

                        return buttonList
                    #@-node:ekr.20080822065427.12:createButtons
                    #@+node:ekr.20080822065427.14:createTopFrame
                    def createTopFrame(self):

                        """Create the Tk.Toplevel widget for a leoTkinterDialog."""

                        self.root = Tk.Tk()
                        self.top = Tk.Toplevel(self.root)
                        self.top.title(self.title)
                        self.root.withdraw()

                        self.frame = Tk.Frame(self.top)
                        self.frame.pack(side="top",expand=1,fill="both")

                        label = Tk.Label(self.frame,text=message,bg='white')
                        label.pack(pady=10)
                    #@-node:ekr.20080822065427.14:createTopFrame
                    #@+node:ekr.20080822065427.10:okButton
                    def okButton(self):

                        """Do default click action in ok button."""

                        self.top.destroy()
                        self.top = None

                    #@-node:ekr.20080822065427.10:okButton
                    #@+node:ekr.20080822065427.21:onKey
                    def onKey(self,event):

                        """Handle Key events in askOk dialogs."""

                        self.okButton()

                        return "break"
                    #@-node:ekr.20080822065427.21:onKey
                    #@+node:ekr.20080822065427.16:run
                    def run (self):

                        """Run the modal emergency dialog."""

                        self.top.geometry("%dx%d%+d%+d" % (300,200,50,50))
                        self.top.lift()

                        self.top.grab_set() # Make the dialog a modal dialog.
                        self.root.wait_window(self.top)
                    #@-node:ekr.20080822065427.16:run
                    #@-others
                #@-node:ekr.20080822065427.8:<< define emergency dialog class >>
                #@nl
                d = emergencyDialog(title='Python Version Error',message=message)
                d.run()
            except Exception:
                pass
        return ok
    except Exception:
        print("isValidPython: unexpected exception: g.CheckVersion")
        traceback.print_exc()
        return 0
#@-node:ekr.20031218072017.1936:isValidPython
#@-node:ekr.20031218072017.1934:run & helpers
#@+node:ekr.20031218072017.2607:profile_leo
#@+at 
#@nonl
# To gather statistics, do the following in a Python window, not idle:
# 
#     import leo
#     import leo.core.runLeo as runLeo
#     runLeo.profile_leo()  (this runs leo)
#     load leoDocs.leo (it is very slow)
#     quit Leo.
#@-at
#@@c

def profile_leo ():

    """Gather and print statistics about Leo"""

    import cProfile as profile
    import pstats
    import leo.core.leoGlobals as g
    import os

    # name = r"c:\leo.repo\trunk\leo\test\leoProfile.txt"
    # name = g.os_path_finalize_join(g.app.loadDir,'..','test','leoProfile.txt')
    theDir = os.getcwd()

    # On Windows, name must be a plain string. An apparent cProfile bug.
    name = str(g.os_path_normpath(g.os_path_join(theDir,'leoProfile.txt')))
    print ('profiling to %s' % name)
    profile.run('import leo ; leo.run()',name)
    p = pstats.Stats(name)
    p.strip_dirs()
    p.sort_stats('module','calls','time','name')
    reFiles='leoAtFile.py:|leoFileCommands.py:|leoGlobals.py|leoNodes.py:'
    p.print_stats(reFiles)

prof = profile_leo
#@-node:ekr.20031218072017.2607:profile_leo
#@-others

if __name__ == "__main__":
    run()

#@-node:ekr.20031218072017.2605:@thin runLeo.py 
#@-leo
