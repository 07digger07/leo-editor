import leo.core.leoGlobals as g
from leo.core.leoQt import QtCore, QtGui, QtWidgets, QtConst

import markdown
from webkitview import LEP_WebKitView as HtmlView
# from plaintextview import LEP_PlainTextView as TextView
def to_html(text):
    """to_html - convert to HTML

    :param str text: markdown text to convert
    :return: html
    :rtype: str
    """

    return markdown.markdown(
        text,
        extensions=[
            'markdown.extensions.extra',
            'markdown.extensions.codehilite',
        ]
    )
class LEP_MarkdownView(HtmlView):
    """LEP_MarkdownView - 
    """
    lep_type = "MARKDOWN"
    lep_name = "Markdown(.py) View"
    def __init__(self, c=None, lep=None, *args, **kwargs):
        """set up"""
        super(LEP_MarkdownView, self).__init__(c=c, lep=lep, *args, **kwargs)
        self.c = c
        self.lep = lep
    def new_position(self, p):
        """new_position - update for new position

        :param Leo position p: new position
        """
        if self.lep.recurse:
            self.setHtml(to_html(g.getScript(self.c, p, useSelectedText=False, useSentinels=False)))
        else:
            self.setHtml(to_html(p.b))
    def update_position(self, p):
        """update_position - update for current position

        :param Leo position p: current position
        """
        # h = self.horizontalScrollBar().value()
        # v = self.verticalScrollBar().value()
        self.new_position(p)
        # self.horizontalScrollBar().setValue(h)
        # self.verticalScrollBar().setValue(v)
if 0:
    class LEP_MarkdownHtmlView(TextView):
        """LEP_MarkdownHtmlView - view the HTML for markdown
        """
        lep_type = "MARKDOWN-HTML"
        lep_name = "Markdown(.py) Html View"
        def __init__(self, c=None, lep=None, *args, **kwargs):
            """set up"""
            super(LEP_MarkdownHtmlView, self).__init__(c=c, lep=lep, *args, **kwargs)
            self.c = c
            self.lep = lep
        def new_position(self, p):
            """new_position - update for new position

            :param Leo position p: new position
            """
            if self.lep.recurse:
                self.setText(to_html(g.getScript(self.c, p, useSelectedText=False, useSentinels=False)))
            else:
                self.setText(to_html(p.b))
