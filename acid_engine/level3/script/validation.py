"""Validate implementation against ImplementationRequirements."""
from __future__ import annotations

from acid_engine.level3.script.module import ScriptModule


def validate_implementation_requirements(script: ScriptModule) -> list[str]:
    """
    Check that script.implementation satisfies required_methods,
    required_exports, required_signatures.
    Returns a list of error messages (empty = valid).
    """
    errors: list[str] = []
    impl = script.implementation
    req = script.specification.implementation_requirements

    # required_methods: check that impl has callable attributes with those names
    for method_name in req.required_methods:
        if not hasattr(impl, method_name) or not callable(getattr(impl, method_name)):
            errors.append(f"Missing required method: {method_name}")

    # required_exports: check module-level attributes (for functions/classes)
    if req.required_exports:
        import sys
        mod_name = getattr(impl, '__module__', None)
        if mod_name and mod_name in sys.modules:
            mod = sys.modules[mod_name]
            for export_name in req.required_exports:
                if not hasattr(mod, export_name):
                    errors.append(f"Missing required export: {export_name}")

    # required_signatures: placeholder — just check if attribute exists
    for sig_name in req.required_signatures:
        if not hasattr(impl, sig_name):
            errors.append(f"Missing required signature: {sig_name}")

    return errors