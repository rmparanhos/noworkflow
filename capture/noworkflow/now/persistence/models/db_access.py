# Copyright (c) 2016 Universidade Federal Fluminense (UFF)
# Copyright (c) 2016 Polytechnic Institute of New York University.
# This file is part of noWorkflow.
# Please, consult the license terms in the LICENSE file.
"""File Access Model"""
from __future__ import (absolute_import, print_function,
                        division, unicode_literals)

import os
import ast

from sqlalchemy import Column, Integer, Text, TIMESTAMP
from sqlalchemy import PrimaryKeyConstraint, ForeignKeyConstraint

from ...utils.prolog import PrologDescription, PrologTrial, PrologAttribute
from ...utils.prolog import PrologRepr, PrologTimestamp, PrologNullable
from ...utils.prolog import PrologNullableRepr

from .. import relational, persistence_config

from .base import AlchemyProxy, proxy_class, backref_one, proxy


@proxy_class
class DbAccess(AlchemyProxy):  # arquivo aquifile_access.py
    """Represent a db access"""

    hide_timestamp = False

    __tablename__ = "db_access"
    __table_args__ = (
        PrimaryKeyConstraint("trial_id", "id"),
        ForeignKeyConstraint(["trial_id", "function_activation_id"],
                             ["function_activation.trial_id",
                              "function_activation.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["trial_id"], ["trial.id"], ondelete="CASCADE"),
    )
    trial_id = Column(Integer, index=True)
    id = Column(Integer, index=True)                                             # pylint: disable=invalid-name
    name = Column(Text)

    # db
    host = Column(Text)
    user = Column(Text)
    dml = Column(Text)

    timestamp = Column(TIMESTAMP)
    function_activation_id = Column(Integer, index=True)

    trial = backref_one("trial")  # Trial.file_accesses
    activation = backref_one("activation")  # Activation.file_accesses

    prolog_description = PrologDescription("db_access", (
        PrologTrial("trial_id", link="activation.trial_id"),
        PrologAttribute("id", fn=lambda obj: "f{}".format(obj.id)),
        PrologRepr("name"),
        PrologRepr("mode"),
        PrologNullableRepr("content_hash_before"),
        PrologNullableRepr("content_hash_after"),
        PrologTimestamp("timestamp"),
        PrologNullable("activation_id", attr_name="function_activation_id",
                       link="activation.id"),
    ), description=(
        "informs that in a given trial (*trial_id*),\n"
        "a database *name*\n"
        "in a host *host*\n"
        "was accessed by a function activation (*activation_id*)\n"
        "and used this dml *dml*\n"
        "at a specific *timestamp*.\n"
    ))

    @property
    def stack(self):
        """Return the activation stack since the beginning of execution"""
        stack = []
        activation = self.activation
        while activation:
            name = activation.name
            activation = activation.caller
            if activation:
                stack.insert(0, name)
        if not stack or stack[-1] != "open":
            stack.append(" ... -> open")
        return " -> ".join(stack)

    @property
    def brief(self):
        """Brief description of file access"""
        result = "({0.mode}) {0.name}".format(self)
        if self.content_hash_before is None:
            result += " (new)"
        return result

    @property
    def activation_id(self):
        return self.function_activation_id

    @property
    def is_internal(self):
        return (
            not os.path.isabs(self.name) or
            persistence_config.base_path in self.name
        )

    @classmethod  # query
    def find_by_name_and_time(cls, name, timestamp, trial=None,
                              session=None):
        """Return the first access according to name and timestamp

        Arguments:
        name -- specify the desired file
        timestamp -- specify the start of finish time of trial

        Keyword Arguments:
        trial -- limit search in a specific trial_id
        """
        model = cls.m
        session = session or relational.session
        query = (
            session.query(model)
            .filter(
                (model.name == name) &
                (model.timestamp.like(timestamp + "%"))
            ).order_by(model.timestamp)
        )
        if trial:
            query = query.filter(model.trial_id == trial)
        return proxy(query.first())

    def __key(self):
        return (self.name, self.content_hash_before, self.content_hash_after,
                self.mode)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if not isinstance(other, DbAccess):
            return False
        return (
            (self.content_hash_before == other.content_hash_before)
            and (self.content_hash_after == other.content_hash_after)
        )

    def show(self, _print=print):
        """Show object

        Keyword arguments:
        _print -- custom print function (default=print)
        """
        result = """\
            Name: {f.name}
            Host: {f.host}
            User: {f.user}
            """
        dmls = ast.literal_eval(self.dml)
        cont = 0
        for item in dmls:
            cont += 1
            if cont == 1:
                result += "DML {}: \n".format(cont)
            else:
                result += "\tDML {}: \n".format(cont)
            result += "\t\t\tTable: {} \n".format(item[0])
            result += "\t\t\tHash Table: {} \n".format(item[1])
            result += "\t\t\tQuery: {} \n".format(item[2])
            result += "\t\t\tHash Query: {} \n\t".format(item[3])

        if not self.hide_timestamp:
            result += """Timestamp: {f.timestamp}
            """
        result += """Function: {f.stack}\
            """
        _print(result.format(f=self))


    def __repr__(self):
        return "DbAccess({0.trial_id}, {0.id}, {0.name}, {0.mode})".format(
            self)


class UniqueFileAccess(DbAccess):

    def __key(self):
        return self.id

    def __eq__(self, other):
        if not isinstance(other, DbAccess):
            return False
        return (self.id == other.id)

    def __hash__(self):
        return hash(self.__key())
