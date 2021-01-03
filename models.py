from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class PythonRepo(Base):
    __tablename__ = 'pythonrepo'
    id = Column(Integer, primary_key=True)
    repo_id = Column(String(32))  # TODO: make FK
    files = relationship('PythonFile', back_populates='repo')


class PythonFile(Base):
    __tablename__ = 'pythonfile'
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    python_repo_id = Column(Integer, ForeignKey('pythonrepo.id'))
    repo = relationship('PythonRepo', back_populates="files")
    loc = Column(Integer)
    lloc = Column(Integer)
    sloc = Column(Integer)
    comments = Column(Integer)
    multi = Column(Integer)
    blank = Column(Integer)
    single_comments = Column(Integer)
