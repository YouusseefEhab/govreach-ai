"""Narrow checks on marketing generation inputs and provider drafts."""

import re
from collections.abc import Iterable, Mapping
from decimal import Decimal
from unicodedata import normalize

from app.providers.text import GenerationError
from app.schemas.generation import TextPackage


_CREDENTIAL = re.compile(
    r"""
    -----BEGIN[ ](?:[A-Z0-9]+[ ])*PRIVATE[ ]KEY(?:[ ]BLOCK)?-----
    | \b(?:AIza[A-Za-z0-9_-]{35}|sk-[A-Za-z0-9_-]{20,}
        |(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}|gh[pousr]_[A-Za-z0-9]{30,})(?![A-Za-z0-9_-])
    | \beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{12,}\b
    | (?i:\bauthorization[ \t]*[:=][ \t]*["']?bearer[ \t]+)[A-Za-z0-9._~+/-]{12,}
    | (?i:\bbearer[ \t]+)(?=[A-Za-z0-9._~+/-]*[0-9._~+/-])[A-Za-z0-9._~+/-]{16,}
    | (?i:\b(?:[a-z0-9]+[_-])*
        (?:api[_ -]?key|client[_ -]?secret|access[_ -]?token|password))
        ["']?[ \t]*[:=][ \t]*["']?(?=[A-Za-z0-9._~+/=!@#-]*[0-9._~+/=!@#-])
        [A-Za-z0-9._~+/=!@#-]{12,}
    """,
    re.VERBOSE,
)

_NUMBERS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٫٬٪", "01234567890123456789.,%")
_AMOUNT = r"(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?"
_CURRENCY = r"(?:EGP|USD|US\$|\$|جنيه(?:ا|ًا)?(?:\s+مصري)?|ج\.\s*م\.?|دولار(?:ا|ًا)?(?:\s+أمريكي)?)"
_MONEY = re.compile(
    rf"(?<![\w.,])(?:(?P<leading>{_CURRENCY})\s*(?P<after>{_AMOUNT})(?!\w|[.,]\d)"
    rf"|(?P<before>{_AMOUNT})\s*(?P<trailing>{_CURRENCY})(?!\w))",
    re.IGNORECASE,
)
_PROMOTION_WORDS = r"(?:off|discount|save|savings|cashback|خصم|تخفيض|وفر|توفير)"
_PROMOTION_PREFIX = re.compile(rf"\b{_PROMOTION_WORDS}\s+(?:(?:of|up to|حتى|لحد)\s+)?$", re.IGNORECASE)
_PROMOTION_SUFFIX = re.compile(rf"^\s*{_PROMOTION_WORDS}\b", re.IGNORECASE)
_PROMOTIONS = re.compile(
    rf"\b{_PROMOTION_WORDS}\s+(?:(?:of|up to|حتى|لحد)\s+)?(?P<after>{_AMOUNT})\s*%"
    rf"|(?<![\w.,])(?P<before>{_AMOUNT})\s*%\s*{_PROMOTION_WORDS}\b",
    re.IGNORECASE,
)
_GUARANTEES = re.compile(
    r"\b(?:(?P<refund>money[- ]back guarantee|ضمان استرداد (?:الأموال|الفلوس))"
    r"|(?P<lifetime>lifetime (?:guarantee|warranty)|ضمان مدى الحياة)"
    r"|(?P<satisfaction>satisfaction guaranteed|guaranteed satisfaction|رضاك مضمون)"
    r"|(?P<results>guaranteed results?|results? guaranteed|نتائج مضمونة)"
    r"|(?P<delivery>guaranteed delivery|delivery guaranteed|توصيل مضمون))\b",
    re.IGNORECASE,
)
_CLAUSE_BOUNDARY = re.compile(r"[\n;؛!?؟]+|(?<=\.)\s+")
_NEGATED = re.compile(r"\b(?:no|not|without|never|بدون|بلا|من غير)\s+(?:(?:an?|the)\s+)?$", re.IGNORECASE)
_NONFACTUAL_REFERENCE = re.compile(
    r"\b(?:budget|invent|make up|fabricate|pretend|ignore|claim that|ميزانية|اختلق|اخترع|افترض|تجاهل)\b",
    re.IGNORECASE,
)


def validate_marketing_inputs(inputs: Mapping[str, object]) -> None:
    for field, value in inputs.items():
        values = value if isinstance(value, list) else [value]
        if any(isinstance(item, str) and _CREDENTIAL.search(item) for item in values):
            raise GenerationError(422, f"Remove credential-like text from {field} before generating a draft.")


def _claims(text: str, *, reference: bool = False) -> set[tuple[str, Decimal | str]]:
    claims = set()
    normalized = normalize("NFKC", text).translate(_NUMBERS)
    for clause in _CLAUSE_BOUNDARY.split(normalized):
        if reference and _NONFACTUAL_REFERENCE.search(clause):
            continue
        for match in _MONEY.finditer(clause):
            if _NEGATED.search(clause[:match.start()]):
                continue
            currency = match["leading"] or match["trailing"]
            code = "USD" if currency.upper() in {"USD", "US$", "$"} or currency.startswith("دولار") else "EGP"
            amount = match["after"] or match["before"]
            promotion = (
                _PROMOTION_PREFIX.search(clause[:match.start()])
                or _PROMOTION_SUFFIX.match(clause[match.end():])
            )
            claims.add((f"discount_{code}" if promotion else code, Decimal(amount.replace(",", ""))))
        for match in _PROMOTIONS.finditer(clause):
            if not _NEGATED.search(clause[:match.start()]):
                amount = match["after"] or match["before"]
                claims.add(("promotion", Decimal(amount.replace(",", ""))))
        for match in _GUARANTEES.finditer(clause):
            if not _NEGATED.search(clause[:match.start()]):
                claims.add(("guarantee", match.lastgroup))
    return claims


def validate_marketing_drafts(packages: Iterable[TextPackage], offer_summary: str | None) -> None:
    supported = _claims(offer_summary or "", reference=True)
    if any(_claims(text) - supported for package in packages for text in package.model_dump().values()):
        raise GenerationError(
            502,
            "Generated draft contains an unsupported monetary amount, percentage promotion, or guarantee. "
            "Check the campaign offer summary and regenerate.",
        )
