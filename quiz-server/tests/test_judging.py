"""判分单测，覆盖 DESIGN M3 边界：全角、大小写、标点、数值容差、漏选、乱序填空。"""

from app.judging.normalizer import cosine_tfidf, normalize, numeric_equal
from app.judging.strategies.coding import CodingStrategy
from app.judging.strategies.essay import EssayStrategy
from app.judging.strategies.fill_blank import FillBlankStrategy
from app.judging.strategies.multiple_choice import MultipleChoiceStrategy
from app.judging.strategies.single_choice import SingleChoiceStrategy


# --------------------------------------------------------------------------- #
# 归一化
# --------------------------------------------------------------------------- #


class TestNormalizer:
    def test_fullwidth_to_halfwidth(self):
        # ＴＣＰ（全角） → tcp
        assert normalize("ＴＣＰ") == "tcp"

    def test_casefold(self):
        assert normalize("TCP") == normalize("tcp") == "tcp"

    def case_sensitive(self):
        assert normalize("TCP", case_sensitive=True) == "TCP"
        assert normalize("tcp", case_sensitive=True) == "tcp"

    def test_strip_punct(self):
        assert normalize("Hello, World！") == "helloworld"

    def test_nbsp(self):
        assert normalize("a\u00a0b") == "ab"

    def test_ignore_punct_false_keeps_spaces(self):
        assert normalize("a, b", ignore_punct=False) == "a, b"  # 逗号不是空白，保留
        assert normalize("a  b", ignore_punct=False) == "a b"

    def test_aliases(self):
        assert normalize("TCP/IP 协议", aliases={"TCP/IP": "tcpip"}) == "tcpip协议"

    def test_numeric_equal(self):
        assert numeric_equal("1.0", "1.0001", 0.001) is True
        assert numeric_equal("1.0", "1.5", 0.001) is False
        assert numeric_equal("abc", "1") is False

    def test_cosine_identical_is_one(self):
        assert cosine_tfidf("三次握手建立连接", "三次握手建立连接") == 1.0

    def test_cosine_disjoint_is_zero(self):
        assert cosine_tfidf("苹果", "香蕉") == 0.0

    def test_cosine_partial(self):
        s = cosine_tfidf("三次握手", "三次握手建立连接")
        assert 0 < s < 1


# --------------------------------------------------------------------------- #
# 单选
# --------------------------------------------------------------------------- #


class TestSingleChoice:
    strat = SingleChoiceStrategy()

    def test_correct(self):
        r = self.strat.judge(
            payload={"options": [{"key": "A"}, {"key": "B"}]},
            answer={"correct": "B"},
            config={},
            response={"choice": "B"},
            max_score=2.0,
        )
        assert r.is_correct is True and r.score == 2.0

    def test_wrong(self):
        r = self.strat.judge(
            payload={}, answer={"correct": "B"}, config={}, response={"choice": "A"}, max_score=1.0
        )
        assert r.is_correct is False and r.score == 0.0

    def test_casefold_and_fullwidth(self):
        # 全角 Ｂ → b == b
        r = self.strat.judge(
            payload={}, answer={"correct": "b"}, config={}, response={"choice": "Ｂ"}, max_score=1.0
        )
        assert r.is_correct is True


# --------------------------------------------------------------------------- #
# 多选
# --------------------------------------------------------------------------- #


class TestMultipleChoice:
    strat = MultipleChoiceStrategy()

    def test_all_correct(self):
        r = self.strat.judge(
            payload={},
            answer={"correct": ["A", "C"]},
            config={},
            response={"choices": ["C", "A"]},  # 顺序无关
            max_score=1.0,
        )
        assert r.is_correct is True and r.score == 1.0

    def test_missing_only_partial(self):
        # 漏一个 → 按比例 0.5 * (1/2) = 0.25
        r = self.strat.judge(
            payload={},
            answer={"correct": ["A", "C"]},
            config={"partial_ratio": 0.5},
            response={"choices": ["A"]},
            max_score=1.0,
        )
        assert r.is_correct is False and r.score == 0.25

    def test_extra_means_zero(self):
        # 错选一个额外项 → 0 分
        r = self.strat.judge(
            payload={},
            answer={"correct": ["A"]},
            config={},
            response={"choices": ["A", "B"]},
            max_score=1.0,
        )
        assert r.score == 0.0

    def test_all_or_nothing(self):
        r = self.strat.judge(
            payload={},
            answer={"correct": ["A", "B"]},
            config={"partial_credit": False},
            response={"choices": ["A"]},
            max_score=1.0,
        )
        assert r.score == 0.0 and r.detail["rule"] == "all_or_nothing"


# --------------------------------------------------------------------------- #
# 填空（含乱序匹配）
# --------------------------------------------------------------------------- #


class TestFillBlank:
    strat = FillBlankStrategy()

    def _spec(self, accepted, **kw):
        base = {"id": 1, "accepted": accepted, "regex": None, "case_sensitive": False,
                "numeric_tolerance": 0.001}
        base.update(kw)
        return base

    def test_ordered_all_correct(self):
        r = self.strat.judge(
            payload={},
            answer={"blanks": [self._spec(["TCP"]), self._spec(["三次握手"], id=2)]},
            config={},
            response={"blanks": {1: "tcp", 2: "三次握手"}},
            max_score=2.0,
        )
        assert r.is_correct is True and r.score == 2.0

    def test_ordered_one_wrong(self):
        r = self.strat.judge(
            payload={},
            answer={"blanks": [self._spec(["TCP"]), self._spec(["UDP"], id=2)]},
            config={},
            response={"blanks": {1: "tcp", 2: "TCP"}},  # 空2 错
            max_score=2.0,
        )
        assert r.is_correct is False and r.score == 1.0

    def test_unordered_matching(self):
        # 空数 2，用户把空1的答案填到空2、空2的填到空1 → 乱序匹配应判全对
        r = self.strat.judge(
            payload={},
            answer={"blanks": [self._spec(["TCP"]), self._spec(["UDP"], id=2)]},
            config={"ordered": False},
            response={"blanks": {1: "udp", 2: "tcp"}},
            max_score=2.0,
        )
        assert r.is_correct is True and r.score == 2.0, r.detail

    def test_numeric_tolerance(self):
        r = self.strat.judge(
            payload={},
            answer={"blanks": [self._spec(["3.14"], numeric_tolerance=0.01)]},
            config={},
            response={"blanks": {1: "3.1416"}},
            max_score=1.0,
        )
        assert r.is_correct is True

    def test_regex(self):
        r = self.strat.judge(
            payload={},
            answer={"blanks": [self._spec([], regex=r"\d{4}")]},
            config={},
            response={"blanks": {1: "2026"}},
            max_score=1.0,
        )
        assert r.is_correct is True
        r2 = self.strat.judge(
            payload={},
            answer={"blanks": [self._spec([], regex=r"\d{4}")]},
            config={},
            response={"blanks": {1: "abc"}},
            max_score=1.0,
        )
        assert r2.is_correct is False


# --------------------------------------------------------------------------- #
# 代码（沙箱关闭 → 降级自评）
# --------------------------------------------------------------------------- #


class TestCoding:
    strat = CodingStrategy()

    def test_sandbox_off_manual(self):
        r = self.strat.judge(
            payload={"language": "python", "testcases": []},
            answer={"reference_code": "print(1)"},
            config={},
            response={"code": "print(1)"},
            max_score=1.0,
        )
        assert r.need_manual is True and r.is_correct is None and r.score == 0.0
        assert r.detail["mode"] == "manual"


# --------------------------------------------------------------------------- #
# 简答（参考分 + 关键词覆盖）
# --------------------------------------------------------------------------- #


class TestEssay:
    strat = EssayStrategy()

    def test_reference_score_and_manual(self):
        r = self.strat.judge(
            payload={},
            answer={"reference": "三次握手用于建立 TCP 连接", "keywords": [{"word": "TCP", "weight": 2},
                                                            {"word": "建立连接", "weight": 1}]},
            config={},
            response={"text": "TCP 通过三次握手建立连接"},
            max_score=10.0,
        )
        assert r.need_manual is True and r.is_correct is None
        assert 0 < r.score <= 10.0
        assert r.detail["coverage"] == 1.0  # 两个关键词都命中

    def test_keywords_as_strings(self):
        # 兼容 keywords 为字符串数组的简化形态
        r = self.strat.judge(
            payload={},
            answer={"reference_answer": "TCP 三次握手", "keywords": ["tcp", "握手"]},
            config={},
            response={"text": "tcp 三次握手建立连接"},
            max_score=1.0,
        )
        assert r.detail["coverage"] == 1.0

    def test_no_keywords_coverage_zero(self):
        r = self.strat.judge(
            payload={},
            answer={"reference": "某参考答案", "keywords": []},
            config={},
            response={"text": "完全无关的内容"},
            max_score=1.0,
        )
        assert r.detail["coverage"] == 0.0
        # 仍有相似度信号
        assert 0.0 <= r.detail["similarity"] <= 1.0
