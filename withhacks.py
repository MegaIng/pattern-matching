from __future__ import annotations

"""

  withhacks:  building blocks for with-statement-related hackery

This module is a collection of useful building-blocks for hacking the Python
"with" statement.  It combines ideas from several neat with-statement hacks 
I found around the internet into a suite of re-usable components:

  * http://www.mechanicalcat.net/richard/log/Python/Something_I_m_working_on.3
  * http://billmill.org/multi_line_lambdas.html
  * http://code.google.com/p/ouspg/wiki/AnonymousBlocksInPython

By subclassing the appropriate context managers from this module, you can
easily do things such as:

  * skip execution of the code inside the with-statement
  * set local variables in the frame executing the with-statement
  * capture the bytecode from inside the with-statement
  * capture local variables defined inside the with-statement

Building on these basic tools, this module also provides some useful prebuilt
hacks:

  :xargs:      call a function with additional arguments defined in the
               body of the with-statement
  :xkwargs:    call a function with additional keyword arguments defined
               in the body of the with-statement
  :namespace:  direct all variable accesses and assignments to the attributes
               of a given object (like "with" in JavaScript or VB)
  :keyspace:   direct all variable accesses and assignments to the keys of
               of a given object (like namespace() but for dicts)

WithHacks makes extensive use of Noam Raphael's fantastic "byteplay" module;
since the official byteplay distribution doesn't support Python 2.6, a local
version with appropriate patches is included in this module.

"""

__ver_major__ = 0
__ver_minor__ = 1
__ver_patch__ = 1
__ver_sub__ = ""
__version__ = "%d.%d.%d%s" % (__ver_major__, __ver_minor__,
                              __ver_patch__, __ver_sub__)

import sys

try:
    import threading
except ImportError:
    import dummy_threading as threading

from frameutils import *


class _ExitContext(Exception):
    """Special exception used to skip execution of a with-statement block."""
    pass


def _exit_context(frame):
    """Simple function to throw an _ExitContext exception."""
    raise _ExitContext


class _Bucket:
    """Anonymous attribute-bucket class."""
    pass


class WithHack(object):
    """Base class for with-statement-related hackery.

    This class provides some useful utilities for constructing with-statement
    hacks.  Specifically:

        * ability to skip execution of the contained block of code
        * ability to access the frame of execution containing the block
        * ability to update local variables in the execution frame

    If a subclass sets the attribute "dont_execute" to true then execution
    of the with-statement's contained code block will be skipped.  If it sets
    the attribute "must_execute" to true, the block will be executed regardless
    of the setting of "dont_execute".  Having two settings allows hacks that
    want to skip the block to be combined with hacks that need it executed.
    """

    dont_execute = False
    must_execute = False

    def _get_context_frame(self):
        """Get the frame object corresponding to the with-statement context.

        This is designed to work from within superclass method call. It finds
        the first frame in which the variable "self" is not bound to this 
        object.  While this heuristic rules out some strange uses of WithHack
        objects (such as entering on object inside its own __exit__ method)
        it should suffice in practise.
        """
        try:
            return self.__frame
        except AttributeError:
            # Offset 2 accounts for this method, and the one calling it.
            f = sys._getframe(2)
            while f.f_locals.get("self") is self:
                f = f.f_back
            self.__frame = f
            return f

    def _set_context_locals(self, locals):
        """Set local variables in the with-statement context.

        The argument "locals" is a dictionary of name bindings to be inserted
        into the execution context of the with-statement.
        """
        frame = self._get_context_frame()
        inject_trace_func(frame, lambda frame: frame.f_locals.update(locals))

    def __enter__(self):
        """Enter the context of this WithHack.

        The base implementation will skip execution of the contained
        code according to the values of "dont_execute" and "must_execute".
        Be sure to call the superclass version if you override it.
        """
        if self.dont_execute and not self.must_execute:
            frame = self._get_context_frame()
            inject_trace_func(frame, _exit_context)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Enter the context of this WithHack.

        This is usually where all the interesting hackery takes place.

        The base implementation suppresses the special _ExitContext exception
        but lets any other exceptions pass through.  Your subclass should
        probably do the same - the simplest way is to pass through the return
        value given by this base implementation.
        """
        if exc_type is _ExitContext:
            return True
        else:
            return False
