from generator import variant as variant_module
from generator.variant import VariantGenerator


def make_problem(title, tags, difficulty="中等"):
    return {
        "title": title,
        "difficulty": difficulty,
        "tags": tags,
        "description": f"{title} description",
        "examples": [{"input": "input-1", "output": "output-1"}],
        "constraints": ["constraint-1"],
        "hint": "hint-1",
    }


def test_variant_generator_extracts_title_from_llm_text():
    assert VariantGenerator._extract_title("**题目名称：** 子数组计数\n描述") == "子数组计数"
    assert VariantGenerator._extract_title("题目名称: Prefix Sum Practice\n描述") == "Prefix Sum Practice"
    assert VariantGenerator._extract_title("没有标题") == "变式练习"


def test_variant_generator_formats_database_problem_description():
    description = VariantGenerator._format_problem_description(make_problem("两数之和", ["数组"]))

    assert "**两数之和**" in description
    assert "难度：中等" in description
    assert "两数之和 description" in description
    assert "- 输入：`input-1`" in description
    assert "- 输出：`output-1`" in description
    assert "- constraint-1" in description
    assert "**提示：** hint-1" in description


def test_variant_generator_uses_database_matches_without_llm(monkeypatch):
    problems = [
        make_problem("数组哈希", ["数组", "哈希表"], "简单"),
        make_problem("数组基础", ["数组"], "简单"),
        make_problem("链表题", ["链表"], "简单"),
    ]
    monkeypatch.setattr(variant_module, "load_problems", lambda: problems)

    generator = VariantGenerator(prefer_llm=False)
    variants = generator.generate("原题", tags=["数组", "哈希表"], difficulty="简单", count=2)

    assert [variant["title"] for variant in variants] == ["数组哈希", "数组基础"]
    assert all(variant["source"] == "database" for variant in variants)


def test_variant_generator_uses_fixed_random_sample_for_large_database(monkeypatch):
    problems = [
        make_problem("题目 A", ["数组"]),
        make_problem("题目 B", ["数组"]),
        make_problem("题目 C", ["数组"]),
    ]
    monkeypatch.setattr(variant_module, "load_problems", lambda: problems)
    monkeypatch.setattr(variant_module.random, "sample", lambda seq, count: [seq[2], seq[0]])

    variants = VariantGenerator(prefer_llm=False).generate("原题", tags=["数组"], count=2)

    assert [variant["title"] for variant in variants] == ["题目 C", "题目 A"]
