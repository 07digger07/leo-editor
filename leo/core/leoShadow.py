# -*- coding: utf-8 -*-
#@+leo-ver=4-thin
#@+node:ekr.20080708094444.1:@thin leoShadow.py
#@@first

#@<< docstring >>
#@+node:ekr.20080708094444.78:<< docstring >>
'''
leoShadow.py


This code allows users to use Leo with files which contain no sentinels
and still have information flow in both directions between outlines and
derived files.

Private files contain sentinels: they live in the Leo-shadow subdirectory.
Public files contain no sentinels: they live in the parent (main) directory.

When Leo first reads an @shadow we create a file without sentinels in the regular directory.

The slightly hard thing to do is to pick up changes from the file without
sentinels, and put them into the file with sentinels.



Settings:
- @string shadow_subdir (default: LeoFolder): name of the shadow directory.

- @string shadow_prefix (default: x): prefix of shadow files.
  This prefix allows the shadow file and the original file to have different names.
  This is useful for name-based tools like py.test.
'''
#@-node:ekr.20080708094444.78:<< docstring >>
#@nl
#@<< imports >>
#@+node:ekr.20080708094444.52:<< imports >>
import leo.core.leoGlobals as g

import difflib
import os
import unittest
#@-node:ekr.20080708094444.52:<< imports >>
#@nl

#@@language python
#@@tabwidth -4
#@@pagewidth 80

#@+others
#@+node:ekr.20080708094444.80:class shadowController
class shadowController:

    '''A class to manage @shadow files'''

    #@    @+others
    #@+node:ekr.20080708094444.79: x.ctor
    def __init__ (self,c,trace=False,trace_writers=False):

        self.c = c

        # Configuration...
        self.shadow_subdir = c.config.getString('shadow_subdir') or '.leo_shadow'
        self.shadow_prefix = c.config.getString('shadow_prefix') or ''

        # Munch shadow_subdir
        self.shadow_subdir = g.os_path_normpath(self.shadow_subdir)

        # Debugging...
        self.trace = trace
        self.trace_writers = trace_writers  # True: enable traces in all sourcewriters.

        # Error handling...
        self.errors = 0
        self.last_error  = '' # The last error message, regardless of whether it was actually shown.

        # Support for goto-line.
        self.line_mapping = []
    #@-node:ekr.20080708094444.79: x.ctor
    #@+node:ekr.20080711063656.1:x.File utils
    #@+node:ekr.20080711063656.7:x.baseDirName
    def baseDirName (self):

        x = self ; c = x.c ; filename = c.fileName()

        if filename:
            return g.os_path_dirname(c.os_path_finalize(filename))
        else:
            self.error('Can not compute shadow path: .leo file has not been saved')
            return None
    #@nonl
    #@-node:ekr.20080711063656.7:x.baseDirName
    #@+node:ekr.20080711063656.4:x.dirName and pathName
    def dirName (self,filename):

        '''Return the directory for filename.'''

        x = self

        return g.os_path_dirname(x.pathName(filename))

    def pathName (self,filename):

        '''Return the full path name of filename.'''

        x = self ; c = x.c ; theDir = x.baseDirName()

        return theDir and c.os_path_finalize_join(theDir,filename)
    #@nonl
    #@-node:ekr.20080711063656.4:x.dirName and pathName
    #@+node:ekr.20080712080505.3:x.isSignificantPublicFile
    def isSignificantPublicFile (self,fn):

        '''This tells the atFile.read logic whether to import a public file or use an existing public file.'''

        return g.os_path_exists(fn) and g.os_path_isfile(fn) and g.os_path_getsize(fn) > 10
    #@-node:ekr.20080712080505.3:x.isSignificantPublicFile
    #@+node:ekr.20080710082231.19:x.makeShadowDirectory
    def makeShadowDirectory (self,fn):

        '''Make a shadow directory for the **public** fn.'''

        x = self ; path = x.shadowDirName(fn)

        if not g.os_path_exists(path):

            # Force the creation of the directories.
            g.makeAllNonExistentDirectories(path,c=None,force=True)

        return g.os_path_exists(path) and g.os_path_isdir(path)
    #@-node:ekr.20080710082231.19:x.makeShadowDirectory
    #@+node:ekr.20080711063656.2:x.rename
    def rename (self,src,dst,mode=None,silent=False):

        x = self ; c = x.c

        ok = g.utils_rename (c,src,dst,mode=mode,verbose=not silent)
        if not ok:
            x.error('can not rename %s to %s' % (src,dst),silent=silent)

        return ok
    #@-node:ekr.20080711063656.2:x.rename
    #@+node:ekr.20080713091247.1:x.replaceFileWithString
    def replaceFileWithString (self,fn,s):

        '''Replace the file with s if s is different from theFile's contents.

        Return True if theFile was changed.
        '''

        trace = False and not g.unitTesting
        x = self
        exists = g.os_path_exists(fn)

        if exists:
            # Read the file.  Return if it is the same.
            s2,e = g.readFileIntoString(fn)
            if s2 is None:
                return False
            if s == s2:
                if not g.unitTesting: g.es('unchanged:',fn)
                return False

        # Issue warning if directory does not exist.
        theDir = g.os_path_dirname(fn)
        if theDir and not g.os_path_exists(theDir):
            if not g.unitTesting:
                x.error('not written: %s directory not found' % fn)
            return False

        # Replace the file.
        try:
            f = open(fn,'wb')
            f.write(g.toEncodedString(s))
            if trace: g.trace('fn',fn,
                '\nlines...\n%s' %(g.listToString(g.splitLines(s))),
                '\ncallers',g.callers(4))
            f.close()
            if not g.unitTesting:
                # g.trace('created:',fn,g.callers())
                if exists:  g.es('wrote:',fn)
                else:       g.es('created:',fn)
            return True
        except IOError:
            x.error('unexpected exception writing file: %s' % (fn))
            g.es_exception()
            return False
    #@-node:ekr.20080713091247.1:x.replaceFileWithString
    #@+node:ekr.20080711063656.6:x.shadowDirName and shadowPathName
    def shadowDirName (self,filename):

        '''Return the directory for the shadow file corresponding to filename.'''

        x = self

        return g.os_path_dirname(x.shadowPathName(filename))

    def shadowPathName (self,filename):

        '''Return the full path name of filename, resolved using c.fileName()'''

        x = self ; c = x.c

        baseDir = x.baseDirName()
        fileDir = g.os_path_dirname(filename)

        return baseDir and c.os_path_finalize_join(
                baseDir,
                fileDir, # Bug fix: honor any directories specified in filename.
                x.shadow_subdir,
                x.shadow_prefix + g.shortFileName(filename))
    #@-node:ekr.20080711063656.6:x.shadowDirName and shadowPathName
    #@+node:ekr.20080711063656.3:x.unlink
    def unlink (self, filename,silent=False):

        '''Unlink filename from the file system.
        Give an error on failure.'''

        x = self

        ok = g.utils_remove(filename, verbose=not silent)
        if not ok:
            x.error('can not delete %s' % (filename),silent=silent)

        return ok
    #@-node:ekr.20080711063656.3:x.unlink
    #@-node:ekr.20080711063656.1:x.File utils
    #@+node:ekr.20080708192807.1:x.Propagation
    #@+node:ekr.20080708094444.35:x.check_the_final_output
    def check_the_final_output(self, new_private_lines, new_public_lines, sentinel_lines, marker):
        """
        Check that we produced a valid output.

        Input:
            new_targetlines:   the lines with sentinels which produce changed_lines_without_sentinels.
            sentinels:         new_targetlines should include all the lines from sentinels.

        checks:
            1. new_targetlines without sentinels must equal changed_lines_without_sentinels.
            2. the sentinel lines of new_targetlines must match 'sentinels'
        """
        new_public_lines2, new_sentinel_lines2 = self.separate_sentinels (new_private_lines, marker)

        ok = True
        if new_public_lines2 != new_public_lines:
            last_line2 = new_public_lines2[-1]
            last_line  = new_public_lines[-1]
            if (
                new_public_lines2[:-1] == new_public_lines[:-1] and
                last_line2 == last_line + '\n'
            ):
                ok = True
            else:
                ok = False
                self.show_error(
                    lines1 = new_public_lines2,
                    lines2 = new_public_lines,
                    message = "Error in updating public file!",
                    lines1_message = "new public lines (derived from new private lines)",
                    lines2_message = "new public lines")
            # g.trace(g.callers())

        if new_sentinel_lines2 != sentinel_lines:
            ok = False
            self.show_error(
                lines1 = sentinel_lines,
                lines2 = new_sentinel_lines2,
                message = "Sentinals not preserved!",
                lines1_message = "old sentinels",
                lines2_message = "new sentinels")

        # if ok: g.trace("success!")
    #@-node:ekr.20080708094444.35:x.check_the_final_output
    #@+node:ekr.20080708094444.37:x.copy_sentinels
    def copy_sentinels(self,reader,writer,marker,limit):

        '''Copy sentinels from reader to writer while reader.index() < limit.'''

        x = self
        start = reader.index()
        while reader.index() < limit:
            line = reader.get()
            if marker.isSentinel(line):
                if marker.isVerbatimSentinel(line):
                    # We are *deleting* non-sentinel lines, so we must delete @verbatim sentinels!
                    # We must **extend** the limit to get the next line.
                    if reader.index() < limit + 1:
                        # Skip the next line, whatever it is.
                        # Important: this **deletes** the @verbatim sentinel,
                        # so this is a exception to the rule that sentinels are preserved.
                        line = reader.get()
                    else:
                        x.verbatim_error()
                else:
                    # g.trace('put line',repr(line))
                    writer.put(line,tag='copy sent %s:%s' % (start,limit))
    #@-node:ekr.20080708094444.37:x.copy_sentinels
    #@+node:ekr.20080708094444.38:x.propagate_changed_lines (the main loop)
    def propagate_changed_lines(self,new_public_lines,old_private_lines,marker,p=None):

        '''Propagate changes from 'new_public_lines' to 'old_private_lines.

        We compare the old and new public lines, create diffs and
        propagate the diffs to the new private lines, copying sentinels as well.

        We have two invariants:
        1. We *never* delete any sentinels.
           New at 2010/01/07: Replacements preserve sentinel locations.
        2. Insertions that happen at the boundary between nodes will be put at
           the end of a node.  However, insertions must always be done within sentinels.
        '''

        trace = False and not g.unitTesting
        verbose = True
        x = self
        # mapping tells which line of old_private_lines each line of old_public_lines comes from.
        old_public_lines, mapping = self.strip_sentinels_with_map(old_private_lines,marker)

        #@    << init vars >>
        #@+node:ekr.20080708094444.40:<< init vars >>
        new_private_lines_wtr = self.sourcewriter(self)
        # collects the contents of the new file.

        new_public_lines_rdr = self.sourcereader(self,new_public_lines)
            # Contains the changed source code.

        old_public_lines_rdr = self.sourcereader(self,old_public_lines)
            # this is compared to new_public_lines_rdr to find out the changes.

        old_private_lines_rdr = self.sourcereader(self,old_private_lines) # lines_with_sentinels)
            # This is the file which is currently produced by Leo, with sentinels.

        # Check that all ranges returned by get_opcodes() are contiguous
        old_old_j, old_i2_modified_lines = -1,-1

        tag = old_i = old_j = new_i = new_j = None
        #@nonl
        #@-node:ekr.20080708094444.40:<< init vars >>
        #@nl
        #@    << define print_tags >>
        #@+node:ekr.20080708094444.39:<< define print_tags >>
        def print_tags(tag, old_i, old_j, new_i, new_j, message):

            sep1 = '=' * 10 ; sep2 = '-' * 20

            g.pr('\n',sep1,message,sep1,p and p.h)

            g.pr('\n%s: old[%s:%s] new[%s:%s]' % (tag,old_i,old_j,new_i,new_j))

            g.pr('\n',sep2)

            table = (
                (old_private_lines_rdr,'old private lines'),
                (old_public_lines_rdr,'old public lines'),
                (new_public_lines_rdr,'new public lines'),
                (new_private_lines_wtr,'new private lines'),
            )

            for f,tag in table:
                f.dump(tag)
                g.pr(sep2)


        #@-node:ekr.20080708094444.39:<< define print_tags >>
        #@nl

        delim1,delim2 = marker.getDelims()
        sm = difflib.SequenceMatcher(None,old_public_lines,new_public_lines)
        prev_old_j = 0 ; prev_new_j = 0

        for tag,old_i,old_j,new_i,new_j in sm.get_opcodes():

            #@        << About this loop >>
            #@+node:ekr.20080708192807.2:<< about this loop >>
            #@+at
            # 
            # This loop writes all output lines using a single writer: 
            # new_private_lines_wtr.
            # 
            # The output lines come from two, and *only* two readers:
            # 
            # 1. old_private_lines_rdr delivers the complete original sources. 
            # All
            #    sentinels and unchanged regular lines come from this reader.
            # 
            # 2. new_public_lines_rdr delivers the new, changed sources. All 
            # inserted or
            #    replacement text comes from this reader.
            # 
            # Each time through the loop, the following are true:
            # 
            # - old_i is the index into old_public_lines of the start of the 
            # present SequenceMatcher opcode.
            # 
            # - mapping[old_i] is the index into old_private_lines of the 
            # start of the same opcode.
            # 
            # At the start of the loop, the call to copy_sentinels effectively 
            # skips (deletes)
            # all previously unwritten non-sentinel lines in 
            # old_private_lines_rdr whose index
            # is less than mapping[old_i].
            # 
            # As a result, the opcode handlers do not need to delete elements 
            # from the
            # old_private_lines_rdr explicitly. This explains why opcode 
            # handlers for the
            # 'insert' and 'delete' opcodes are identical.
            #@-at
            #@-node:ekr.20080708192807.2:<< about this loop >>
            #@nl

            # Verify that SequenceMatcher never leaves gaps.
            if old_i != prev_old_j: # assert old_i == prev_old_j
                x.error('can not happen: gap in old: %s %s' % (old_i,prev_old_j))
            if new_i != prev_new_j: # assert new_i == prev_new_j
                x.error('can not happen: gap in new: %s %s' % (new_i,prev_new_j))

            #@        << Handle the opcode >>
            #@+node:ekr.20080708192807.5:<< Handle the opcode >>
            # Do not copy sentinels if a) we are inserting and b) limit is at the end of the old_private_lines.
            # In this special case, we must do the insert before the sentinels.
            limit=mapping[old_i]

            if trace: g.trace('tag',tag,'old_i',old_i,'limit',limit)

            if tag == 'equal':
                # Copy sentinels up to the limit = mapping[old_i]
                self.copy_sentinels(old_private_lines_rdr,new_private_lines_wtr,marker,limit=limit)

                # Copy all lines (including sentinels) from the old private file to the new private file.
                start = old_private_lines_rdr.index() # Only used for tag.
                while old_private_lines_rdr.index() <= mapping[old_j-1]:
                    line = old_private_lines_rdr.get()
                    new_private_lines_wtr.put(line,tag='%s %s:%s' % (
                        tag,start,mapping[old_j-1]))

                # Ignore all new lines up to new_j: the same lines (with sentinels) have just been written.
                new_public_lines_rdr.sync(new_j)

            elif tag == 'insert':
                if limit < old_private_lines_rdr.size():
                    self.copy_sentinels(old_private_lines_rdr,new_private_lines_wtr,marker,limit=limit)
                # All unwritten lines from old_private_lines_rdr up to mapping[old_i] have already been ignored.
                # Copy lines from new_public_lines_rdr up to new_j.
                start = new_public_lines_rdr.index() # Only used for tag.
                while new_public_lines_rdr.index() < new_j:
                    line = new_public_lines_rdr.get()
                    if marker.isSentinel(line):
                        new_private_lines_wtr.put(
                            '%s@verbatim%s\n' % (delim1,delim2),
                            tag='%s %s:%s' % ('new sent',start,new_j))
                    new_private_lines_wtr.put(line,tag='%s %s:%s' % (tag,start,new_j))

            elif tag == 'replace':
                # 2010/01/07: This case is new: it was the same as the 'insert' case.
                start = old_private_lines_rdr.index() # Only used for tag.
                while old_private_lines_rdr.index() <= mapping[old_j-1]:
                    old_line = old_private_lines_rdr.get()
                    if marker.isSentinel(old_line):
                        # Important: this should work for @verbatim sentinels
                        # because the next line will also be replaced.
                        new_private_lines_wtr.put(old_line,tag='%s %s:%s' % (
                            'replace: copy sentinel',start,new_j))
                    else:
                        new_line = new_public_lines_rdr.get()
                        new_private_lines_wtr.put(new_line,tag='%s %s:%s' % (
                            'replace: new line',start,new_j))

            elif tag=='delete':
                # Copy sentinels up to the limit = mapping[old_i]
                self.copy_sentinels(old_private_lines_rdr,new_private_lines_wtr,marker,limit=limit)
                # Leave new_public_lines_rdr unchanged.

            else: g.trace('can not happen: unknown difflib.SequenceMather tag: %s' % repr(tag))

            if trace and verbose:
                print_tags(tag, old_i, old_j, new_i, new_j, "After tag")
            #@-node:ekr.20080708192807.5:<< Handle the opcode >>
            #@nl

            # Remember the ends of the previous tag ranges.
            prev_old_j = old_j
            prev_new_j = new_j

        # Copy all unwritten sentinels.
        self.copy_sentinels(
            old_private_lines_rdr,
            new_private_lines_wtr,
            marker,
            limit = old_private_lines_rdr.size())

        # Get the result.
        result = new_private_lines_wtr.getlines()
        if 1:
            #@        << do final correctness check>>
            #@+node:ekr.20080708094444.45:<< do final correctness check >>
            t_sourcelines, t_sentinel_lines = self.separate_sentinels(
                new_private_lines_wtr.lines, marker)

            self.check_the_final_output(
                new_private_lines   = result,
                new_public_lines    = new_public_lines,
                sentinel_lines      = t_sentinel_lines,
                marker              = marker)
            #@-node:ekr.20080708094444.45:<< do final correctness check >>
            #@nl
        return result
    #@-node:ekr.20080708094444.38:x.propagate_changed_lines (the main loop)
    #@+node:ekr.20080708094444.36:x.propagate_changes
    def propagate_changes(self, old_public_file, old_private_file):

        '''Propagate the changes from the public file (without_sentinels)
        to the private file (with_sentinels)'''

        trace = False and not g.unitTesting
        x = self ; at = self.c.atFileCommands
        at.errors = 0

        old_public_lines  = open(old_public_file).readlines()
        old_private_lines = open(old_private_file).readlines()
        marker = x.markerFromFileLines(old_private_lines,old_private_file)

        if trace:
            g.trace(
                'marker',marker,
                '\npublic_file',old_public_file,
                '\npublic lines...\n%s' %(
                    g.listToString(old_public_lines,toRepr=True)),
                '\nprivate_file',old_private_file,
                '\nprivate lines...\n%s\n' %(
                    g.listToString(old_private_lines,toRepr=True)))

        new_private_lines = x.propagate_changed_lines(
            old_public_lines,old_private_lines,marker)

        # Important bug fix: Never create the private file here!
        fn = old_private_file
        copy = os.path.exists(fn) and new_private_lines != old_private_lines

        # 2010/01/07: check at.errors also.
        if copy and x.errors == 0 and at.errors == 0:
            s = ''.join(new_private_lines)
            ok = x.replaceFileWithString(fn,s)
            # g.trace('ok',ok,'writing private file',fn)

        return copy
    #@-node:ekr.20080708094444.36:x.propagate_changes
    #@+node:ekr.20080708094444.34:x.strip_sentinels_with_map
    def strip_sentinels_with_map (self, lines, marker):

        '''Strip sentinels from lines, a list of lines with sentinels.

        Return (results,mapping)

        'lines':     A list of lines containing sentinels.
        'results':   The list of non-sentinel lines.
        'mapping':   A list mapping each line in results to the original list.
                    results[i] comes from line mapping[i] of the original lines.'''

        x = self
        mapping = [] ; results = [] ; i = 0 ; n = len(lines)
        while i < n:
            line = lines[i]
            if marker.isSentinel(line):
                if marker.isVerbatimSentinel(line):
                    i += 1
                    if i < n:
                        # Not a sentinel, whatever it looks like.
                        line = lines[i]
                        # g.trace('not a sentinel',repr(line))
                        results.append(line)
                        mapping.append(i)
                    else:
                        x.verbatim_error()
            else:
                results.append(line)
                mapping.append(i)
            i += 1

        mapping.append(len(lines)) # To terminate loops.
        return results, mapping 
    #@-node:ekr.20080708094444.34:x.strip_sentinels_with_map
    #@+node:bwmulder.20041231170726:x.updatePublicAndPrivateFiles
    def updatePublicAndPrivateFiles (self,fn,shadow_fn):

        '''handle crucial @shadow read logic.

        This will be called only if the public and private files both exist.'''

        x = self ; trace = False

        if trace and not g.app.unitTesting:
            g.trace('significant',x.isSignificantPublicFile(fn),fn)

        if x.isSignificantPublicFile(fn):
            # Update the private shadow file from the public file.
            written = x.propagate_changes(fn,shadow_fn)
            if written: x.message("updated private %s from public %s" % (shadow_fn, fn))
        # else:
            # Don't write *anything*.
            # if 0: # This causes considerable problems.
                # # Create the public file from the private shadow file.
                # x.copy_file_removing_sentinels(shadow_fn,fn)
                # x.message("created public %s from private %s " % (fn, shadow_fn))
    #@-node:bwmulder.20041231170726:x.updatePublicAndPrivateFiles
    #@-node:ekr.20080708192807.1:x.Propagation
    #@+node:ekr.20080708094444.89:x.Utils...
    #@+node:ekr.20080708094444.85:x.error & message & verbatim_error
    def error (self,s,silent=False):

        x = self

        if not silent:
            g.es_print(s,color='red')

        # For unit testing.
        x.last_error = s
        x.errors += 1

    def message (self,s):

        g.es_print(s,color='orange')

    def verbatim_error(self):

        x = self

        x.error('file syntax error: nothing follows verbatim sentinel')
        g.trace(g.callers())
    #@-node:ekr.20080708094444.85:x.error & message & verbatim_error
    #@+node:ekr.20090529125512.6122:x.markerFromFileLines & helper
    def markerFromFileLines (self,lines,fn):  # fn used only for traces.

        '''Return the sentinel delimiter comment to be used for filename.'''

        trace = False and not g.unitTesting
        x = self ; at = x.c.atFileCommands

        s = x.findLeoLine(lines)
        ok,junk,start,end,junk = at.parseLeoSentinel(s)
        if end:
            delims = '',start,end
        else:
            delims = start,'',''

        if trace: g.trace('delim1 %s delim2 %s delim3 %s fn %s' % (
            delims[0],delims[1],delims[2], fn))

        marker = x.markerClass(delims)
        return marker
    #@+node:ekr.20090529125512.6125:x.findLeoLine
    def findLeoLine (self,lines):

        '''Return the @+leo line, or ''.'''

        for line in lines:
            i = line.find('@+leo')
            if i != -1:
                return line
        else:
            return ''
    #@-node:ekr.20090529125512.6125:x.findLeoLine
    #@-node:ekr.20090529125512.6122:x.markerFromFileLines & helper
    #@+node:ekr.20080708094444.9:x.markerFromFileName
    def markerFromFileName (self,filename):

        '''Return the sentinel delimiter comment to be used for filename.'''

        x = self
        if not filename: return None
        root,ext = g.os_path_splitext(filename)
        if ext=='.tmp':
            root, ext = os.path.splitext(root)

        delims = g.comment_delims_from_extension(filename)
        marker = self.markerClass(delims)
        return marker
    #@-node:ekr.20080708094444.9:x.markerFromFileName
    #@+node:ekr.20080708094444.30:x.push_filter_mapping
    def push_filter_mapping (self,lines, marker):
        """
        Given the lines of a file, filter out all
        Leo sentinels, and return a mapping:

          stripped file -> original file

        Filtering should be the same as
        separate_sentinels
        """

        x = self ; mapping = [None]

        i = 0 ; n = len(lines)
        while i < n:
            line = lines[i]
            if marker.isSentinel(line):
                if marker.isVerbatimSentinel(line):
                    i += 1
                    if i < n:
                        mapping.append(i+1)
                    else:
                        x.verbatim_error()
            else:
                mapping.append(i+1)
            i += 1

        return mapping 
    #@-node:ekr.20080708094444.30:x.push_filter_mapping
    #@+node:ekr.20080708094444.29:x.separate_sentinels
    def separate_sentinels (self, lines, marker):

        '''
        Separates regular lines from sentinel lines.

        Returns (regular_lines, sentinel_lines)
        '''

        x = self ; regular_lines = [] ; sentinel_lines = []

        i = 0 ; n = len(lines)
        while i < len(lines):
            line = lines[i]
            if marker.isSentinel(line):
                sentinel_lines.append(line)
                if marker.isVerbatimSentinel(line):
                    i += 1
                    if i < len(lines):
                        line = lines[i]
                        regular_lines.append(line)
                    else:
                        x.verbatim_error()
            else:
                regular_lines.append(line)
            i += 1

        return regular_lines, sentinel_lines 
    #@-node:ekr.20080708094444.29:x.separate_sentinels
    #@+node:ekr.20080708094444.33:x.show_error
    def show_error (self, lines1, lines2, message, lines1_message, lines2_message):

        x = self
        banner1 = '=' * 30
        banner2 = '-' * 30
        g.es_print('%s\n%s\n%s\n%s\n%s' % (
            banner1,message,banner1,lines1_message,banner2))

        x.show_error_lines(lines1,'shadow_errors.tmp1')

        g.es_print('\n%s\n%s\n%s' % (
            banner1,lines2_message,banner1))

        x.show_error_lines(lines2,'shadow_errors.tmp2')

        g.es_print('\n@shadow did not pick up the external changes correctly')

        # g.es_print('Please check shadow.tmp1 and shadow.tmp2 for differences')
    #@+node:ekr.20080822065427.4:show_error_lines
    def show_error_lines (self,lines,fileName):

        for line in lines:
            g.es_print(line)

        if False: # Only for major debugging.
            try:
                f1 = open(fileName, "w")
                for line in lines:
                    f1.write(g.toEncodedString(line))
                f1.close()
            except IOError:
                g.es_exception()
                g.es_print('can not open',fileName)
    #@-node:ekr.20080822065427.4:show_error_lines
    #@-node:ekr.20080708094444.33:x.show_error
    #@-node:ekr.20080708094444.89:x.Utils...
    #@+node:ekr.20080709062932.2:atShadowTestCase
    class atShadowTestCase (unittest.TestCase):

        '''Support @shadow-test nodes.

        These nodes should have two descendant nodes: 'before' and 'after'.

        '''

        #@    @+others
        #@+node:ekr.20080709062932.6:__init__
        def __init__ (self,c,p,shadowController,lax,trace=False):

             # Init the base class.
            unittest.TestCase.__init__(self)

            self.c = c
            self.lax = lax
            self.p = p.copy()
            self.shadowController=shadowController

            # Hard value for now.
            delims = '#','',''
            self.marker = shadowController.markerClass(delims)

            # For teardown...
            self.ok = True

            # Debugging
            self.trace = trace
        #@-node:ekr.20080709062932.6:__init__
        #@+node:ekr.20080709062932.7: fail
        def fail (self,msg=None):

            """Mark a unit test as having failed."""

            import leo.core.leoGlobals as g

            g.app.unitTestDict["fail"] = g.callers()
        #@-node:ekr.20080709062932.7: fail
        #@+node:ekr.20080709062932.8:setUp & helpers
        def setUp (self):

            c = self.c ; p = self.p ; x = self.shadowController

            old = self.findNode (c,p,'old')
            new = self.findNode (c,p,'new')

            self.old_private_lines = self.makePrivateLines(old)
            self.new_private_lines = self.makePrivateLines(new)

            self.old_public_lines = self.makePublicLines(self.old_private_lines)
            self.new_public_lines = self.makePublicLines(self.new_private_lines)

            # We must change node:new to node:old
            self.expected_private_lines = self.mungePrivateLines(self.new_private_lines,'node:new','node:old')

        #@+node:ekr.20080709062932.19:findNode
        def findNode(self,c,p,headline):
            p = g.findNodeInTree(c,p,headline)
            if not p:
                g.es_print('can not find',headline)
                assert False
            return p
        #@nonl
        #@-node:ekr.20080709062932.19:findNode
        #@+node:ekr.20080709062932.20:createSentinelNode
        def createSentinelNode (self,root,p):

            '''Write p's tree to a string, as if to a file.'''

            h = p.h
            p2 = root.insertAsLastChild()
            p2.setHeadString(h + '-sentinels')
            return p2

        #@-node:ekr.20080709062932.20:createSentinelNode
        #@+node:ekr.20080709062932.21:makePrivateLines
        def makePrivateLines (self,p):

            c = self.c ; at = c.atFileCommands

            at.write (p,
                nosentinels = False,
                thinFile = False,  # Debatable.
                scriptWrite = True,
                toString = True)

            s = at.stringOutput
            return g.splitLines(s)
        #@-node:ekr.20080709062932.21:makePrivateLines
        #@+node:ekr.20080709062932.22:makePublicLines
        def makePublicLines (self,lines):

            x = self.shadowController

            lines,mapping = x.strip_sentinels_with_map(lines,self.marker)

            return lines
        #@-node:ekr.20080709062932.22:makePublicLines
        #@+node:ekr.20080709062932.23:mungePrivateLines
        def mungePrivateLines (self,lines,find,replace):

            x = self.shadowController ; marker = self.marker

            i = 0 ; n = len(lines) ; results = []
            while i < n:
                line = lines[i]
                if marker.isSentinel(line):
                    new_line = line.replace(find,replace)
                    results.append(new_line)
                    if marker.isVerbatimSentinel(line):
                        i += 1
                        if i < len(lines):
                            line = lines[i]
                            results.append(line)
                        else:
                            x.verbatim_error()
                else:
                    results.append(line)
                i += 1

            return results
        #@-node:ekr.20080709062932.23:mungePrivateLines
        #@-node:ekr.20080709062932.8:setUp & helpers
        #@+node:ekr.20080709062932.9:tearDown
        def tearDown (self):

            pass

            # No change is made to the outline.
            # self.c.redraw()
        #@-node:ekr.20080709062932.9:tearDown
        #@+node:ekr.20080709062932.10:runTest (atShadowTestCase)
        def runTest (self,define_g = True):

            x = self.shadowController

            results = x.propagate_changed_lines(
                self.new_public_lines,self.old_private_lines,self.marker,p = self.p.copy())

            if not self.lax and results != self.expected_private_lines:

                g.pr('%s atShadowTestCase.runTest:failure' % ('*' * 40))
                for aList,tag in (
                    (results,'results'),
                    (self.expected_private_lines,'expected_private_lines')
                ):
                    g.pr('%s...' % tag)
                    for i, line in enumerate(aList):
                        g.pr('%3s %s' % (i,repr(line)))
                    g.pr('-' * 40)

                assert results == self.expected_private_lines

            assert self.ok
            return self.ok
        #@nonl
        #@-node:ekr.20080709062932.10:runTest (atShadowTestCase)
        #@+node:ekr.20080709062932.11:shortDescription
        def shortDescription (self):

            return self.p and self.p.h or '@test-shadow: no self.p'
        #@-node:ekr.20080709062932.11:shortDescription
        #@-others

    #@-node:ekr.20080709062932.2:atShadowTestCase
    #@+node:ekr.20090529061522.5727:class marker
    class markerClass:

        '''A class representing comment delims in @shadow files.'''

        #@    @+others
        #@+node:ekr.20090529061522.6257:markerClass.ctor & repr
        def __init__(self,delims):

            delim1,delim2,delim3 = delims
            self.delim1 = delim1 # Single-line comment delim.
            self.delim2 = delim2 # Block comment starting delim.
            self.delim3 = delim3 # Block comment ending delim.
            if not delim1 and not delim2:
                self.delim1 = g.app.language_delims_dict.get('unknown_language')

        def __repr__ (self):

            if self.delim1:
                delims = self.delim1
            else:
                delims = '%s %s' % (self.delim2,self.delim2)

            return '<markerClass: delims: %s>' % repr(delims)
        #@-node:ekr.20090529061522.6257:markerClass.ctor & repr
        #@+node:ekr.20090529061522.6258:getDelims
        def getDelims(self):

            if self.delim1:
                return self.delim1,''
            else:
                return self.delim2,self.delim3
        #@-node:ekr.20090529061522.6258:getDelims
        #@+node:ekr.20090529061522.6259:isSentinel
        def isSentinel(self,s,suffix=''):
            '''Return True is line s contains a valid sentinel comment.'''

            s = s.strip()
            if self.delim1 and s.startswith(self.delim1):
                return s.startswith(self.delim1+'@'+suffix)
            elif self.delim2:
                return s.startswith(self.delim2+'@'+suffix) and s.endswith(self.delim3)
            else:
                return False
        #@-node:ekr.20090529061522.6259:isSentinel
        #@+node:ekr.20090529061522.6260:isVerbatimSentinel
        def isVerbatimSentinel(self,s):

            return self.isSentinel(s,suffix='verbatim')
        #@nonl
        #@-node:ekr.20090529061522.6260:isVerbatimSentinel
        #@-others

    #@-node:ekr.20090529061522.5727:class marker
    #@+node:ekr.20080708094444.12:class sourcereader
    class sourcereader:
        """
        A class to read lines sequentially.

        The class keeps an internal index, so that each
        call to get returns the next line.

        Index returns the internal index, and sync
        advances the index to the the desired line.

        The index is the *next* line to be returned.

        The line numbering starts from 0.
        """
        #@    @+others
        #@+node:ekr.20080708094444.13:__init__
        def __init__ (self,shadowController,lines):

            self.lines = lines 
            self.length = len(self.lines)
            self.i = 0
            self.shadowController=shadowController
        #@nonl
        #@-node:ekr.20080708094444.13:__init__
        #@+node:ekr.20080708094444.14:index
        def index (self):
            return self.i
        #@-node:ekr.20080708094444.14:index
        #@+node:ekr.20080708094444.15:get
        def get (self):

            trace = False and not g.unitTesting

            result = self.lines[self.i]
            self.i+=1

            if trace: g.trace(repr(result))
            return result 
        #@-node:ekr.20080708094444.15:get
        #@+node:ekr.20080708094444.16:sync
        def sync (self,i):
            self.i = i 
        #@-node:ekr.20080708094444.16:sync
        #@+node:ekr.20080708094444.17:size
        def size (self):
            return self.length 
        #@-node:ekr.20080708094444.17:size
        #@+node:ekr.20080708094444.18:atEnd
        def atEnd (self):
            return self.index>=self.length 
        #@-node:ekr.20080708094444.18:atEnd
        #@+node:ekr.20080708094444.19:clone
        def clone(self):
            sr = self.shadowController.sourcereader(shadowController,self.lines)
            sr.i = self.i
            return sr
        #@nonl
        #@-node:ekr.20080708094444.19:clone
        #@+node:ekr.20080708094444.20:dump
        def dump(self, title):

            g.pr(title)
            # g.pr('self.i',self.i)
            for i, line in enumerate(self.lines):
                marker = g.choose(i==self.i,'**','  ')
                g.pr("%s %3s:%s" % (marker, i, repr(line)),)
        #@nonl
        #@-node:ekr.20080708094444.20:dump
        #@-others
    #@-node:ekr.20080708094444.12:class sourcereader
    #@+node:ekr.20080708094444.21:class sourcewriter
    class sourcewriter:
        """
        Convenience class to capture output to a file.

        Similar to class sourcereader.
        """
        #@	@+others
        #@+node:ekr.20080708094444.22:__init__
        def __init__ (self,shadowController):

            self.i = 0
            self.lines =[]
            self.shadowController=shadowController
            self.trace = False or self.shadowController.trace_writers
        #@-node:ekr.20080708094444.22:__init__
        #@+node:ekr.20080708094444.23:put
        def put(self, line, tag=''):

            trace = (False or self.trace) and not g.unitTesting

            # An important hack.  Make sure *all* lines end with a newline.
            # This will cause a mismatch later in check_the_final_output,
            # and a special case has been inserted to forgive this newline.
            if not line.endswith('\n'):
                if trace: g.trace('adding newline',repr(line))
                line = line + '\n'

            self.lines.append(line)
            self.i+=1

            if trace: g.trace('%30s %s' % (tag,repr(line)))
        #@-node:ekr.20080708094444.23:put
        #@+node:ekr.20080708094444.24:index
        def index (self):

            return self.i 
        #@-node:ekr.20080708094444.24:index
        #@+node:ekr.20080708094444.25:getlines
        def getlines (self):

            return self.lines 
        #@-node:ekr.20080708094444.25:getlines
        #@+node:ekr.20080708094444.26:dump
        def dump(self, title):

            '''Dump lines for debugging.'''

            g.pr(title)
            for i, line in enumerate(self.lines):
                marker = '  '
                g.es("%s %3s:%s" % (marker, i, line),newline=False)
        #@-node:ekr.20080708094444.26:dump
        #@-others
    #@-node:ekr.20080708094444.21:class sourcewriter
    #@-others
#@-node:ekr.20080708094444.80:class shadowController
#@-others
#@-node:ekr.20080708094444.1:@thin leoShadow.py
#@-leo
