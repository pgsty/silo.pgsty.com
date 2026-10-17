"""The documentation tree gives every page one canonical parent."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class NavigationTests(unittest.TestCase):
    def test_pages_have_one_navigation_placement(self):
        data = json.loads((ROOT / "data/docs_nav.json").read_text())
        seen = set()
        def walk(nodes):
            for node in nodes:
                page = node.get("page")
                if page:
                    self.assertNotIn(page, seen, f"duplicate navigation page: {page}")
                    seen.add(page)
                walk(node.get("children", []))
        walk(data["sections"])

    def test_child_lookup_has_one_parent(self):
        data = json.loads((ROOT / "data/docs_nav.json").read_text())
        seen = set()
        for children in data["children_by_url"].values():
            for child in children:
                self.assertNotIn(child, seen, f"duplicate navigation child: {child}")
                seen.add(child)

if __name__ == "__main__":
    unittest.main()
