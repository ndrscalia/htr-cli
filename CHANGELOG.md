# Changelog

## [0.1.1] - 2026-06-01
- Lower `lxml` lower bound to `>=4.6.3` so the published wheel can resolve alongside `transkribus-client`'s `lxml==4.6.3` pin.

## [0.1.0] - 2026-06-01
- Initial public release.
- `Typer` CLI with subcommands: config, fetch-data, extract-data, split, process, process-tfe.
- Transkribus ground-truth pull via `transkribus-client`.
- Image preprocessing (OpenCV pipeline) and optional `TextFeatExtractor` pipeline.
- Train/val/test splitting with PyLaia-compatible output layout.
