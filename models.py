from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, BigInteger, SmallInteger, Boolean
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
    repository_id = Column(String(250), ForeignKey('repository.id'))
    language_id = Column(SmallInteger, ForeignKey('language.id'))
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
    __tablename__ = 'pythonfile'
    id = Column(BigInteger, primary_key=True)
    file_id = Column(BigInteger, ForeignKey('repository_language_file.id'))
    file = relationship('RepositoryLanguageFile', uselist=False, foreign_keys=[file_id])
    loc = Column(Integer)
    lloc = Column(Integer)
    sloc = Column(Integer)
    comments = Column(Integer)
    multi = Column(Integer)
    blank = Column(Integer)
    single_comments = Column(Integer)
