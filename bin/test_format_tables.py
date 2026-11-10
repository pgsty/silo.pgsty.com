"""Verify East Asian Markdown table alignment and OINK {.wide .expand} rules."""

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import format_tables as ft


ROOT = Path(__file__).resolve().parents[1]


class FormatTablesTests(unittest.TestCase):
    def test_east_asian_display_width(self):
        self.assertEqual(ft.display_width("SILO"), 4)
        self.assertEqual(ft.display_width("全角字符"), 8)
        self.assertEqual(ft.display_width("中文（全角）"), 12)
        # Ambiguous punctuation matches POSIX/macOS UTF-8 wcwidth = 1
        self.assertEqual(ft.display_width("a — b · c → d"), 13)
        # Combining characters add zero width
        self.assertEqual(ft.display_width("e\u0301"), 1)

    def test_cjk_and_numeric_alignment_borders_match(self):
        raw = "\n".join([
            "| 仓库 | Issue | 状态 | 备注 |",
            "| :-- | --: | :-: | --- |",
            "| `pgsty/silo` | 171 | ✅ | 核心服务端（含内嵌 Console） |",
            "| `pgsty/mc` | 45 | OK | 客户端工具 |",
            "| **合计** | **216** | | |",
        ]) + "\n"
        formatted = ft.format_markdown(raw, is_oink_content=True)
        lines = formatted.splitlines()
        self.assertEqual(lines[-1], "{.wide .expand}")
        table_lines = lines[:-1]
        expected_pipes = ft.pipe_positions(table_lines[0])
        for row in table_lines[1:]:
            self.assertEqual(ft.pipe_positions(row), expected_pipes, msg=formatted)
        # Idempotency
        self.assertEqual(ft.format_markdown(formatted, is_oink_content=True), formatted)

    def test_escaped_pipes_and_code_fences_preserved(self):
        doc = "\n".join([
            "---",
            "title: Test",
            "---",
            "",
            "```markdown",
            "| unformatted | in_code_fence |",
            "|---|---|",
            "```",
            "",
            "| 模式 | 表达式 |",
            "| --- | --- |",
            r"| `FULL_OBJECT` | 拼接 `P1 \|\| ... \|\| Pn` |",
        ]) + "\n"
        formatted = ft.format_markdown(doc, is_oink_content=False)
        self.assertIn("| unformatted | in_code_fence |\n|---|---|", formatted)
        self.assertNotIn("{.wide .expand}", formatted)
        after_fence = formatted.split("```\n\n", 1)[1]
        lines = [ln for ln in after_fence.splitlines() if ln.startswith("| ")]
        self.assertEqual(len(lines), 3)
        self.assertEqual(ft.pipe_positions(lines[0]), ft.pipe_positions(lines[1]))
        self.assertEqual(ft.pipe_positions(lines[0]), ft.pipe_positions(lines[2]))

    def test_unescaped_pipe_excess_columns_reported(self):
        bad = [
            "| Type | Formula |",
            "| --- | --- |",
            "| `FULL_OBJECT` | `P1 || Pn` |",
        ]
        _, errors = ft.extract_tables(bad, "fixture.md")
        self.assertEqual(len(errors), 1)
        self.assertIn("fixture.md:3", errors[0])

    def test_fields_attribute_never_receives_expand(self):
        doc = "\n".join([
            "| 参数 | 类型 | 默认值 | 说明 |",
            "| --- | --- | --- | --- |",
            "| `offline_search` | boolean | `false` | 构建本地搜索索引 |",
            '{.fields meta="type default"}',
        ]) + "\n"
        formatted = ft.format_markdown(doc, is_oink_content=True)
        self.assertIn('{.fields meta="type default"}', formatted)
        self.assertNotIn(".expand", formatted)

    def test_bilingual_pair_syncs_wide_expand_and_indented_tables_keep_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = root / "content/guide"
            content.mkdir(parents=True)
            (content / "item.md").write_text(
                "1. Step\n\n"
                "   | Subcommand | Description |\n"
                "   | --- | --- |\n"
                "   | `mcli admin replicate info` | Display site replication status and peer synchronization details across all configured cluster buckets. |\n",
                encoding="utf-8",
            )
            (content / "item.zh.md").write_text(
                "1. 步骤\n\n"
                "   | 子命令 | 说明 |\n"
                "   | --- | --- |\n"
                "   | `mcli admin replicate info` | 查看复制状态。 |\n",
                encoding="utf-8",
            )
            changed, total, diags = ft.process_site(root, check_only=False)
            self.assertEqual(diags, [])
            self.assertEqual((changed, total), (2, 2))
            zh_lines = (content / "item.zh.md").read_text(encoding="utf-8").splitlines()
            self.assertEqual(zh_lines[-1], "   {.wide .expand}")

    def test_all_repository_markdown_tables_are_aligned(self):
        changed, total, diags = ft.process_site(ROOT, check_only=True)
        self.assertGreater(total, 0)
        self.assertEqual(diags, [])
        self.assertEqual(changed, 0, "Run `python3 bin/format_tables.py` to align Markdown tables.")


if __name__ == "__main__":
    unittest.main()
