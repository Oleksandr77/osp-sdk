# Contributing to OSP

Thank you for your interest in contributing to the Open Skills Protocol!

## Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Install dependencies: `pip install -r requirements.txt`
4. Make your changes
5. Run tests: `python -m pytest tests/ -v`
6. Submit a Pull Request

## Code Style

- Python 3.9+ compatible
- Type hints on all public functions
- Docstrings on public classes and methods
- Use `osp_` namespace for all protocol packages (not `asp_`)

## Testing

All changes must pass the existing test suite:

```bash
python -m pytest tests/ -v --tb=short
```

For conformance-related changes, also run:

```bash
python tests/conformance_harness.py
```

## Architecture Rules

- `osp_core/` — Protocol models and crypto only. No I/O, no external deps.
- `osp_server/` — Reference implementation. May depend on `osp_core/`.
- `osp_std/` — Standard library for skills. Sandboxed by design.
- `asp/` — Python SDK. Wraps `osp_server/` for developer UX.

## Security

If you discover a security vulnerability, please report it privately rather than opening a public issue.

## License

By contributing, you agree that your contributions will be licensed under Apache License 2.0.
