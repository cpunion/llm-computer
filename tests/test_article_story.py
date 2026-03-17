from __future__ import annotations

import unittest

from llm_computer.article_story import (
    DOCS_DIR,
    build_method_stories,
    render_article_markdown,
    render_implementation_ladder_svg,
    render_latency_svg,
    render_remotion_data_js,
)


def _read_json(name: str) -> dict[str, object]:
    import json

    return json.loads((DOCS_DIR / name).read_text(encoding="utf-8"))


class ArticleStoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.comparison = _read_json("five-way-comparison.json")
        self.article_examples = _read_json("article-example-validation.json")
        self.sudoku = _read_json("sudoku-result-validation.json")
        self.methods = build_method_stories(self.comparison, self.article_examples, self.sudoku)

    def test_build_method_stories_orders_five_methods_by_depth(self) -> None:
        self.assertEqual(5, len(self.methods))
        self.assertEqual(
            [
                "reference_direct",
                "append_only_naive_direct",
                "closed_source_sidecar",
                "open_source_wrapper",
                "open_source_execution_block",
            ],
            [method.method_id for method in self.methods],
        )

    def test_render_article_mentions_all_five_sections(self) -> None:
        article = render_article_markdown(self.methods, self.comparison, self.article_examples, self.sudoku)

        self.assertIn("# Five Ways We Tried to Execute Programs with LLMs", article)
        self.assertIn("## Original Reference", article)
        self.assertIn("https://www.percepta.ai/blog/can-llms-be-computers", article)
        for method in self.methods:
            self.assertIn(f"### {method.depth_rank}. {method.title}", article)
        self.assertIn("assets/five-implementation-overview.gif", article)
        self.assertIn("assets/five-implementation-validation-matrix.svg", article)

    def test_svg_and_remotion_outputs_are_well_formed(self) -> None:
        ladder = render_implementation_ladder_svg(self.methods)
        latency = render_latency_svg(self.methods)
        remotion_data = render_remotion_data_js(self.methods)

        self.assertTrue(ladder.startswith('<svg '))
        self.assertIn("Five Ways We Moved Execution Closer to the Model", ladder)
        self.assertTrue(latency.startswith('<svg '))
        self.assertIn("Latency on the Canonical 6 × 7 Scenario", latency)
        self.assertTrue(remotion_data.startswith("export const articleData = "))
        self.assertIn("open_source_execution_block", remotion_data)


if __name__ == "__main__":
    unittest.main()
