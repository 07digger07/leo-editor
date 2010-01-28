# -*- coding: utf-8 -*-
#@+leo-ver=4-thin
#@+node:danr7.20060912105041.1:@thin paste_as_headlines.py
#@@first

#@@language python
#@@tabwidth -4

#@<< docstring >>
#@+node:danr7.20060912105041.2:<< docstring >>
'''Paste as Headlines 1.0 plugin by Dan Rahmel

This plug-in takes any text is stored in the clipboard and creates new headlines
for each line of text. The paste routine checks to make sure the line of text is not
greater than 50 characters in length. If it is, the routine truncates the headline to
50 characters and pastes the entire line into the body text of that node.

If the plug-in is functioning properly, a "Paste as Headlines" option should appear in
the Edit menu directly under the existing Paste option.
'''
#@-node:danr7.20060912105041.2:<< docstring >>
#@nl
#@<< version history >>
#@+node:danr7.20060912105041.3:<< version history >>
#@+at
# 0.91 - Added headline truncate code
# 0.90 - Created initial plug-in framework
# 1.1 ERK:
# - Converted code to use c.setHead/BodyString rather than the old position 
# setters.
# - Added call to currentNode.expand in paste_as_headlines, enclosed in 
# c.begin/endUpate.
#@-at
#@nonl
#@-node:danr7.20060912105041.3:<< version history >>
#@nl
#@<< imports >>
#@+node:danr7.20060912105041.4:<< imports >>
import leo.core.leoGlobals as g
import leo.core.leoPlugins as leoPlugins
#@-node:danr7.20060912105041.4:<< imports >>
#@nl

__version__ = "1.1"

#@+others
#@+node:ekr.20100128073941.5377:init
def init():

    leoPlugins.registerHandler("create-optional-menus",
        createPasteAsHeadlinesMenu)

    g.plugin_signon(__name__)

    return True # Ok for unit testing: creates menu.
#@-node:ekr.20100128073941.5377:init
#@+node:danr7.20060912105041.5:createPasteAsHeadlinesMenu
def createPasteAsHeadlinesMenu (tag,keywords):

    c = keywords.get("c")

    # Use code to find index number of menu shortcut
    index_label = 'Pa&ste as Headlines'

    # Find index position of ampersand -- index is how shortcut is defined
    amp_index = index_label.find("&")

    # Eliminate ampersand from menu item text
    index_label = index_label.replace("&","")

    # Add 'Word Count...' to the bottom of the Edit menu.
    c.frame.menu.insert('Edit',6,
        label = index_label,
        underline = amp_index,
        command = lambda c = c: paste_as_headlines(c))
#@-node:danr7.20060912105041.5:createPasteAsHeadlinesMenu
#@+node:danr7.20060912105041.6:paste_as_headlines
def paste_as_headlines(c):
    # g.es("Starting...")

    currentPos = c.p 
    clipText = g.app.gui.getTextFromClipboard()

    # Split clipboard text elements into a list
    clipList = clipText.split("\n")

    init_indent = len(clipList[0]) - len(clipList[0].lstrip())
    cur_pos = currentPos.copy()
    ancestors = [(init_indent,cur_pos)]

    for tempHead in clipList:
        indent = len(tempHead) - len(tempHead.lstrip())
        tempHead = tempHead.strip()
        # Make sure list item has some content
        if tempHead:
            if indent > ancestors[-1][0]:
                ancestors.append((indent,cur_pos))
            else:
                while indent < ancestors[-1][0] and indent >= init_indent:
                    ancestors.pop()

            cur_indent = indent

            insertNode = ancestors[-1][1].insertAsLastChild()
            cur_pos = insertNode.copy()

            if len(tempHead)>50:
                c.setHeadString(insertNode,tempHead[:50])
                c.setBodyString(insertNode,tempHead)
            else:
                c.setHeadString(insertNode,tempHead)

    currentPos.expand()
    c.redraw()
#@-node:danr7.20060912105041.6:paste_as_headlines
#@-others
#@-node:danr7.20060912105041.1:@thin paste_as_headlines.py
#@-leo
