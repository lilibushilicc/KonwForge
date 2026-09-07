"""判分层入口：导入本包即注册全部内置策略。"""

from app.judging.registry import register
from app.judging.strategies.coding import CodingStrategy
from app.judging.strategies.essay import EssayStrategy
from app.judging.strategies.fill_blank import FillBlankStrategy
from app.judging.strategies.multiple_choice import MultipleChoiceStrategy
from app.judging.strategies.single_choice import SingleChoiceStrategy

register(SingleChoiceStrategy())
register(MultipleChoiceStrategy())
register(FillBlankStrategy())
register(CodingStrategy())
register(EssayStrategy())

__all__ = [
    "CodingStrategy",
    "EssayStrategy",
    "FillBlankStrategy",
    "MultipleChoiceStrategy",
    "SingleChoiceStrategy",
]
