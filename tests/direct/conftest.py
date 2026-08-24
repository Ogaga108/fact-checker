"""Windows compatibility shim for genlayer-test 0.29.2.

The direct runner's stdin injection deletes its temp file while fd 0 still
holds it open, which raises PermissionError on Windows. By the time that
happens the injection itself has already succeeded, so we swallow exactly
that error and let everything else propagate.
"""

try:
    from gltest.direct import loader as _loader

    _original = getattr(_loader, "_inject_message_to_fd0", None)
    if _original is not None:

        def _safe_inject(vm):
            try:
                _original(vm)
            except PermissionError:
                pass

        _loader._inject_message_to_fd0 = _safe_inject
except Exception:
    pass
