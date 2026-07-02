"""interface_web — frontend-only Starlette proxy package (issue #844).

This ``__init__.py`` makes ``interface_web`` a regular package rather than an
implicit namespace package. A regular package resolves deterministically from
the first matching ``sys.path`` entry, which prevents a name collision with
``tests/unit/interface_web/`` (the dashboard test package) from shadowing this
package's modules — notably ``interface_web.app`` — under certain import
environments (e.g. when ``jpype.imports`` is active). See #1336.
"""

__version__ = "3.1.0"
