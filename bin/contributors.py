#!/usr/bin/env python3
"""Render reviewed contributor data into repository records, READMEs, and site pages.

Requires PyYAML. Run from a workspace containing sibling SILO checkouts, or pass
--workspace. This command is offline: review all paginated GitHub issue/PR records
and update data/home/contributors.yaml before rendering. --check writes nothing.
"""

from __future__ import annotations

import argparse
import html
from pathlib import Path
import re
from urllib.parse import urlencode

import yaml


SITE = Path(__file__).resolve().parent.parent
GROUPS = (
    ("code", "Merged pull requests", "已合并 PR 的贡献者"),
    ("proposed", "Other pull-request authors", "其他 PR 贡献"),
    ("reports", "Issue reports", "问题报告与安全披露"),
)
STATES = (
    ("merged", "Merged PRs", "已合并 PR", "pull"),
    ("open", "Open PRs", "待合并 PR", "pull"),
    ("draft", "Draft PRs", "草稿 PR", "pull"),
    ("closed", "PRs closed without merging", "未直接合并的已关闭 PR", "pull"),
    ("issuesClosed", "Closed issues", "已关闭 issue", "issues"),
    ("issuesOpen", "Open issues", "未关闭 issue", "issues"),
)
SOURCE = "https://github.com/pgsty/silo.pgsty.com/blob/main/data/home/contributors.yaml"
ROLL = "https://github.com/pgsty/silo/blob/main/CONTRIBUTORS.md"


def people(data, repo=None):
    return [c for group, _, _ in GROUPS for c in data[group]
            if repo is None or any(a["repo"] == repo for a in c["activity"])]


def localized(entry, key, zh):
    return entry[key + "Zh"] if zh else entry[key]


def description(c, zh=False, repo=None):
    for a in c['activity']:
        if a['repo'] == repo and 'what' in a:
            return localized(a, 'what', zh)
    return localized(c, 'what', zh)


def wall(entries, zh=False, repo=None, website=False):
    lines = ['<div class="community-avatars">' if website else '<p align="center">']
    origin = '' if website else 'https://silo.pgsty.com'
    for c in entries:
        handle = c["handle"]
        size = 60 if c.get("featured") else 48
        title = html.escape(f'@{handle} — {description(c, zh, repo)}', quote=True)
        lines.append(f'<a href="https://github.com/{handle}"><img src="{origin}/images/contributors/{handle}.svg" width="{size}" height="{size}" alt="@{handle}" title="{title}"></a>')
    return "\n".join(lines + ['</div>' if website else '</p>'])


def activity(c, zh=False, repo=None, compact=True):
    lines = []
    for a in c["activity"]:
        if repo is not None and a["repo"] != repo:
            continue
        for state, en, cn, kind in STATES:
            numbers = a.get(state, [])
            if not numbers:
                continue
            label = cn if zh else en
            if compact and len(numbers) > 12:
                query = f'author:{c["handle"]} ' + ("is:issue" if kind == "issues" else "is:pr")
                query += " " + {"merged": "is:merged", "open": "is:open draft:false", "draft": "is:open draft:true", "closed": "is:closed is:unmerged", "issuesClosed": "is:closed", "issuesOpen": "is:open"}[state]
                url = f'https://github.com/{a["repo"]}/issues?{urlencode({"q": query})}'
                lines.append(f'[{a["repo"]}: {label} ({len(numbers)})]({url})')
            else:
                links = ", ".join(f'[{a["repo"]}#{n}](https://github.com/{a["repo"]}/{kind}/{n})' for n in numbers)
                lines.append(f"{label}: {links}")
    if "note" in c:
        lines.append(localized(c, "note", zh))
    return "<br>".join(lines)


def tables(data, zh=False, repo=None):
    selected = {c["handle"] for c in people(data, repo)}
    sections = []
    for group, en, cn in GROUPS:
        entries = [c for c in data[group] if c["handle"] in selected]
        if not entries:
            continue
        lines = [f'## {cn if zh else en}', '',
                 '| 贡献者 | 贡献 | 记录 |' if zh else '| Contributor | Contribution | Record |',
                 '| :-- | :-- | :-- |']
        for c in entries:
            what = description(c, zh, repo).replace("|", "&#124;")
            record = activity(c, zh, repo).replace("|", "&#124;")
            lines.append(f'| [@{c["handle"]}](https://github.com/{c["handle"]}) | {what} | {record} |')
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def scope_table(data, zh=False, repo=None):
    rows = ['| 仓库 | Issue | PR |' if zh else '| Repository | Issues | Pull requests |', '| :-- | --: | --: |']
    selected = [r for r in data["repositories"] if repo is None or r["repo"] == repo]
    for r in selected:
        rows.append(f'| [{r["repo"]}](https://github.com/{r["repo"]}) | {r["issues"]} | {r["pullRequests"]} |')
    rows.append(f'| **{"合计" if zh else "Total"}** | **{sum(r["issues"] for r in selected)}** | **{sum(r["pullRequests"] for r in selected)}** |')
    return "\n".join(rows)


def record(data, zh=False, repo=None, website=False):
    entries = people(data, repo)
    date = data["updated"][:10]
    count = len(entries)
    if zh:
        intro = f'截至 **{date}**，SILO 及相关项目共有 **{count} 位社区贡献者**，包括维护者、公开 issue / PR 作者，以及已公开致谢的安全披露者。'
        policy = '只要提交过 issue 或 PR，无论开启、关闭、草稿或未合并，均予以认可。同一账号只计一次。排序先列已合并 PR 的作者，再列其他 PR 作者和问题报告者；每组优先展示重要修复、已采纳方案和推动修复的报告，其余按首次参与时间排列。金色圆环突出显著贡献。'
        caveat = '原 PR 未合并但工作被后续修复吸收时，会单独列出采纳记录；关闭 issue 不等于问题已修复，代码合入也不等于已发布。自动化账号不计入人数。上游作者的署名继续保留在 Git 历史与版权声明中。'
    else:
        subject = 'SILO and related projects' if repo is None else f'`{repo}`'
        noun = 'contributor' if count == 1 else 'contributors'
        verb = 'is' if count == 1 else 'are'
        intro = f'As of **{date}**, **{count} community {noun}** {verb} credited in {subject}. The roll includes maintainers and every human issue / PR author' + (', plus the previously acknowledged security disclosure.' if repo is None else '.')
        policy = 'Opening an issue or PR counts, whether open, closed, draft, or unmerged. Each account appears once. Merged PR authors come first, followed by other PR authors and reporters. Within each group, significant fixes, adopted proposals, and reports that led to fixes take priority, followed by first participation. Gold rings highlight significant contributions.'
        caveat = 'When a proposal was incorporated through a later repair, its adoption is credited separately from the original PR status. A closed issue does not necessarily mean a fix, and merged source does not imply a published release. Automated accounts are excluded. Upstream authorship remains in Git history and copyright notices.'
    sections = [intro, policy, caveat, wall(entries, zh, repo, website), tables(data, zh, repo)]
    audit_title = '统计范围' if zh else 'Audit scope'
    note = ('以下统计来自全部分页的 GitHub issue / PR 记录，包含所有状态和自动化账号。' if zh else 'Counts below come from every page of the GitHub issue / PR records, across all states, including automated accounts.')
    if repo is None:
        public = sum(bool(c['activity']) for c in entries)
        supplemental = count - public
        security_noun = 'reporter' if supplemental == 1 else 'reporters'
        note += (f' 去重后有 {public} 位公开 issue / PR 作者，另保留 {supplemental} 位安全披露者。排除的自动化账号：' if zh else f' There are {public} distinct human public issue / PR authors, plus {supplemental} credited security {security_noun}. Excluded automated accounts: ') + ', '.join(f'`{b}`' for b in data['bots']) + ('。' if zh else '.')
    sections.extend([f'## {audit_title}', note, scope_table(data, zh, repo)])
    maintainers = [c for c in entries if any(sum(len(a.get(k, [])) for k, *_ in STATES) > 12 for a in c['activity'] if repo is None or a['repo'] == repo)]
    if maintainers:
        sections.append('## 维护者记录 {#maintainer-record}' if zh else '## Maintainer record')
        for c in maintainers:
            sections.append(f'<details>\n<summary>@{c["handle"]} — {"完整 issue / PR 记录" if zh else "complete issue / PR record"}</summary>\n\n' + activity(c, zh, repo, compact=False).replace('<br>', '\n\n') + '\n\n</details>')
    if repo is not None:
        sections.append(f'The [full SILO community roll]({ROLL}) recognizes contributions across the maintained server, Console, mcli, shared packages, and related repositories. Code contributions follow [CONTRIBUTING.md](CONTRIBUTING.md).')
    elif website:
        sections.append(('名单来源：' if zh else 'Record source: ') + f'[SILO CONTRIBUTORS.md]({ROLL}) · [GitHub data]({SOURCE}). ' + ('如有遗漏或描述不准确，欢迎提交 issue 或 PR。' if zh else 'Please open an issue or PR to correct missing or inaccurate credit.'))
    else:
        sections.extend(['## Keeping this record current', f'The reviewed [website contributor data]({SOURCE}) is shared by this record, the component records, README avatar walls, and both website languages. After auditing all issue / PR pages and reviewing adoption evidence, update that data and run `python3 bin/contributors.py` and `python3 bin/contributor_avatars.py` in the site checkout. Validate the generated records with `python3 bin/contributors.py --check`.', 'Code contributions follow the no-CLA, DCO policy in [CONTRIBUTING.md](CONTRIBUTING.md).'])
    text = '\n\n'.join(sections) + '\n'
    return text.replace('https://silo.pgsty.com/', '/') if website else text


def silo_readme_section(zh=False):
    """Keep the daily cards when regenerating the server README."""
    if zh:
        return """## 贡献者

<!-- Generated by silo.pgsty.com/bin/contributors.py. -->

每位 issue 或 PR 的作者都是 SILO 社区的一员，包括尚未合并的工作。已合并的修复、被采纳的方案和有效报告优先展示，其余参考首次参与时间；金色圆环突出经过审核的显著贡献。

<a href="CONTRIBUTORS.md">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/pgsty/silo/codex/repository-cards/contributors-dark.svg">
  <img src="https://raw.githubusercontent.com/pgsty/silo/codex/repository-cards/contributors-light.svg" alt="SILO 社区贡献者">
</picture>
</a>

[查看贡献记录与实际 PR 状态](CONTRIBUTORS.md)。

"""
    return """## Contributors

<!-- Generated by silo.pgsty.com/bin/contributors.py. -->

Every human issue or pull-request author is part of the SILO community, including open and unmerged work. Merged fixes, adopted proposals, and actionable reports receive priority, with first participation guiding the remaining order. Gold rings highlight reviewed significant contributions.

<a href="CONTRIBUTORS.md">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/pgsty/silo/codex/repository-cards/contributors-dark.svg">
  <img src="https://raw.githubusercontent.com/pgsty/silo/codex/repository-cards/contributors-light.svg" alt="SILO community contributors">
</picture>
</a>

[View contribution notes and actual PR status](CONTRIBUTORS.md).

"""


def readme_section(data, repo=None, zh=False):
    if repo is None:
        return silo_readme_section(zh)
    entries = people(data, repo)
    count, date = len(entries), data['updated'][:10]
    if zh:
        intro = f'截至 **{date}**，' + (f'SILO 及相关项目共有 **{count} 位社区贡献者**。' if repo is None else f'本仓库记录了 **{count} 位贡献者**。')
        intro += '提交 issue 或 PR 即认可为贡献，不以合并为前提；已合并的修复、被采纳的方案和有效报告优先展示，其余参考首次参与时间。金色圆环突出显著贡献。'
        tail = '[查看完整贡献记录](CONTRIBUTORS.md)，包括实际 PR 状态与后续采纳情况。'
    else:
        local_credit = f'**{count} contributor** is credited' if count == 1 else f'**{count} contributors** are credited'
        intro = f'As of **{date}**, ' + (f'**{count} community contributors** have helped build SILO and related projects.' if repo is None else f'{local_credit} in this repository.')
        intro += ' Every human issue or PR author counts, regardless of merge status. Merged fixes, adopted proposals, and actionable reports receive priority, with first participation guiding the remaining order. Gold rings highlight significant contributions.'
        tail = '[View the contribution record](CONTRIBUTORS.md), including actual PR status and work incorporated through later fixes.'
    return ('## 贡献者' if zh else '## Contributors') + '\n\n<!-- Generated by silo.pgsty.com/bin/contributors.py. -->\n\n' + intro + '\n\n' + wall(entries, zh, repo) + '\n\n' + tail + '\n\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=SITE.parent)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = yaml.safe_load((SITE / 'data/home/contributors.yaml').read_text())
    entries = people(data)
    handles = [c['handle'].lower() for c in entries]
    if len(handles) != len(set(handles)):
        raise SystemExit('Duplicate contributor handles')
    outputs = {}
    for repo, files, before in (
        ('silo', ('README.md', 'README_ZH.md'), '## Background'),
        ('silo-console', ('README.md',), '## License, Attribution, and Trademarks'),
        ('mc', ('README.md', 'README_ZH.md'), '## Background'),
        ('silo-pkg', ('README.md',), '## License'),
    ):
        directory = args.workspace / repo
        scope = None if repo == 'silo' else f'pgsty/{repo}'
        outputs[directory / 'CONTRIBUTORS.md'] = '# Contributors\n\n<!-- Generated by silo.pgsty.com/bin/contributors.py. -->\n\n' + record(data, repo=scope)
        for filename in files:
            path = directory / filename
            old = path.read_text()
            zh = filename == 'README_ZH.md'
            section = readme_section(data, scope, zh)
            pattern = r'^## ' + ('贡献者' if zh else 'Contributors') + r'\n.*?(?=^## |\Z)'
            if re.search(pattern, old, flags=re.M | re.S):
                new = re.sub(pattern, lambda _: section, old, count=1, flags=re.M | re.S)
            else:
                anchor = '## 背景' if zh else before
                if anchor not in old:
                    raise SystemExit(f'Missing insertion point in {path}')
                new = old.replace(anchor, section + anchor, 1)
            outputs[path] = new
    for zh in (False, True):
        title = '贡献者' if zh else 'Contributors'
        url = '/zh/about/contributors/' if zh else '/about/contributors/'
        description = 'SILO 社区贡献者、贡献记录与认可口径。' if zh else 'SILO community contributors, contribution records, and recognition policy.'
        frontmatter = f'---\ntitle: "{title}"\nlinkTitle: "{title}"\ndescription: "{description}"\nurl: "{url}"\nweight: 35\ntype: docs\ncontributor_page: true\nicon: fa-solid fa-users\n---\n\n'
        path = SITE / 'content/about' / ('contributors.zh.md' if zh else 'contributors.md')
        outputs[path] = frontmatter + '<!-- Generated by bin/contributors.py. -->\n\n' + record(data, zh, website=True)
    changed = [p for p, text in outputs.items() if not p.exists() or p.read_text() != text]
    for p in changed:
        print(('out of date: ' if args.check else 'updated: ') + str(p))
        if not args.check:
            p.write_text(outputs[p])
    if args.check and changed:
        return 1
    print(f'{len(entries)} contributors; {len(outputs)} generated files {"verified" if args.check else "synchronized"}.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
