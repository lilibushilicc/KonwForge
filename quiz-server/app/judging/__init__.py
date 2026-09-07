"""判分包：导入即注册策略（registry 顶部已 import strategies）。"""

from app.judging import registry

__all__ = ["registry"]
