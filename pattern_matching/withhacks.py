from __future__ import annotations

from dataclasses import dataclass, field
from types import FrameType
from typing import Any, Callable, Optional, DefaultDict, Dict, ClassVar

"""

A subset of [withhacks](https://github.com/rfk/withhacks)


  withhacks:  building blocks for with-statement-related hackery

This module is a collection of useful building-blocks for hacking the Python
"with" statement.  It combines ideas from several neat with-statement hacks 
I found around the internet into a suite of re-usable components:

  * http://www.mechanicalcat.net/richard/log/Python/Something_I_m_working_on.3
  * http://billmill.org/multi_line_lambdas.html
  * http://code.google.com/p/ouspg/wiki/AnonymousBlocksInPython

"""
import sys

try:
    import threading
except ImportError:
    import dummy_threading as threading
from collections import defaultdict

_trace_lock = threading.Lock()
_orig_sys_trace = None

def _dummy_sys_trace(*args, **kwds):
    """Dummy trace function used to enable tracing."""


def _enable_tracing():
    """Enable system-wide tracing, if it wasn't already."""
    global _orig_sys_trace
    try:
        _orig_sys_trace = sys.gettrace()
    except AttributeError:
        _orig_sys_trace = None
    if _orig_sys_trace is None:
        sys.settrace(_dummy_sys_trace)


def _disable_tracing():
    """Disable system-wide tracing, if we specifically switched it on."""
    global _orig_sys_trace
    if _orig_sys_trace is None:
        sys.settrace(None)

@dataclass
class _FrameTracer:
    frame: FrameType
    orig_function: Optional[Callable]
    start_line: int
    injected_functions: DefaultDict[str, list] = field(default_factory=lambda: defaultdict(list))
    orig_trace_opcodes: bool = None
    
    trace_counter: ClassVar[int] = 0
    
    def __call__(self, frame, event, arg):
        assert frame is self.frame
        if self.orig_function is not None:
            self.orig_function = self.orig_function(frame, event, arg)
        if event == 'line' and frame.f_lineno == self.start_line:
            # We want to to call the child functions at a point where assigning to `f_lineno` is valid.
            # Sadly, sometimes python calls us to early for that when we are leaving a `__enter__` method (see bpo42286)
            # Therefore we first check whether or not we are still on the line in which we were when inject_trace_func was called
            # If we didn't move, we just don't do anything
            return self
        exc_to_reraise = None
        for f in self.injected_functions[event]:
            try:
                f(frame)
            except Exception as e:
                exc_to_reraise = e
        with _trace_lock:
            del self.injected_functions[event]
            if event == 'opcode':
                self.frame.f_trace_opcodes = self.orig_trace_opcodes
            if len(self.injected_functions) > 0:
                if exc_to_reraise is not None:
                    raise exc_to_reraise
                return self
            _FrameTracer.trace_counter -= 1
            assert _FrameTracer.trace_counter >= 0
            del _frame_tracer[frame]
            self.frame = None
            if _FrameTracer.trace_counter == 0:
                _disable_tracing()
            frame.f_trace = self.orig_function
            if exc_to_reraise is not None:
                raise exc_to_reraise
            return self.orig_function
    
    def register_function(self, event: str, f: Callable):
        if event == 'opcode':
            if not self.injected_functions['opcode']:
                self.orig_trace_opcodes = self.frame.f_trace_opcodes
                self.frame.f_trace_opcodes = True
        self.injected_functions[event].append(f)

_frame_tracer: Dict[FrameType, _FrameTracer] = {}


def inject_trace_func(frame, func, event='line'):
    """Inject the given function as a trace function for frame.

    The given function will be executed immediately as the frame's execution
    resumes.  Since it's running inside a trace hook, it can do some nasty
    things like modify frame.f_locals, frame.f_lineno and friends.
    """
    with _trace_lock:
        if frame not in _frame_tracer:
            if len(_frame_tracer) == 0:
                _enable_tracing()
            _frame_tracer[frame] = _FrameTracer(frame, frame.f_trace, frame.f_lineno)
            frame.f_trace = _frame_tracer[frame]
            _FrameTracer.trace_counter += 1
        _frame_tracer[frame].register_function(event, func)


# def _invoke_trace_funcs(frame, event, arg):
#     """Invoke any trace funcs that have been injected.
# 
#     Once all injected functions have been executed, the trace hooks are
#     removed.  Hopefully this will keep the overhead of all this madness
#     to a minimum :-)
#     """
#     if _orig_trace_funcs[frame] is not None: # We try to just wrap the original trace function
#         _orig_trace_funcs[frame] = _orig_trace_funcs[frame](frame, event, arg)
#         
#     if event == 'line' and frame.f_lineno == _injected_trace_funcs[frame][0]:
#         # We want to to call the child functions at a point where assigning to `f_lineno` is valid.
#         # Sadly, sometimes python calls us to early for that when we are leaving a `__enter__` method (see bpo42286)
#         # Therefore we first check whether or not we are still on the line in which we were when inject_trace_func was called
#         # If we didn't move, we just don't do anything
#         return _invoke_trace_funcs
#     try:
#         for func in _injected_trace_funcs[frame][1][event]:
#             func(frame)
#     finally:
#         del _injected_trace_funcs[frame][1][event]
#         if len(_injected_trace_funcs[frame][1]) == 0:
#             del _injected_trace_funcs[frame]
#             with _trace_lock:
#                 if len(_orig_trace_funcs) == 1:
#                     _disable_tracing()
#                 frame.f_trace = _orig_trace_funcs.pop(frame)
#             if frame.f_trace is not None:
#                 return frame.f_trace(frame, event, arg)


def lookup_name(frame, name):
    """Get the value of the named variable, as seen by the given frame.

    The name is first looked for in f_locals, then f_globals, and finally
    f_builtins.  If it's not defined in any of these scopes, NameError 
    is raised.
    """
    try:
        return frame.f_locals[name]
    except KeyError:
        try:
            return frame.f_globals[name]
        except KeyError:
            try:
                return frame.f_builtins[name]
            except KeyError:
                raise NameError(name)


class _ExitContext(Exception):
    """Special exception used to skip execution of a with-statement block."""
    pass


def _exit_context(frame):
    """Simple function to throw an _ExitContext exception."""
    raise _ExitContext


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

    _missing_marker = object()
    
    def __init__(self):
        self.__to_reset__ = {}

    def _set_context_locals(self, locals: dict[str, Any]):
        """Set local variables in the with-statement context.

        The argument "locals" is a dictionary of name bindings to be inserted
        into the execution context of the with-statement.
        
        This tries to be as smart as possible to reduce the chance of surprises (e.g. conflict between lookup in locals/globals)
        """
        
        # The naive approach as used by the old withhacks doesn't work:
        # def main():
        #     with Inject(x=5):
        #         print(x)
        #
        # If we just update the f_locals, x will still not be accessible. The bytecode compiler didn't consider it a local variable,
        # and therefore it is just looked up in the globals.
        # To get around this we need to check whether or not a variable is considered local and then behave diffrently depending on that
        # Since we might inject globals from within a function, we also need to cleanup at the end of the withblock.
        # Note that this might override some globals as seen in child functions. Too bad! We just need to put a warning somewhere.
        
        f = self.__frame__
        if f.f_locals is f.f_globals: # we are in global scope. We don't need to worry and the old approach works
            inject_trace_func(f, lambda frame: frame.f_locals.update(locals), 'opcode')
        else:
            c = f.f_code
            lcl_vars = set(c.co_varnames)
            store_local = set(locals.keys()) & lcl_vars
            store_global = set(locals.keys()) - store_local
            self.__to_reset__ |= {n:f.f_globals.get(n, self._missing_marker) for n in store_global}
            def set_vars(frame):
                for n,v in locals.items():
                    if n in store_local:
                        frame.f_locals[n] = v
                    else:
                        frame.f_globals[n] = v
            inject_trace_func(f, set_vars, 'opcode')
    
    def _set_lineno(self, i: int):
        """Sets the next line to be executed"""

        def callback(frame):
            frame.f_lineno = i

        inject_trace_func(self.__frame__, callback)

    def _get_local(self, name: str):
        return lookup_name(self.__frame__, name)
    
    def _dont_execute(self):
        inject_trace_func(self.__frame__, _exit_context)

    def __enter__(self):
        """Enter the context of this WithHack.

        The base implementation will skip execution of the contained
        code according to the values of "dont_execute" and "must_execute".
        Be sure to call the superclass version if you override it.
        """
        f = sys._getframe(1)
        while f.f_locals.get("self") is self:  # We need to adjust for super calls
            f = f.f_back
        self.__frame__ = f
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Enter the context of this WithHack.

        This is usually where all the interesting hackery takes place.

        The base implementation suppresses the special _ExitContext exception
        but lets any other exceptions pass through.  Your subclass should
        probably do the same - the simplest way is to pass through the return
        value given by this base implementation.
        """
        # register_opcode_debugger(self.__frame__)
        for n, v in self.__to_reset__.copy().items():
            if v is self._missing_marker:
                try:
                    del self.__frame__.f_globals[n]
                except KeyError:
                    pass
            else:
                self.__frame__.f_globals[n] = v
            del self.__to_reset__[n]
        self.__frame__ = None
        if exc_type is _ExitContext:
            return True
        else:
            return False
