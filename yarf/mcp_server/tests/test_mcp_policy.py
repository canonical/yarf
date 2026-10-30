import pytest

from yarf.errors.yarf_errors import KeywordNotAllowedError
from yarf.mcp_server.policy import KeywordPolicy, validate_argument


class TestValidateArgument:
    @pytest.mark.parametrize(
        "text",
        [
            "plain text",
            "",
            "${NAME}",
            "@{list}",
            "&{dict}",
            "${OUTPUT DIR}/x.png",
            "item ${list}[0] and ${list}[1:2]",
            "\\${{not_a_variable}}",
            "4+2\\=",
        ],
    )
    def test_allowed(self, text: str) -> None:
        validate_argument(text)

    @pytest.mark.parametrize(
        "text",
        [
            "${{__import__('os').system('id')}}",
            "${CURDIR.upper()}",
            "${3+4}",
            "%{HOME}",
            "${a${b}}",
            "${list}[${{1+1}}]",
            "${unclosed",
        ],
    )
    def test_blocked(self, text: str) -> None:
        with pytest.raises(KeywordNotAllowedError):
            validate_argument(text)


class TestKeywordPolicy:
    policy = KeywordPolicy(frozenset({"Hid", "kvm"}))

    @pytest.mark.parametrize(
        "owner, keyword, allowed",
        [
            ("Hid", "Type String", True),
            ("kvm", "Click ${button} Button", True),
            ("BuiltIn", "Sleep", True),
            ("BuiltIn", "sleep", True),
            ("BuiltIn", "Should_Be_Equal", True),
            ("BuiltIn", "Evaluate", False),
            ("BuiltIn", "Run Keyword", False),
            ("BuiltIn", "Import Library", False),
            ("Process", "Run Process", False),
            ("OperatingSystem", "Run", False),
            (None, "No Such Keyword", False),
        ],
    )
    def test_is_allowed(
        self, owner: str | None, keyword: str, allowed: bool
    ) -> None:
        assert self.policy.is_allowed(owner, keyword) is allowed

    def test_check_allowed(self) -> None:
        self.policy.check("Hid", "Type String", ["hello ${NAME}"])

    def test_check_blocked_keyword(self) -> None:
        with pytest.raises(KeywordNotAllowedError, match="Evaluate"):
            self.policy.check("BuiltIn", "Evaluate", ["1+1"])

    @pytest.mark.parametrize("position", [0, 1])
    def test_check_blocked_argument(self, position: int) -> None:
        texts = ["Type String", "${{evil}}"]
        with pytest.raises(KeywordNotAllowedError, match="not allowed"):
            self.policy.check("Hid", texts[position], [texts[1 - position]])
