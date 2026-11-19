from . import exporter
from . import operators
from . import ui

modules = (operators, exporter, ui)


def register():
    for module in modules:
        module.register()


def unregister():
    for module in reversed(modules):
        module.unregister()
