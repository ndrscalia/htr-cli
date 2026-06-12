# Changelog

## [0.3.1] - 2026-06-12
- Fix `process-images` and `process-images-tfe` boolean toggle flags that were silently no-ops because they used a single `--no-X` name instead of the `--X/--no-X` slash form Typer requires for on/off behavior.

## [0.3.0] - 2026-06-09
- Add `port-escriptorium` subcommand:
    - normalizes eScriptorium-style PAGE-XML into the Transkribus convention for which `data-extraction` was written;
    - lines get nested in the typed `TextRegion`;
    - `readingOrder` is injected on regions and lines;
    - already compliant files are skipped;
    - files are modified in place;
    - anchor for assignment + sort is the baseline midpoint (with polygon's centroid as fallback), because a centroid can land just outside a region's bbox even if it belongs to it.
- Add helper to let `data-extraction` find the images regardless of extension.
- Add dynamical namespace reading to avoid `data-extraction` crashing with PAGE-XML 2019 schema.

## [0.2.0] - 2026-06-04
- Add `--custom-train`, `--custom-val`, `--custom-test` flags to `split-dataset` for supplying pre-determined page splits via text files. Files accept page names or full line ids, so the `dataset/{train,val,test}_ids.txt` files this command writes can be fed back in to reproduce a previous split.
- Fixed pre-existing bug at the omit-unclear filter and added an explicit switch for this option (`--no-omit-unclear` / `-U`).

## [0.1.2] - 2026-06-01
- Make `transkribus-client` an optional extra (`htr-cli[transkribus]`). The `pull-transkribus` subcommand now lazy-imports it and raises a friendly error if missing.
- This lets pip/pipx users install the base package without hitting `transkribus-client`'s `lxml==4.6.3` pin.

## [0.1.1] - 2026-06-01
- Lower `lxml` lower bound to `>=4.6.3` so the published wheel can resolve alongside `transkribus-client`'s `lxml==4.6.3` pin.

## [0.1.0] - 2026-06-01
- Initial public release.
- `Typer` CLI with subcommands: config, fetch-data, extract-data, split, process, process-tfe.
- Transkribus ground-truth pull via `transkribus-client`.
- Image preprocessing (OpenCV pipeline) and optional `TextFeatExtractor` pipeline.
- Train/val/test splitting with PyLaia-compatible output layout.
