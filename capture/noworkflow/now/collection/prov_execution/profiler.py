# Copyright (c) 2016 Universidade Federal Fluminense (UFF)
# Copyright (c) 2016 Polytechnic Institute of New York University.
# This file is part of noWorkflow.
# Please, consult the license terms in the LICENSE file.
"""Profiler Provider"""
from __future__ import (absolute_import, print_function,
                        division, unicode_literals)

import array
import sys
import os
import traceback
import time
import io
import codecs

import mysql.connector
import hashlib

from datetime import datetime

from ...persistence.models.db_access import DbAccess
from ...persistence import content
from ...persistence.models import Activation, ObjectValue, FileAccess, Trial
from ...utils.cross_version import builtins

from .base import ExecutionProvider
from .argument_captors import ProfilerArgumentCaptor



MODES = {
    # All
    "O_RDONLY": "r",
    "O_WRONLY": "w",
    "O_RDWR": "+",
    "O_APPEND": "a",
    "O_CREAT": None,
    "O_TRUNC": None,
    # Linux
    "O_DSYNC": None,
    "O_RSYNC": None,
    "O_SYNC": None,
    "O_NDELAY": None,
    "O_NONBLOCK": None,
    "O_NOCTTY": None,
    "O_CLOEXEC": None,
    # Windowns
    "O_BINARY": None,
    "O_NOINHERIT": None,
    "O_SHORT_LIVED": None,
    "O_TEMPORARY": None,
    "O_RANDOM": None,
    "O_SEQUENTIAL": None,
    "O_TEXT": None,
    # Extensions that must be defined by the C library
    "O_ASYNC": None,
    "O_DIRECT": None,
    "O_DIRECTORY": None,
    "O_NOFOLLOW": None,
    "O_NOATIME": None,
    "O_PATH": None,
    "O_TMPFILE": None,
    "O_SHLOCK": None,
    "O_EXLOCK": None,
}


class Profiler(ExecutionProvider):                                               # pylint: disable=too-many-instance-attributes
    """Profiler

    Collect:
        activations, arguments, returns, global variables, and file accesses
    """

    def __init__(self, *args):
        super(Profiler, self).__init__(*args)
        # Open
        content.std_open = open
        content.io_open = io.open
        content.codecs_open = codecs.open
        content.os_open = os.open
        builtins.open = self.new_open(open)
        io.open = self.new_open(io.open)
        codecs.open = self.new_open(codecs.open)
        os.open = self.new_open(os.open, osopen=True)

        # db connect
        mysql.connector.connect = self.new_connect(mysql.connector.connect)

        # the number of user functions activated
        #   (starts with -1 to compensate the first call to the script itself)
        self.depth_user = -1
        # the number of non-user functions activated
        self.depth_non_user = 0
        # The first caller is None
        self.activation_stack = [None]

        # Store provenance
        self.activations = self.metascript.activations_store
        self.object_values = self.metascript.object_values_store
        self.file_accesses = self.metascript.file_accesses_store

        # db provenance
        self.db_accesses = self.metascript.db_accesses_store

        # Avoid using the same event for tracer and profiler
        self.last_event = None

        self.definition = self.metascript.definition
        self.function_globals = self.definition.function_globals

        self.event_map["c_call"] = self.trace_c_call
        self.event_map["call"] = self.trace_call
        self.event_map["c_return"] = self.trace_c_return
        self.event_map["c_exception"] = self.trace_c_exception
        self.event_map["return"] = self.trace_return

        # Partial save
        self.save_frequency = self.metascript.save_frequency / 1000.0
        self.call_storage_frequency = self.metascript.call_storage_frequency
        self.closed_activations = 0

        self.timer = time.time
        self.last_time = self.timer()

        # Events are unique
        self.unique_events = True

        # Global activations
        self.globals = {}
        # Main activation
        self.main_activation = None

        # Skip tear_up return
        self.skip_first_return = True
        self.enabled = True

        # Capture arguments
        self.argument_captor = ProfilerArgumentCaptor(self)

        if sys.version_info >= (3, 0):
            Profiler.add_activation = Profiler.initial_add_activation

    @property
    def current_activation(self):
        """Return current activation"""
        astack = self.activation_stack
        if astack[-1] is not None:
            return self.activations[astack[-1]]
        return self.activations.dry_add("", "", "empty", 0, 0, -1, False)

    @property
    def parent_activation(self):
        """Return activation that called current activation"""
        return self.activations[self.activation_stack[-2]]

    def new_open(self, old_open, osopen=False):  # arquivo aqui
        """Wrap the open builtin function to register file access"""
        print(self)
        print(old_open)

        def open(name, *args, **kwargs):                                         # pylint: disable=redefined-builtin
            """Open file and add it to file_accesses"""
            print("teste open")
            print(name)
            print(self.enabled)
            if self.enabled:
                # Create a file access object with default values
                fid = self.file_accesses.add(name)
                print('fid')
                print(fid)
                file_access = self.file_accesses[fid]

                if os.path.exists(name):
                    # Read previous content if file exists
                    with content.std_open(name, "rb") as fil:
                        file_access.content_hash_before = content.put(
                            fil.read()
                        )

                # Update with the informed keyword arguments (mode / buffering)
                file_access.update(kwargs)
                # Update with the informed positional arguments
                if len(args) > 1:
                    file_access.buffering = args[1]
                elif len(args) > 0:
                    mode = args[0]
                    if osopen:
                        mode = ""
                        for key, value in MODES.items():
                            flag = getattr(os, key, 0)
                            if args[0] & flag:
                                value = value or "({})".format(key)
                                mode += value

                    file_access.mode = mode

                self.add_file_access(file_access)
            return old_open(name, *args, **kwargs)

        return open

    def add_file_access(self, file_access):  # arquivo aqui
        """After activation that called open finish, add file_accesses to it"""
        print("teste add_file_access")
        activation = self.current_activation
        file_access.function_activation_id = activation.id
        activation.file_accesses.append(file_access)

    def new_connect(self, old_connect):  #
        """Wrap the connect function to register db access"""
        print('teste new_connect')
        print(self)
        print('teste new_connect')
        print(old_connect)
        print('teste new_connect')

        def connect(*args, **kwargs):                                         # pylint: disable=redefined-builtin
            """Open file and add it to file_accesses"""
            print("teste connect")
            print(args)
            print(kwargs)
            print(self.enabled)
            if self.enabled:
                # Create a file access object with default values
                dbid = self.db_accesses.add(kwargs['database'])
                print(dbid)
                db_access = self.db_accesses[dbid]

                '''
                if os.path.exists(name):
                    # Read previous content if file exists
                    with content.std_open(name, "rb") as fil:
                        file_access.content_hash_before = content.put(
                            fil.read()
                        )
                '''

                db_access.host = kwargs['host']
                db_access.user = kwargs['user']

                mydb = content.std_connect(
                    host=kwargs['host'],
                    user=kwargs['user'],
                    passwd=kwargs['passwd'],
                    database=kwargs['database']
                )
                #encontra as poscioes dos comandos dml
                indices_dml = []
                i = 0
                while True:
                    print(i)
                    indice_ini = self.metascript.code.upper().find('SELECT', i)
                    indice_fim = self.metascript.code.upper().find(')', indice_ini + 6)
                    if indice_ini < 0:
                        break
                    else:
                        indices_dml.append((indice_ini, indice_fim - 1))
                    i = indice_ini + 1

                print(indices_dml)

                # usa os indices para encontrar os comandos
                dmls = []
                for indice in indices_dml:
                    dmls.append(self.metascript.code[indice[0]:indice[1]])
                print(dmls)

                mycursor = mydb.cursor()
                db_access.dml = []
                #calcula as hashs de cada tabela
                for comando in dmls:
                    indice_from = comando.upper().split().index("FROM")
                    tabela = comando.split()[indice_from + 1]
                    select = "SELECT * FROM " + tabela
                    print(select)
                    mycursor.execute(select)
                    myresult = mycursor.fetchall()

                    stringao = ""
                    for row in myresult:
                        for col in row:
                            stringao = stringao + col.__str__()
                    print(stringao)
                    print(hashlib.sha1(bytes(stringao, 'utf-8')).hexdigest())

                    db_access.dml.append((tabela, comando, hashlib.sha1(bytes(stringao, 'utf-8')).hexdigest()))
                # Update with the informed keyword arguments (mode / buffering)
                db_access.dml = db_access.dml.__str__()
                db_access.update(kwargs)
                # Update with the informed positional arguments
                '''
                if len(args) > 1:
                    file_access.buffering = args[1]
                elif len(args) > 0:
                    mode = args[0]
                    if osopen:
                        mode = ""
                        for key, value in MODES.items():
                            flag = getattr(os, key, 0)
                            if args[0] & flag:
                                value = value or "({})".format(key)
                                mode += value

                    file_access.mode = mode
                '''
                self.add_db_access(db_access)
            return old_connect(*args, **kwargs)

        return connect

    def add_db_access(self, db_access):  # arquivo aqui
        """After activation that called open finish, add file_accesses to it"""
        print("teste add_db_access")
        activation = self.current_activation
        db_access.function_activation_id = activation.id
        activation.db_accesses.append(db_access)


    def valid_depth(self, extra=0):
        """Check if it is capturing in a valid depth
        Consider both user depth and non user depth.
        """
        depth = self.depth_user + self.depth_non_user + extra
        if depth < 0:
            self.enabled = False
            return False
        if depth > self.depth_threshold:
            return False
        return self.depth_non_user <= self.non_user_depth_threshold

    def add_activation(self, aid):                                               # pylint: disable=function-redefined
        """Add activation to activation stack"""
        self.activation_stack.append(aid)

    _old_add_activation = add_activation

    def initial_add_activation(self, aid):
        """Add activation to activation stack.
        Ignore first module.exec on Python 3"""
        Profiler.add_activation = Profiler._old_add_activation
        if aid == 1 and self.activations[aid].name == "module.exec":
            self.depth_non_user -= 1
            self.activations.id = 0
            return
        return Profiler._old_add_activation(self, aid)

    def close_activation(self, frame, event, arg):                               # pylint: disable=unused-argument
        """Remove activation from stack, set finish time and add accesses"""
        activation = self.current_activation
        self.activation_stack.pop()
        activation.finish = datetime.now()
        try:
            if event == "return":
                activation.return_value = self.serialize(arg)
        except Exception:  # ignoring any exception during capture               # pylint: disable=broad-except
            activation.return_value = None
        # Update content of accessed files
        for file_access in activation.file_accesses:
            # Checks if file still exists
            if os.path.exists(file_access.name):
                with content.std_open(file_access.name, "rb") as fil:
                    file_access.content_hash_after = content.put(fil.read())
            file_access.done = True
        self.closed_activations += 1
        if (self.call_storage_frequency and
                (self.closed_activations % self.call_storage_frequency == 0)):
            self.store(partial=True)

    def trace_c_call(self, frame, event, arg):                                   # pylint: disable=unused-argument
        """Trace c_call. Increase non_user depth"""
        self.depth_non_user += 1
        if self.valid_depth():
            self.add_activation(self.activations.add(
                "now(n/a)",
                frame.f_code.co_filename,
                arg.__name__ if arg.__self__ is None else ".".join(
                    [type(arg.__self__).__name__, arg.__name__]),
                frame.f_lineno, frame.f_lasti, self.activation_stack[-1],
                False
            ))

    def trace_call(self, frame, event, arg):                                     # pylint: disable=unused-argument
        """Trace call. Increase depth and create activation"""
        co_name = frame.f_code.co_name
        co_filename = frame.f_code.co_filename
        if co_filename in self.paths:
            self.depth_user += 1
            in_paths = True
        else:
            self.depth_non_user += 1
            in_paths = False

        if self.valid_depth():
            aid = self.activations.add(
                co_filename,
                frame.f_back.f_code.co_filename,
                co_name if co_name != "<module>" else co_filename,
                frame.f_back.f_lineno, frame.f_back.f_lasti,
                self.activation_stack[-1],
                in_paths and self.valid_depth(extra=1)
            )
            activation = self.activations[aid]

            if activation.is_main:
                self.main_activation = activation
            if co_name == "<module>":
                self.globals[co_filename] = activation
            # Capturing arguments
            self.argument_captor.capture(frame, activation)

            # Capturing globals
            def_globals = self.function_globals[co_filename][activation.name]
            fglobals = frame.f_globals
            for global_var in def_globals:
                self.object_values.add(
                    global_var, self.serialize(fglobals[global_var]),
                    "GLOBAL", aid)

            activation.start = datetime.now()
            self.add_activation(aid)

    def trace_c_return(self, frame, event, arg):                                 # pylint: disable=unused-argument
        """Trace c_return. Decrease non_user depth"""
        if self.valid_depth():
            self.close_activation(frame, event, arg)
        self.depth_non_user -= 1

    def trace_c_exception(self, frame, event, arg):
        """Trace c_exception. Decrease non_user depth"""
        if self.valid_depth():
            self.close_activation(frame, event, arg)
        self.depth_non_user -= 1

    def trace_return(self, frame, event, arg):
        """Trace return. Decrease depth and close activation"""
        # Only enable activations gathering after the first call to the script
        if self.skip_first_return:
            self.skip_first_return = False
            return
        if self.valid_depth():
            self.close_activation(frame, event, arg)

        if frame.f_code.co_filename in self.paths:
            if frame.f_code.co_name == "<module>":
                self.enabled = False
            self.depth_user -= 1
        else:
            self.depth_non_user -= 1

    def new_event(self, frame, event, arg):                                      # pylint: disable=unused-argument
        """Check if event is new to avoid Profiler and Tracer overlap"""
        current_event = (event, frame.f_lineno, id(frame))
        if self.last_event != current_event:
            self.last_event = current_event
            return True
        return False

    def tracer(self, frame, event, arg):
        """Check if event is valid before executing tracer
        Call event function from event_map
        """
        try:
            if self.enabled:
                if self.unique_events or self.new_event(frame, event, arg):
                    self.pre_tracer(frame, event, arg)
                    self.event_map[event](frame, event, arg)
                if (self.save_frequency and
                        (self.timer() - self.last_time > self.save_frequency)):
                    self.store(partial=True)
                    self.last_time = self.timer()
        except Exception:                                                        # pylint: disable=broad-except
            traceback.print_exc()
        finally:
            return self.tracer                                                   # pylint: disable=lost-exception

    def pre_tracer(self, frame, event, arg):                                     # pylint: disable=unused-argument, no-self-use
        """It is executed before the tracing event"""
        pass

    def store(self, partial=False):
        """Store execution provenance"""
        tid = self.trial_id
        if not partial:
            now = datetime.now()
            Trial.fast_update(tid, now, self.metascript.docstring)

        Activation.fast_store(tid, self.activations, partial)
        ObjectValue.fast_store(tid, self.object_values, partial)
        FileAccess.fast_store(tid, self.file_accesses, partial)
        DbAccess.fast_store(tid, self.db_accesses, partial)

    def tearup(self):
        """Activate profiler"""
        sys.setprofile(self.tracer)

    def teardown(self):
        """Deactivate profiler"""
        builtins.open = content.std_open
        super(Profiler, self).teardown()
        sys.setprofile(self.default_profile)
