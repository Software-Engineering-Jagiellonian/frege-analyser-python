import json
from time import sleep

import pika
from radon.raw import analyze
from sqlalchemy.orm import sessionmaker

import config
from logger import logger
from models import RepositoryLanguage, PythonFile


class Analyser:
    LANGUAGE_ID = 8

    def __init__(self, uid, db_conn, repo_id):
        self.uid = uid
        self.db_conn = db_conn
        self.repo_id = repo_id
        self.repo = None
        self.out_channel = None

    def analyse(self):
        try:
            logger.info(f'[{self.uid}] Started processing of the message')

            session = sessionmaker(bind=self.db_conn)()
            self.repo = session.query(RepositoryLanguage).filter(
                RepositoryLanguage.repository_id == self.repo_id,
                RepositoryLanguage.language_id == self.LANGUAGE_ID
            ).first()
            if not self.repo:
                raise Exception('No repository entity found')

            self.out_channel = pika.BlockingConnection(
                pika.ConnectionParameters(host=config.RABBITMQ_HOST, port=config.RABBITMQ_PORT)
            ).channel()
            self.out_channel.confirm_delivery()
            self.out_channel.queue_declare(queue=config.OUT_QUEUE_NAME, durable=True)

            agg_stats = {}
            for file in self.repo.files:
                with open(file.file_path, 'r') as f:
                    stats = analyze(f.read())
                    agg_stats[file.id] = stats
                    print(stats)

            self.save_stats(session, agg_stats)
            self.send_ack()
            logger.info(f'[{self.uid}] Message processed successfully')
        except Exception as e:
            logger.exception(f'[{self.uid}] Exception occurred during processing of the message: {e}')

    def save_stats(self, session, agg_stats):
        for file, stats in agg_stats.items():
            python_file = PythonFile(file_id=file, **stats._asdict())

            session.add(python_file)

        session.commit()

    def send_ack(self):
        msg = {
            'repo_id': self.repo_id,
            'language_id': self.LANGUAGE_ID,
        }
        self.send_to_queue(msg)

    def send_to_queue(self, msg):
        queue_name = config.OUT_QUEUE_NAME
        while True:
            try:
                self.out_channel.basic_publish(
                    exchange='',
                    routing_key=queue_name,
                    properties=pika.BasicProperties(delivery_mode=2),
                    body=json.dumps(msg).encode('utf-8')
                )
                break
            except pika.exceptions.NackError:
                logger.warning(f'[{self.uid}] Message to the {queue_name} queue was rejected by RabbitMQ')
                sleep(config.PUBLISH_DELAY)

        logger.info(f'[{self.uid}] Message to the {queue_name} queue was received by RabbitMQ')
