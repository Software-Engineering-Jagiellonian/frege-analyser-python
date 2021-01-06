from radon.metrics import mi_visit, mi_rank

from analysers.base import BaseAnalyser
from models import PythonFileMIMetrics


class MIAnalyser(BaseAnalyser):
    @classmethod
    def analyse(cls, file_content):
        score = mi_visit(file_content, True)
        rank = mi_rank(score)
        return PythonFileMIMetrics(score=score, rank=rank)
