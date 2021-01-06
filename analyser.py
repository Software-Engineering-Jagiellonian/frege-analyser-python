import json
from time import sleep

import pika
from sqlalchemy.orm import sessionmaker

import config
from analysers.halstead import HalsteadAnalyser
from analysers.loc import LOCAnalyser
from logger import logger
from models import RepositoryLanguage, PythonFile


class Analyser:
    LANGUAGE_ID = 8

    analysers = [
        LOCAnalyser,
        HalsteadAnalyser,
    ]

    def __init__(self, uid, db_conn, repo_id):
        self.uid = uid
        self.db_conn = db_conn
        self.repo_id = repo_id
        self.repo = None
        self.out_channel = None
        self.session = None

    def analyse(self):
        try:
            logger.info(f'[{self.uid}] Started processing of the message')

            self.session = sessionmaker(bind=self.db_conn)()
            self.repo = self.session.query(RepositoryLanguage).filter(
                RepositoryLanguage.repository_id == self.repo_id,
                RepositoryLanguage.language_id == self.LANGUAGE_ID,
                RepositoryLanguage.present == True
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
                    stats = self.run_analysers(f.read())
                    agg_stats[file.id] = stats

            self.save_stats( agg_stats)
            self.send_ack()
            logger.info(f'[{self.uid}] Message processed successfully')
        except Exception as e:
            logger.exception(f'[{self.uid}] Exception occurred during processing of the message: {e}')

    def save_stats(self, agg_stats):
        for file, stats in agg_stats.items():
            python_file = PythonFile(file_id=file)
            for metric in stats:
                metric.python_file = python_file
                self.session.add(metric)

            self.session.add(python_file)

        self.repo.analyzed = True
        self.session.add(self.repo)
        self.session.commit()

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

    def run_analysers(self, file_content):
        stats = []
        for analyser in self.analysers:
            stats.append(analyser.analyse(file_content))

        return stats
