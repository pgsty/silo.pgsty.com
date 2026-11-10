#!/usr/bin/env python3
"""Format GFM Markdown tables with East Asian display-width alignment and OINK attributes.

Full-width characters (East Asian Width W and F) count as 2 ASCII columns,
combining/format characters count as 0, and all other printable characters count
as 1, matching POSIX/macOS wcwidth under UTF-8 locales. Large tables inside
content/ receive OINK's {.wide .expand} block attribute unless incompatible
(such as .fields).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys
import unicodedata


SITE_ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_DIRS = {".git", "public", "resources", ".venv-check", "node_modules", "__pycache__"}
DELIM_CELL_RE = re.compile(r"^:?-{1,}:?$")
FENCE_OPEN_RE = re.compile(r"^[ \t]*(?:>[ \t]*)*(`{3,}|~{3,})(.*)$")
PREFIX_RE = re.compile(r"^([ \t]*(?:>[ \t]*)*)")
FIELDS_CLASS_RE = re.compile(r"(?<![A-Za-z0-9_-])\.fields(?![A-Za-z0-9_-])")
WIDE_CLASS_RE = re.compile(r"(?<![A-Za-z0-9_-])\.(?:wide|td-table--wide)(?![A-Za-z0-9_-])")
EXPAND_CLASS_RE = re.compile(r"(?<![A-Za-z0-9_-])\.expand(?![A-Za-z0-9_-])")
HTML_BLOCK_OPEN_RE = re.compile(r"^[ \t]*<(table|pre|script|style)\b", re.IGNORECASE)


def char_width(ch: str) -> int:
    """Return monospace column width of a single Unicode codepoint."""
    if unicodedata.combining(ch) or unicodedata.category(ch) in ("Mn", "Me", "Cf"):
        return 0
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def display_width(text: str) -> int:
    """Return total monospace display width of text (full-width = 2, ASCII = 1)."""
    return sum(char_width(ch) for ch in text)


def visible_text(cell: str) -> str:
    """Approximate rendered inline text for sizing heuristics."""
    s = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", cell)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&#124;", "|").replace(r"\|", "|")
    return s


def split_gfm_row(line_body: str) -> tuple[list[str], bool, bool] | None:
    """Split a GFM table row on unescaped '|' pipes."""
    s = line_body.strip()
    if not s:
        return None

    cells: list[str] = []
    cur: list[str] = []
    backslashes = 0
    for ch in s:
        if ch == "\\":
            backslashes += 1
            cur.append(ch)
        elif ch == "|" and backslashes % 2 == 0:
            cells.append("".join(cur))
            cur = []
            backslashes = 0
        else:
            backslashes = 0
            cur.append(ch)
    cells.append("".join(cur))

    has_leading = s.startswith("|")
    trailing_bs = 0
    idx = len(s) - 2
    while idx >= 0 and s[idx] == "\\":
        trailing_bs += 1
        idx -= 1
    has_trailing = s.endswith("|") and (trailing_bs % 2 == 0)

    if has_leading:
        cells = cells[1:]
    if has_trailing and cells:
        cells = cells[:-1]

    normalized = [c.replace("\t", " ").strip() for c in cells]
    return normalized, has_leading, has_trailing


def parse_delim_row(line_body: str) -> list[str] | None:
    """Return delimiter cells if line_body is a valid GFM table delimiter row."""
    if "|" not in line_body:
        return None
    parsed = split_gfm_row(line_body)
    if parsed is None:
        return None
    cells, lead, trail = parsed
    if not cells:
        return None
    if len(cells) == 1 and not (lead or trail):
        return None
    if all(DELIM_CELL_RE.match(c) for c in cells):
        return cells
    return None


def parse_prefix(line: str) -> str:
    """Extract leading whitespace and blockquote markers."""
    m = PREFIX_RE.match(line)
    return m.group(1) if m else ""


def is_attr_line(body: str) -> bool:
    """Return True if body is a Goldmark block attribute line like {.wide .expand}."""
    s = body.strip()
    if not (s.startswith("{") and s.endswith("}")):
        return False
    if s.startswith("{{") or s.endswith("}}"):
        return False
    if "|" in s:
        return False
    return True


@dataclass
class TableBlock:
    start_line: int  # 0-based inclusive
    end_line: int    # 0-based exclusive (excludes attr_line)
    prefix: str
    header: list[str]
    delims: list[str]
    body_rows: list[list[str]]
    attr_line: str | None
    attr_idx: int | None


def column_spec(delim: str) -> tuple[str, int]:
    """Return (alignment, min_width) for a delimiter cell."""
    left = delim.startswith(":")
    right = delim.endswith(":")
    if left and right:
        return "center", 5
    if left:
        return "left", 4
    if right:
        return "right", 4
    return "default", 3


def format_delim_cell(align: str, width: int) -> str:
    if align == "center":
        return ":" + ("-" * (width - 2)) + ":"
    if align == "left":
        return ":" + ("-" * (width - 1))
    if align == "right":
        return ("-" * (width - 1)) + ":"
    return "-" * width


def pad_cell(cell: str, align: str, width: int) -> str:
    pad = width - display_width(cell)
    if pad <= 0:
        return cell
    if align == "right":
        return (" " * pad) + cell
    if align == "center":
        left_pad = pad // 2
        right_pad = pad - left_pad
        return (" " * left_pad) + cell + (" " * right_pad)
    return cell + (" " * pad)


def format_table_block(table: TableBlock) -> list[str]:
    """Format a parsed TableBlock into aligned Markdown lines (excluding attr_line)."""
    num_cols = len(table.header)
    specs = [column_spec(d) for d in table.delims]
    all_content_rows = [table.header, *table.body_rows]

    col_widths: list[int] = []
    for j in range(num_cols):
        min_w = specs[j][1]
        max_cell_w = max(display_width(row[j]) for row in all_content_rows)
        col_widths.append(max(min_w, max_cell_w))

    out: list[str] = []
    hdr_cells = [pad_cell(table.header[j], specs[j][0], col_widths[j]) for j in range(num_cols)]
    out.append(f"{table.prefix}| " + " | ".join(hdr_cells) + " |")
    dlm_cells = [format_delim_cell(specs[j][0], col_widths[j]) for j in range(num_cols)]
    out.append(f"{table.prefix}| " + " | ".join(dlm_cells) + " |")
    for row in table.body_rows:
        row_cells = [pad_cell(row[j], specs[j][0], col_widths[j]) for j in range(num_cols)]
        out.append(f"{table.prefix}| " + " | ".join(row_cells) + " |")
    return out


def format_table_text(table_md: str) -> str:
    """Format a standalone GFM table string (convenience helper for generators)."""
    lines = table_md.splitlines()
    tables, errors = extract_tables(lines, "<memory>")
    if errors:
        raise ValueError("; ".join(errors))
    if len(tables) != 1:
        raise ValueError(f"expected 1 table, got {len(tables)}")
    t = tables[0]
    rendered = format_table_block(t)
    if t.attr_line is not None:
        rendered.append(f"{t.prefix}{t.attr_line}")
    return "\n".join(rendered)


def format_markdown(text: str, is_oink_content: bool = True) -> str:
    """Format all GFM tables in a Markdown document string."""
    tables, errors = extract_tables(text.splitlines(), "<memory>")
    if errors:
        raise ValueError("; ".join(errors))
    return render_document(text, tables, is_oink_content=is_oink_content)


def is_large_table(table: TableBlock) -> bool:
    """Return True if table benefits from OINK's {.wide .expand} controls."""
    num_cols = len(table.header)
    num_body_rows = len(table.body_rows)
    if num_cols >= 3 or num_body_rows >= 10:
        return True
    all_rows = [table.header, *table.body_rows]
    vis_col_max = [
        max(display_width(visible_text(row[j])) for row in all_rows)
        for j in range(num_cols)
    ]
    if sum(vis_col_max) >= 80 or vis_col_max[0] >= 32:
        return True
    return False


def has_wide_or_expand(attr_line: str | None) -> bool:
    if not attr_line:
        return False
    return bool(WIDE_CLASS_RE.search(attr_line) or EXPAND_CLASS_RE.search(attr_line))


def merge_wide_expand(attr_line: str | None) -> str:
    """Add .wide and .expand to attr_line unless .fields is present."""
    if attr_line is None:
        return "{.wide .expand}"
    s = attr_line.strip()
    if FIELDS_CLASS_RE.search(s):
        return s
    inner = s[1:-1].strip()
    additions: list[str] = []
    if not WIDE_CLASS_RE.search(s):
        additions.append(".wide")
    if not EXPAND_CLASS_RE.search(s):
        additions.append(".expand")
    if not additions:
        return s
    if inner:
        return "{" + inner + " " + " ".join(additions) + "}"
    return "{" + " ".join(additions) + "}"


def strip_frontmatter_end(lines: list[str]) -> int:
    if not lines:
        return 0
    first = lines[0].strip()
    if first in ("---", "+++"):
        for i in range(1, len(lines)):
            if lines[i].strip() == first:
                return i + 1
    return 0


def extract_tables(lines: list[str], source_label: str) -> tuple[list[TableBlock], list[str]]:
    """Scan Markdown lines and return all parsed GFM tables plus any structural errors."""
    tables: list[TableBlock] = []
    errors: list[str] = []
    start = strip_frontmatter_end(lines)
    in_fence: str | None = None
    in_math = False
    in_html_tag: str | None = None
    in_comment = False

    i = start
    n = len(lines)
    while i < n:
        line = lines[i]

        if in_comment:
            if "-->" in line:
                in_comment = False
            i += 1
            continue
        if "<!--" in line and "-->" not in line[line.index("<!--") + 4:]:
            in_comment = True
            i += 1
            continue

        if in_fence is not None:
            close_re = re.compile(
                r"^[ \t]*(?:>[ \t]*)*" + re.escape(in_fence[0]) + r"{" + str(len(in_fence)) + r",}[ \t]*$"
            )
            if close_re.match(line):
                in_fence = None
            i += 1
            continue

        fm = FENCE_OPEN_RE.match(line)
        if fm:
            in_fence = fm.group(1)
            i += 1
            continue

        stripped = line.strip()
        if in_math:
            if stripped.endswith("$$"):
                in_math = False
            i += 1
            continue
        if stripped == "$$" or (stripped.startswith("$$") and not stripped.endswith("$$")):
            in_math = True
            i += 1
            continue

        if in_html_tag is not None:
            if re.search(rf"</{in_html_tag}\s*>", line, re.IGNORECASE):
                in_html_tag = None
            i += 1
            continue
        hm = HTML_BLOCK_OPEN_RE.match(line)
        if hm:
            tag = hm.group(1).lower()
            if not re.search(rf"</{tag}\s*>", line, re.IGNORECASE):
                in_html_tag = tag
            i += 1
            continue

        if i + 1 < n and not FENCE_OPEN_RE.match(lines[i + 1]):
            pref0 = parse_prefix(lines[i])
            pref1 = parse_prefix(lines[i + 1])
            body0 = lines[i][len(pref0):]
            body1 = lines[i + 1][len(pref1):]
            if pref0.strip() == pref1.strip() and "|" in body0 and body0.strip():
                delims = parse_delim_row(body1)
                if delims is not None:
                    hdr_parsed = split_gfm_row(body0)
                    if hdr_parsed is not None and len(hdr_parsed[0]) == len(delims):
                        num_cols = len(delims)
                        body_rows: list[list[str]] = []
                        j = i + 2
                        while j < n:
                            if FENCE_OPEN_RE.match(lines[j]):
                                break
                            prefj = parse_prefix(lines[j])
                            bodyj = lines[j][len(prefj):]
                            if prefj.strip() != pref0.strip():
                                break
                            sbody = bodyj.strip()
                            if not sbody or is_attr_line(sbody) or "|" not in sbody:
                                break
                            row_parsed = split_gfm_row(bodyj)
                            if row_parsed is None:
                                break
                            cells = row_parsed[0]
                            if len(cells) > num_cols:
                                errors.append(
                                    f"{source_label}:{j + 1}: row has {len(cells)} cells "
                                    f"(expected {num_cols}; check for unescaped '|')"
                                )
                                j += 1
                                continue
                            if len(cells) < num_cols:
                                cells = cells + [""] * (num_cols - len(cells))
                            body_rows.append(cells)
                            j += 1

                        attr_line: str | None = None
                        attr_idx: int | None = None
                        if j < n:
                            prefj = parse_prefix(lines[j])
                            bodyj = lines[j][len(prefj):].strip()
                            if prefj.strip() == pref0.strip() and is_attr_line(bodyj):
                                attr_line = bodyj
                                attr_idx = j

                        tables.append(
                            TableBlock(
                                start_line=i,
                                end_line=j,
                                prefix=pref0,
                                header=hdr_parsed[0],
                                delims=delims,
                                body_rows=body_rows,
                                attr_line=attr_line,
                                attr_idx=attr_idx,
                            )
                        )
                        i = (attr_idx + 1) if attr_idx is not None else j
                        continue

        i += 1

    return tables, errors


def pipe_positions(line: str) -> list[int]:
    """Return display-column offsets of all unescaped '|' characters in line."""
    positions: list[int] = []
    col = 0
    backslashes = 0
    for ch in line:
        if ch == "\\":
            backslashes += 1
        elif ch == "|" and backslashes % 2 == 0:
            positions.append(col)
            backslashes = 0
        else:
            backslashes = 0
        col += char_width(ch)
    return positions


def render_document(
    text: str,
    tables: list[TableBlock],
    is_oink_content: bool,
    force_expand_indices: set[int] | None = None,
) -> str:
    """Rebuild document text with all TableBlocks formatted."""
    if not tables:
        return text
    has_trailing_nl = text.endswith("\n")
    lines = text.splitlines()
    force = force_expand_indices or set()

    out: list[str] = []
    cursor = 0
    for idx, t in enumerate(tables):
        out.extend(lines[cursor:t.start_line])
        out.extend(format_table_block(t))
        should_expand = is_oink_content and (idx in force or is_large_table(t) or has_wide_or_expand(t.attr_line))
        if should_expand:
            new_attr = merge_wide_expand(t.attr_line)
            out.append(f"{t.prefix}{new_attr}")
        elif t.attr_line is not None:
            out.append(f"{t.prefix}{t.attr_line}")
        cursor = (t.attr_idx + 1) if t.attr_idx is not None else t.end_line

    out.extend(lines[cursor:])
    result = "\n".join(out)
    if has_trailing_nl:
        result += "\n"
    return result


def iter_markdown_files(root: Path) -> list[Path]:
    return sorted(
        p for p in root.rglob("*.md")
        if not any(part in EXCLUDED_DIRS for part in p.relative_to(root).parts)
    )


def process_site(root: Path, check_only: bool = False) -> tuple[int, int, list[str]]:
    """Format or check all Markdown files under root.

    Returns (files_changed, tables_formatted, diagnostics).
    """
    md_files = iter_markdown_files(root)
    raw_by_rel: dict[str, bytes] = {}
    text_by_rel: dict[str, str] = {}
    tables_by_rel: dict[str, list[TableBlock]] = {}
    errs_by_rel: dict[str, list[str]] = {}
    diagnostics: list[str] = []

    for path in md_files:
        rel = path.relative_to(root).as_posix()
        raw = path.read_bytes()
        raw_by_rel[rel] = raw
        text = raw.decode("utf-8")
        text_by_rel[rel] = text
        tables, errs = extract_tables(text.splitlines(), rel)
        tables_by_rel[rel] = tables
        errs_by_rel[rel] = errs
        diagnostics.extend(errs)

    force_by_rel: dict[str, set[int]] = {rel: set() for rel in text_by_rel}
    for rel, tables in tables_by_rel.items():
        if not rel.startswith("content/") or rel.endswith(".zh.md"):
            continue
        zh_rel = rel[:-3] + ".zh.md"
        zh_tables = tables_by_rel.get(zh_rel)
        if zh_tables is not None and len(tables) == len(zh_tables):
            for idx, (t_en, t_zh) in enumerate(zip(tables, zh_tables)):
                if (
                    is_large_table(t_en)
                    or is_large_table(t_zh)
                    or has_wide_or_expand(t_en.attr_line)
                    or has_wide_or_expand(t_zh.attr_line)
                ):
                    force_by_rel[rel].add(idx)
                    force_by_rel[zh_rel].add(idx)

    files_changed = 0
    total_tables = sum(len(ts) for ts in tables_by_rel.values())

    for path in md_files:
        rel = path.relative_to(root).as_posix()
        tables = tables_by_rel[rel]
        if not tables or errs_by_rel[rel]:
            continue
        is_oink = rel.startswith("content/")
        old_text = text_by_rel[rel]
        new_text = render_document(old_text, tables, is_oink, force_by_rel[rel])

        new_tables, new_errs = extract_tables(new_text.splitlines(), rel)
        if new_errs:
            diagnostics.extend(new_errs)
            continue
        new_lines = new_text.splitlines()
        for t in new_tables:
            expected_pos = pipe_positions(new_lines[t.start_line])
            for line_no in range(t.start_line + 1, t.end_line):
                actual_pos = pipe_positions(new_lines[line_no])
                if actual_pos != expected_pos:
                    diagnostics.append(
                        f"{rel}:{line_no + 1}: internal alignment bug: "
                        f"pipes at {actual_pos} != header {expected_pos}"
                    )

        if new_text != old_text:
            files_changed += 1
            if check_only:
                old_lines = old_text.splitlines()
                reported = False
                for t in tables:
                    hdr_pos = pipe_positions(old_lines[t.start_line])
                    for line_no in range(t.start_line + 1, t.end_line):
                        if pipe_positions(old_lines[line_no]) != hdr_pos:
                            diagnostics.append(f"{rel}:{t.start_line + 1}: unaligned Markdown table")
                            reported = True
                            break
                    if reported:
                        break
                if not reported:
                    diagnostics.append(f"{rel}:{tables[0].start_line + 1}: uncanonical Markdown table formatting")
            else:
                current_raw = path.read_bytes()
                if current_raw != raw_by_rel[rel]:
                    diagnostics.append(f"{rel}: skipped write because file changed concurrently on disk")
                    continue
                path.write_bytes(new_text.encode("utf-8"))

    return files_changed, total_tables, diagnostics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=SITE_ROOT, help="Repository root directory")
    parser.add_argument("--check", action="store_true", help="Verify formatting without modifying files")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    files_changed, total_tables, diagnostics = process_site(root, check_only=args.check)
    for msg in diagnostics:
        print(msg, file=sys.stderr)
    if args.check:
        if diagnostics or files_changed:
            print(
                f"FAIL: {files_changed} file(s) need table formatting ({len(diagnostics)} issue(s) across {total_tables} tables).",
                file=sys.stderr,
            )
            return 1
        print(f"OK: {total_tables} Markdown tables verified across {root}.")
        return 0

    if diagnostics:
        print(
            f"Formatted {files_changed} file(s) ({total_tables} tables), with {len(diagnostics)} issue(s) requiring attention.",
            file=sys.stderr,
        )
        return 1
    print(f"Formatted {files_changed} file(s); {total_tables} Markdown tables aligned.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
