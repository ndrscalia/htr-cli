from pathlib import Path

import typer
from lxml import etree
from rich import print
from rich.progress import track

app = typer.Typer(rich_markup_mode="rich")


def _polygon_centroid(points: str) -> tuple[float, float]:
    pts = [tuple(map(int, p.split(","))) for p in points.split()]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _line_anchor(line, ns) -> tuple[float, float] | None:
    """Where the text actually sits: baseline midpoint if available, else polygon
    centroid. The baseline is a better anchor than the polygon centroid because
    polygons include ascender/descender padding and can spill outside a region's
    bbox even when the line clearly belongs to it."""
    baseline = line.find("p:Baseline", namespaces=ns)
    if baseline is not None and baseline.get("points"):
        return _polygon_centroid(baseline.get("points"))
    coords = line.find("p:Coords", namespaces=ns)
    if coords is not None and coords.get("points"):
        return _polygon_centroid(coords.get("points"))
    return None


def _polygon_bbox(points: str) -> tuple[int, int, int, int]:
    pts = [tuple(map(int, p.split(","))) for p in points.split()]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def _bbox_contains(bbox: tuple[int, int, int, int], x: float, y: float) -> bool:
    xmin, ymin, xmax, ymax = bbox
    return xmin <= x <= xmax and ymin <= y <= ymax


def _has_reading_order(custom: str | None) -> bool:
    return custom is not None and "readingOrder" in custom


def _has_structure(custom: str | None) -> bool:
    return custom is not None and "structure" in custom


def _prepend_reading_order(custom: str | None, index: int) -> str:
    ro = f"readingOrder {{index:{index};}}"
    return f"{ro} {custom}" if custom else ro


@app.command(rich_help_panel="Pre-processing")
def port_escriptorium():
    """
    Normalize eScriptorium-style PAGE XML in `data/xml_texts/` to the Transkribus
    convention `data-extraction` expects: lines nested in their typed `TextRegion`
    and a `readingOrder` annotation on every region and line. Idempotent — files
    already shaped that way are skipped.
    """
    files_dir = Path("data/xml_texts/")
    if not files_dir.exists():
        raise typer.BadParameter(f"directory not found: {files_dir}")

    files = sorted(files_dir.glob("*.xml"))
    if not files:
        print(f"[yellow]no XML files in {files_dir}[/yellow]")
        raise typer.Exit()

    ported = 0
    skipped = 0
    dropped_total = 0

    for file in track(files, description="Porting eScriptorium PAGE XML"):
        tree = etree.parse(file)
        root = tree.getroot()
        ns_uri = etree.QName(root.tag).namespace
        ns = {"p": ns_uri} if ns_uri else {}

        page = root.find("p:Page", namespaces=ns) if ns else root.find("Page")
        if page is None:
            skipped += 1
            continue

        regions = page.findall("p:TextRegion", namespaces=ns)
        if not regions:
            skipped += 1
            continue

        if any(_has_reading_order(r.get("custom")) for r in regions):
            skipped += 1
            continue

        typed_regions = [r for r in regions if _has_structure(r.get("custom"))]
        dummy_regions = [r for r in regions if not _has_structure(r.get("custom"))]
        if not typed_regions:
            skipped += 1
            continue

        typed_bboxes = []
        for r in typed_regions:
            coords = r.find("p:Coords", namespaces=ns)
            bbox = _polygon_bbox(coords.get("points")) if coords is not None else None
            typed_bboxes.append((r, bbox))

        dropped = 0
        for dr in dummy_regions:
            for line in list(dr.findall("p:TextLine", namespaces=ns)):
                anchor = _line_anchor(line, ns)
                dr.remove(line)
                if anchor is None:
                    dropped += 1
                    continue
                ax, ay = anchor
                assigned = next((r for r, bb in typed_bboxes if bb and _bbox_contains(bb, ax, ay)), None)
                if assigned is None:
                    dropped += 1
                    continue
                assigned.append(line)

        for dr in dummy_regions:
            page.remove(dr)

        doc_ordered = page.findall("p:TextRegion", namespaces=ns)
        for idx, r in enumerate(doc_ordered):
            r.set("custom", _prepend_reading_order(r.get("custom"), idx))

        for r in doc_ordered:
            lines = r.findall("p:TextLine", namespaces=ns)
            sorted_lines = sorted(
                lines,
                key=lambda ln: (_line_anchor(ln, ns) or (0.0, 0.0))[1],
            )
            for line in lines:
                r.remove(line)
            for idx, line in enumerate(sorted_lines):
                line.set("custom", _prepend_reading_order(line.get("custom"), idx))
                r.append(line)

        tree.write(str(file), xml_declaration=True, encoding="UTF-8", standalone=True)
        ported += 1
        dropped_total += dropped

    print(
        f"\n[bold bright_green]ported[/bold bright_green]: {ported}    "
        f"[bold]skipped[/bold] (already normalized or no typed regions): {skipped}    "
        f"[bold yellow]dropped lines[/bold yellow] (centroid outside every typed region): {dropped_total}"
    )
