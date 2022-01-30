import logging
import os
from urllib.parse import quote_plus

import pika
from pymongo import MongoClient

from .reddit import CustomRedditClient

logging.basicConfig(format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID', '')
REDDIT_SECRET = os.getenv('REDDIT_SECRET', '')
REDDIT_USER = os.getenv('REDDIT_USER', '')
REDDIT_PASSWORD = os.getenv('REDDIT_PASSWORD', "")
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', "localhost")
RABBITMQ_PORT = os.environ.get('RABBITMQ_PORT', "5672")
MONGODB_HOST = os.environ.get('MONGODB_HOST', "localhost")
MONGODB_PORT = os.environ.get('MONGODB_PORT', "30017")


class Consumer():
    def __init__(self, queue_name="queue_id_t3"):
        self.queue_name = queue_name
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        self.logger = logger
        uri = "mongodb://%s:%s@%s" % (
            quote_plus("admin"),
            quote_plus("admin123$"),
            "%s:%s" % (MONGODB_HOST, MONGODB_PORT))
        print(uri)
        self.mongo_client = MongoClient(uri)
        self.db = self.mongo_client["reddit"]
        self.collection = self.db["t3"]
        credentials = pika.PlainCredentials('admin', 'admin')
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST,
                                      port=int(RABBITMQ_PORT),
                                      credentials=credentials))
        self.channel = self.connection.channel()
        self.channel.basic_qos(prefetch_count=100)
        self.channel.basic_consume(queue=self.queue_name,
                                   on_message_callback=self.callback,
                                   auto_ack=False)
        self.reddit_client = CustomRedditClient(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_SECRET,
            password=REDDIT_PASSWORD,
            username=REDDIT_USER,
            user_agent="linux:reddit-history:0.0.1 (by /u/aDrz)"
        )
        self.reddit_client.random_subreddit()

        self.data = []
        self.tags = []

    def start(self):
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.channel.stop_consuming()

    def callback(self, ch, method, properties, body):
        body_str = body.decode()
        delivery_tag = method.delivery_tag
        self.tags.append(delivery_tag)
        # self.channel.basic_ack(delivery_tag=delivery_tag)
        self.data.append(body_str)
        if len(self.data) >= 100:
            self.logger.info(f"[x] got {len(self.data)} records {self.data[0]}")
            res = [x for x in self.reddit_client.info(self.data)]
            self.logger.info("[x] got %d valid records" % len(res))
            if len(res):
                self.collection.insert_many(res)
            for tag in self.tags:
                self.channel.basic_ack(delivery_tag=tag)
            self.tags = []
            self.data = []
