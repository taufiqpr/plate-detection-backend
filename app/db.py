from typing import Tuple
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


def init_db(user: str, password: str, host: str, port: str, name: str):
    database_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
    engine = create_engine(database_url)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Session = scoped_session(session_factory)
    return engine, Session


def get_scoped_session(app):
    return app.extensions["Session"]


