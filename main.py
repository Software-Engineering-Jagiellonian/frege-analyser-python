import json

from radon.raw import analyze
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import PythonFile, PythonRepo

LANGUAGE_ID = 8


def analyse(session, repo_id, files):
    agg_stats = {}
    for file in files:
        with open(file, 'r') as f:
            stats = analyze(f.read())
            agg_stats[file] = stats
            print(stats)

    save_stats(session, repo_id, agg_stats)
    send_ack(repo_id)


def save_stats(session, repo_id, agg_stats):
    repo = PythonRepo(repo_id=repo_id)
    session.add(repo)

    for file, stats in agg_stats.items():
        python_file = PythonFile(repo=repo, **stats._asdict())

        session.add(python_file)

    session.commit()


def send_ack(repo_id):
    queue_name = 'gc'
    msg = {
        'repo_id': repo_id,
        'language_id': LANGUAGE_ID,
    }
    send_to_queue(queue_name, msg)


def send_to_queue(queue_name, msg):
    return
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name)
    channel.basic_publish(exchange='',
                          routing_key=queue_name,
                          body=json.dumps(msg))


engine = create_engine('postgresql://user:pass@localhost:5432/sqlalchemy')
session = sessionmaker(bind=engine)()
analyse(session, 'g76sdyuhj', ['main.py'])
