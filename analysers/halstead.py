from radon.metrics import h_visit

from analysers.base import BaseAnalyser
from models import PythonFileHalsteadMetrics


class HalsteadAnalyser(BaseAnalyser):
    @classmethod
    def analyse(cls, file_content):
        stats = h_visit(file_content)
        return PythonFileHalsteadMetrics(**stats.total._asdict())
