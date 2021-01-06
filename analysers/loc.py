from radon.raw import analyze

from analysers.base import BaseAnalyser
from models import PythonFileLOCMetrics


class LOCAnalyser(BaseAnalyser):
    @classmethod
    def analyse(cls, file_content):
        stats = analyze(file_content)
        return PythonFileLOCMetrics(**stats._asdict())
