#@+leo-ver=4-thin
#@+node:edream.110203113231.730:@thin dump_globals.py
"""Dump Python globals at startup"""

#@@language python
#@@tabwidth -4

import leo.core.leoGlobals as g
import leo.core.leoPlugins as leoPlugins

__version__ = "1.2"

#@+others
#@+node:ekr.20100128091412.5380:init
def init():

    ok = not g.app.unitTesting # Not for unit testing.

    if ok:

        # Register the handlers...
        leoPlugins.registerHandler("start2", onStart)

        g.plugin_signon(__name__)

    return ok
#@nonl
#@-node:ekr.20100128091412.5380:init
#@+node:edream.110203113231.731:onStart
def onStart (tag,keywords):

    g.pr("\nglobals...")
    for s in globals():
        if s not in __builtins__:
            g.pr(s)

    g.pr("\nlocals...")
    for s in locals():
        if s not in __builtins__:
            g.pr(s)
#@-node:edream.110203113231.731:onStart
#@-others
#@-node:edream.110203113231.730:@thin dump_globals.py
#@-leo
