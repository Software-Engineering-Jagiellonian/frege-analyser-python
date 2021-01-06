from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, BigInteger, SmallInteger, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Repository(Base):
    __tablename__ = 'repositories'
    id = Column(String(250), primary_key=True)
    git_url = Column(String(250))
    repo_url = Column(String(250))
    crawl_time = Column(DateTime)
    download_time = Column(DateTime)
    commit_hash = Column(String(40))


class Language(Base):
    __tablename__ = 'languages'
    id = Column(SmallInteger, primary_key=True)
    name = Column(String(100))


class RepositoryLanguage(Base):
    __tablename__ = 'repository_language'
    id = Column(BigInteger, primary_key=True)
    repository_id = Column(String(250), ForeignKey('repositories.id'))
    language_id = Column(SmallInteger, ForeignKey('languages.id'))
    present = Column(Boolean)
    analyzed = Column(Boolean)
    files = relationship('RepositoryLanguageFile', back_populates='repository_language')


class RepositoryLanguageFile(Base):
    __tablename__ = 'repository_language_file'
    id = Column(BigInteger, primary_key=True)
    repository_language_id = Column(BigInteger, ForeignKey('repository_language.id'))
    repository_language = relationship('RepositoryLanguage', back_populates="files")
    file_path = Column(String(500))


class PythonFile(Base):
    __tablename__ = 'python_file'
    id = Column(BigInteger, primary_key=True)
    file_id = Column(BigInteger, ForeignKey('repository_language_file.id'))
    file = relationship('RepositoryLanguageFile', uselist=False, foreign_keys=[file_id])
    loc_metrics = relationship('PythonFileLOCMetrics',  back_populates="python_file")
    halstead_metrics = relationship('PythonFileHalsteadMetrics',  back_populates="python_file")


class PythonFileLOCMetrics(Base):
    __tablename__ = 'python_file_loc_metrics'
    id = Column(BigInteger, primary_key=True)
    python_file_id = Column(BigInteger, ForeignKey('python_file.id'))
    python_file = relationship('PythonFile', uselist=False, foreign_keys=[python_file_id])
    loc = Column(Integer)
    lloc = Column(Integer)
    sloc = Column(Integer)
    comments = Column(Integer)
    multi = Column(Integer)
    blank = Column(Integer)
    single_comments = Column(Integer)


class PythonFileHalsteadMetrics(Base):
    __tablename__ = 'python_file_halstead_metrics'
    id = Column(BigInteger, primary_key=True)
    python_file_id = Column(BigInteger, ForeignKey('python_file.id'))
    python_file = relationship('PythonFile', uselist=False, foreign_keys=[python_file_id])
    h1 = Column(Integer)
    h2 = Column(Integer)
    N1 = Column(Integer)
    N2 = Column(Integer)
    vocabulary = Column(Integer)
    length = Column(Integer)
    calculated_length = Column(Float)
    volume = Column(Float)
    difficulty = Column(Float)
    effort = Column(Float)
    time = Column(Float)
    bugs = Column(Float)
