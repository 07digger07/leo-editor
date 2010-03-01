#@+leo-ver=4-thin
#@+node:tbrown.20100228141752.5691:@thin leocursor.py
"""A LeoCursor object can walk around on a Leo outline and decode
attributes from nodes.  Node names can be used through . (dot) notation
so ``cursor.Data.Name._B`` for example returns the body text of the
Name node which is a child of the Data node which is a child of the
cursors current location.

See .../plugins/examples/leocursorexample.leo for application.
"""

import re

#@+others
#@+node:tbrown.20100206093439.5452:class AttribManager
class AttribManager(object):

    """Class responsible for reading / writing attributes from
    vnodes for LeoCursor"""

    class NotPresent(Exception):
        pass

    def filterBody(self, b):
        """Return the body string without any parts used to store
        attributes, if this flavor of attribute manager stores attributes
        in the body.  If not, just return the whole body string."""
        raise NotImplemented

    def getAttrib(self, v, what):
        """Get an attribute value from a vnode"""
        raise NotImplemented
#@-node:tbrown.20100206093439.5452:class AttribManager
#@+node:tbrown.20100206093439.5453:class AM_Colon
class AM_Colon(AttribManager):

    """Attributes are in the body text as::

         start-of-line letter letters-or-numbers colon space(s) attribute-value

    Both::

      foo:

    and::

      foo: all this is the value

    are attributes (first one is value==''), but::

      foo:value

    is not (because there's no space after the colon).

    """

    pattern = re.compile(r"^([A-Za-z][A-Za-z0-9_]*)(:)(\s+(\S.*))*$")

    def filterBody(self, b):
        return '\n'.join(
           [i for i in b.split('\n')
            if not self.pattern.match(i)])

    def getAttrib(self, v, what):

        for i in v.b.split('\n'):

            m = self.pattern.match(i)

            if m and m.group(1) == what:
                m = m.group(3)
                if m:
                    m = m.strip()
                else:
                    m = ''  # don't return None
                return m

        raise self.NotPresent
#@-node:tbrown.20100206093439.5453:class AM_Colon
#@+node:tbrown.20100206093439.5455:class AM_CapColon
class AM_CapColon(AM_Colon):

    """Like AM_Colon, but first letter must be capital."""

    pattern = r"^([A-Z][A-Za-z0-9_]*:)(\s+(\S.*))*$"
#@-node:tbrown.20100206093439.5455:class AM_CapColon
#@+node:tbrown.20100206093439.5451:class LeoCursor
class LeoCursor(object):

    """See module docs."""

    #@    @+others
    #@+node:tbrown.20100205200824.5424:__init__
    def __init__(self, v, other=None):

        if other:
            self.__root = other.__root
            self.__attribManagers = list(other.__attribManagers)
        else:
            self.__root = v
            self.__attribManagers = []

        self.__v = v
    #@-node:tbrown.20100205200824.5424:__init__
    #@+node:tbrown.20100205200824.9978:__iter__
    def __iter__(self):

        for i in self.__v.children:
            yield self.__at(i)
    #@-node:tbrown.20100205200824.9978:__iter__
    #@+node:tbrown.20100206093439.5447:__call__
    def __call__(self, path):

        """'Group .*/June/Event .*' - all the events that descend from June
        that dsecend from a Group"""

        stems = [self]
        steps = path.split('/')

        while steps:

            step = steps.pop(0)
            # print 'S',step
            if not step.strip():
                continue

            try:
                step_int = int(step)
            except ValueError:
                step_int = False

            new_stems = []

            for stem in stems:

                if step_int is not False:

                    new_stems.append(self.__at(
                        (stem.__v.children or [])[step_int]))

                elif step.startswith('@'):

                    for i in self.__attribManagers:
                        try:
                            new_stems.append(i.getAttrib(stem.__v, step[1:]))
                        except AttribManager.NotPresent:
                            pass

                else:

                    for i in stem.__v.children or []:
                        #print 'V', step, i.h
                        if re.match(step, i.h):
                            new_stems.append(self.__at(i))
                            #print 'N',i.h

            stems = new_stems

        return stems
    #@-node:tbrown.20100206093439.5447:__call__
    #@+node:tbrown.20100205200824.5425:__getattr__
    def __getattr__(self, what):

        if what == '_H':

            return str(self.__v.h)

        elif what == '_B':

            return self.__body()

        elif what == '_U':

            return self.__v.u

        elif what == '_GNX':  # or _G?

            return self.__v.gnx

        elif what == '_R':
            return self.__at(self.__root)


        for child in self.__v.children:
            if child.h == what:
                return self.__at(child)

        for i in self.__attribManagers:
            t = what[1:] if what.startswith('_') else what
            try:
                return i.getAttrib(self.__v, t)
            except AttribManager.NotPresent:
                pass

    #@-node:tbrown.20100205200824.5425:__getattr__
    #@+node:tbrown.20100208110238.12228:__getitem__
    def __getitem__(self, what):
        """which can be a slice object, we let builtin list take care of it"""

        if isinstance(what, int):
            return self.__at(self.__v.children[what])
        else:
            return [self.__at(i) for i in self.__v.children[what]]
    #@-node:tbrown.20100208110238.12228:__getitem__
    #@+node:tbrown.20100206093439.5449:__body
    def __body(self):

        b = str(self.__v.b)

        # filter out all attribs
        for i in self.__attribManagers:
            b = i.filterBody(b)

        return b
    #@-node:tbrown.20100206093439.5449:__body
    #@+node:tbrown.20100206093439.5450:__at
    def __at(self, v):

        return LeoCursor(v, self)
    #@-node:tbrown.20100206093439.5450:__at
    #@+node:tbrown.20100206093439.5457:_setAttribManagers
    def _setAttribManagers(self, mngrs):

        self.__attribManagers = list(mngrs)
    #@-node:tbrown.20100206093439.5457:_setAttribManagers
    #@-others
#@nonl
#@-node:tbrown.20100206093439.5451:class LeoCursor
#@-others
#@-node:tbrown.20100228141752.5691:@thin leocursor.py
#@-leo
