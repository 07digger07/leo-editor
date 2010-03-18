#@+leo-ver=4-thin
#@+node:ekr.20100103093121.5329:@thin stickynotes.py
#@<< docstring >>
#@+node:vivainio2.20091008133028.5821:<< docstring >>
'''Simple "sticky notes" feature (popout editors)

Adds the following (``Alt-X``) commands:

``stickynote``
  pop out current node as a sticky note
``stickynoter``
  pop out current node as a rich text note
``stickynoteenc``
  pop out current node as an encrypted note
``stickynoteenckey``
  enter a new en/decryption key

Sticky notes are synchronized (both ways) with their parent Leo node.

Encrypted mode requires the python-crypto module.

The first time you open a note in encrypted mode you'll be asked for a pass phrase.  That phrase will be used for the rest of the session, you can change it with ``Alt-X`` ``stickynoteenckey``, but probably won't need to.

The encrypted note is stored in base64 encoded *encrypted* text in the parent Leo node, if you forget the pass phrase there's no way to un-encrypt it again.  Also, you must not edit the text in the Leo node.

When **creating an encrypted note**, you should **start with and empty node**.  If you want to encrypt text that already exists in a node, select-all cut it to empty the node, then paste it into the note.

'''
#@-node:vivainio2.20091008133028.5821:<< docstring >>
#@nl

__version__ = '0.0'
#@<< version history >>
#@+node:vivainio2.20091008133028.5822:<< version history >>
#@@killcolor
#@+at
# 
# Put notes about each version here.
#@-at
#@nonl
#@-node:vivainio2.20091008133028.5822:<< version history >>
#@nl

#@<< imports >>
#@+node:vivainio2.20091008133028.5823:<< imports >>
import leo.core.leoGlobals as g
from leo.core import leoPlugins

# Whatever other imports your plugins uses.

g.assertUi('qt')

import sys
import webbrowser

encOK = False
try:
    from Crypto.Cipher import AES
    from Crypto.Hash import MD5, SHA
    import base64
    import textwrap
    __ENCKEY = [None]
    encOK = True
except ImportError:
    pass

from PyQt4.QtCore import (QSize, QString, QVariant, Qt, SIGNAL, QTimer)
from PyQt4.QtGui import (QAction, QApplication, QColor, QFont,
        QFontMetrics, QIcon, QKeySequence, QMenu, QPixmap, QTextCursor,
        QTextCharFormat, QTextBlockFormat, QTextListFormat,QTextEdit,
        QPlainTextEdit, QInputDialog)
#@nonl
#@-node:vivainio2.20091008133028.5823:<< imports >>
#@nl

#@+others
#@+node:vivainio2.20091008140054.14555:styling
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

def decorate_window(w):
    w.setStyleSheet(stickynote_stylesheet)
    w.setWindowIcon(QIcon(g.app.leoDir + "/Icons/leoapp32.png"))    
    w.resize(600, 300)

#@-node:vivainio2.20091008140054.14555:styling
#@+node:vivainio2.20091008133028.5824:init
def init ():

    ok = True

    if ok:
        #leoPlugins.registerHandler('start2',onStart2)
        g.plugin_signon(__name__)

    g.app.stickynotes = {}    
    return ok
#@-node:vivainio2.20091008133028.5824:init
#@+node:ville.20091008210853.7616:class FocusingPlainTextEdit
class FocusingPlaintextEdit(QPlainTextEdit):

    def __init__(self, focusin, focusout):
        QPlainTextEdit.__init__(self)        
        self.focusin = focusin
        self.focusout = focusout

    def focusOutEvent (self, event):
        #print "focus out"
        self.focusout()

    def focusInEvent (self, event):        
        self.focusin()

    def closeEvent(self, event):
        event.accept()
        self.focusout()


#@-node:ville.20091008210853.7616:class FocusingPlainTextEdit
#@+node:ville.20091023181249.5264:class SimpleRichText
class SimpleRichText(QTextEdit):
    def __init__(self, focusin, focusout):
        QTextEdit.__init__(self)        
        self.focusin = focusin
        self.focusout = focusout
        self.createActions()

        #self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

    def focusOutEvent ( self, event ):
        #print "focus out"
        self.focusout()

    def focusInEvent ( self, event ):        
        self.focusin()


    def closeEvent(self, event):
        event.accept()        

    def createActions(self):
        self.boldAct = QAction(self.tr("&Bold"), self)
        self.boldAct.setCheckable(True)
        self.boldAct.setShortcut(self.tr("Ctrl+B"))
        self.boldAct.setStatusTip(self.tr("Make the text bold"))
        self.connect(self.boldAct, SIGNAL("triggered()"), self.setBold)
        self.addAction(self.boldAct)

        boldFont = self.boldAct.font()
        boldFont.setBold(True)
        self.boldAct.setFont(boldFont)

        self.italicAct = QAction(self.tr("&Italic"), self)
        self.italicAct.setCheckable(True)
        self.italicAct.setShortcut(self.tr("Ctrl+I"))
        self.italicAct.setStatusTip(self.tr("Make the text italic"))
        self.connect(self.italicAct, SIGNAL("triggered()"), self.setItalic)
        self.addAction(self.italicAct)

    def setBold(self):
        format = QTextCharFormat()
        if self.boldAct.isChecked():
                weight = QFont.Bold
        else:
                weight = QFont.Normal
        format.setFontWeight(weight)
        self.setFormat(format)

    def setItalic(self):
        format = QTextCharFormat()
        #format.setFontItalic(self.__italic.isChecked())
        format.setFontItalic(self.italicAct.isChecked())
        self.setFormat(format)

    def setUnderline(self):
        format = QTextCharFormat()
        format.setFontUnderline(self.__underline.isChecked())
        self.setFormat(format)

    def setFormat(self, format):
        self.textCursor().mergeCharFormat(format)
        self.mergeCurrentCharFormat(format)

    def bold(self):
        print("bold")

    def italic(self):
        print("italic")



#@-node:ville.20091023181249.5264:class SimpleRichText
#@+node:vivainio2.20091008133028.5825:g.command('stickynote')
@g.command('stickynote')
def stickynote_f(event):
    """ Launch editable 'sticky note' for the node """

    c= event['c']
    p = c.p
    v = p.v
    def focusin():
        #print "focus in"
        if v is c.p.v:
            nf.setPlainText(v.b)
            nf.setWindowTitle(p.h)
            nf.dirty = False


    def focusout():
        #print "focus out"
        if not nf.dirty:
            return
        v.b = nf.toPlainText()
        v.setDirty()
        nf.dirty = False
        p = c.p
        if p.v is v:
            c.selectPosition(c.p)


    nf = FocusingPlaintextEdit(focusin, focusout)
    nf.dirty = False
    decorate_window(nf)
    nf.setWindowTitle(p.h)
    nf.setPlainText(p.b)
    p.setDirty()

    def textchanged_cb():
        nf.dirty = True

    nf.connect(nf,
        SIGNAL("textChanged()"),textchanged_cb)

    nf.show()

    g.app.stickynotes[p.gnx] = nf
#@-node:vivainio2.20091008133028.5825:g.command('stickynote')
#@+node:ville.20091023181249.5266:g.command('stickynoter')
@g.command('stickynoter')
def stickynoter_f(event):
    """ Launch editable 'sticky note' for the node """

    c= event['c']
    p = c.p
    v = p.v
    def focusin():
        print("focus in")
        if v is c.p.v:
            nf.setHtml(v.b)
            nf.setWindowTitle(p.h)
            nf.dirty = False


    def focusout():
        print("focus out")
        if not nf.dirty:
            return
        v.b = nf.toHtml()
        v.setDirty()
        nf.dirty = False
        p = c.p
        if p.v is v:
            c.selectPosition(c.p)


    nf = SimpleRichText(focusin, focusout)  # not LessSimpleRichText
    nf.dirty = False
    decorate_window(nf)
    nf.setWindowTitle(p.h)
    nf.setHtml(p.b)
    p.setDirty()

    def textchanged_cb():
        nf.dirty = True

    nf.connect(nf,
        SIGNAL("textChanged()"),textchanged_cb)

    nf.show()

    g.app.stickynotes[p.gnx] = nf
#@-node:ville.20091023181249.5266:g.command('stickynoter')
#@+node:tbrown.20100120100336.7829:g.command('stickynoteenc')
if encOK:
    @g.command('stickynoteenc')
    def stickynoteenc_f(event):
        """ Launch editable 'sticky note' for the encrypted node """

        if not encOK:
            g.es('no en/decryption - need python-crypto module')
            return

        if not __ENCKEY[0]:
            sn_getenckey()

        c= event['c']
        p = c.p
        v = p.v
        def focusin():
            #print "focus in"
            if v is c.p.v:
                nf.setPlainText(sn_decode(v.b))
                nf.setWindowTitle(p.h)
                nf.dirty = False

        def focusout():
            #print "focus out"
            if not nf.dirty:
                return
            v.b = sn_encode(str(nf.toPlainText()))
            v.setDirty()
            nf.dirty = False
            p = c.p
            if p.v is v:
                c.selectPosition(c.p)


        nf = FocusingPlaintextEdit(focusin, focusout)
        nf.dirty = False
        decorate_window(nf)
        nf.setWindowTitle(p.h)
        nf.setPlainText(sn_decode(p.b))
        p.setDirty()

        def textchanged_cb():
            nf.dirty = True

        nf.connect(nf,
            SIGNAL("textChanged()"),textchanged_cb)

        nf.show()

        g.app.stickynotes[p.gnx] = nf
#@-node:tbrown.20100120100336.7829:g.command('stickynoteenc')
#@+node:tbrown.20100120100336.7830:sn_de/encode
if encOK:
    def sn_decode(s):
        return AES.new(__ENCKEY[0]).decrypt(base64.b64decode(s)).strip()

    def sn_encode(s):
        pad = ' '*(16-len(s)%16)
        return '\n'.join(textwrap.wrap(
            base64.b64encode(AES.new(__ENCKEY[0]).encrypt(s+pad)),
            break_long_words = True
        ))

    @g.command('stickynoteenckey')
    def sn_getenckey(dummy=None):
        txt,ok = QInputDialog.getText(None, 'Enter key', 'Enter key.\nData lost if key is lost.')
        if not ok:
            return
        # arbitrary kludge to convert string to 256 bits - don't change
        sha = SHA.new()
        md5 = MD5.new()
        sha.update(txt)
        md5.update(txt)
        __ENCKEY[0] = sha.digest()[:16] + md5.digest()[:16]
        if len(__ENCKEY[0]) != 32:
            raise Exception("sn_getenckey failed to build key")
#@-node:tbrown.20100120100336.7830:sn_de/encode
#@-others
#@nonl
#@-node:ekr.20100103093121.5329:@thin stickynotes.py
#@-leo
