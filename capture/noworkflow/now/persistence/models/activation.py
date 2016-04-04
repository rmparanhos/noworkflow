# Copyright (c) 2016 Universidade Federal Fluminense (UFF)
# Copyright (c) 2016 Polytechnic Institute of New York University.
# This file is part of noWorkflow.
# Please, consult the license terms in the LICENSE file.
"""Activation Model"""
from __future__ import (absolute_import, print_function,
                        division, unicode_literals)

from future.builtins import map as cvmap
from sqlalchemy import Column, Integer, Text, TIMESTAMP
from sqlalchemy import PrimaryKeyConstraint, ForeignKeyConstraint
from sqlalchemy.orm import backref

from ...utils.prolog import PrologDescription, PrologTrial, PrologTimestamp
from ...utils.prolog import PrologAttribute, PrologRepr, PrologNullable

from .base import AlchemyProxy, proxy_class, one, many_viewonly_ref, many_ref
from .base import backref_one, backref_many, query_many_property
from .object_value import ObjectValue
from .variable_dependency import VariableDependency
from .variable import Variable


@proxy_class
class Activation(AlchemyProxy):
    """Represent an activation"""
    __tablename__ = "activation"
    __table_args__ = (
        PrimaryKeyConstraint("trial_id", "id"),
        ForeignKeyConstraint(["trial_id"], ["trial.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["trial_id", "id"],
                             ["evaluation.trial_id",
                              "evaluation.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["trial_id", "code_block_id"],
                             ["code_block.trial_id",
                              "code_block.id"], ondelete="CASCADE"),
    )
    trial_id = Column(Integer, index=True)
    id = Column(Integer, index=True)                                             # pylint: disable=invalid-name
    name = Column(Text)
    start = Column(TIMESTAMP)
    code_block_id = Column(Integer)

    #evaluations = many_viewonly_ref("activation", "Evaluation")
    file_accesses = many_viewonly_ref("activation", "FileAccess")

    _children = backref("evaluation", order_by="Activation.start")
    caller = one(
        "Activation", remote_side=[trial_id, id],
        backref=_children, viewonly=True
    )

    this_evaluation = one("Evaluation")

    trial = backref_one("trial")  # Trial.activations
    code_block = backref_one("code_block")  # CodeBlock.activations
    evaluations = backref_many("evaluation")  # Evaluation.caller

    prolog_description = PrologDescription("activation", (
        PrologTrial("trial_id", link="trial.id"),
        PrologAttribute("id", link="evaluation.id"),
        PrologRepr("name"),
        PrologTimestamp("start"),
        PrologNullable("code_block_id", link="code_block.id"),
    ), description=(
        "informs that in a given trial (*trial_id*),\n"
        "a function *name* was activated\n"
        "by another function (*caller_activation_id*)\n"
        "and executed during a time period from *start*\n"
        "to *finish*."
    ))

    # ToDo: Improve hash

    @property
    def line(self):
        return self.this_evaluation.code_component.first_char_line

    @property
    def finish(self):
        return self.this_evaluation.moment

    def __key(self):
        return (self.trial_id, self.name, self.line)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return self.__key() == other.__key()                                     # pylint: disable=protected-access

    @property
    def duration(self):
        """Calculate activation duration"""
        return int((self.finish - self.start).total_seconds() * 1000000)

    def show(self, _print=lambda x, offset=0: print(x)):
        """Show object

        Keyword arguments:
        _print -- custom print function (default=print)
        """
        """
        global_vars = list(self.globals)
        if global_vars:
            _print("{name}: {values}".format(
                name="Globals", values=", ".join(cvmap(str, global_vars))))

        arg_vars = list(self.arguments)
        if arg_vars:
            _print("{name}: {values}".format(
                name="Arguments", values=", ".join(cvmap(str, arg_vars))))

        if self.return_value:
            _print("Return value: {ret}".format(ret=self.return_value))

        _show_slicing("Variables:", self.variables, _print)
        _show_slicing("Usages:", self.variables_usages, _print)
        _show_slicing("Dependencies:", self.source_variables, _print)
        """
        # ToDo: now2

    def __repr__(self):
        return "Activation({0.trial_id}, {0.id}, {0.name})".format(self)


def _show_slicing(name, query, _print):
    """Show slicing objects"""
    objects = list(query)
    if objects:
        _print(name)
        for obj in objects:
            _print(str(obj), 1)
