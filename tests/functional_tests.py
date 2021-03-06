__author__ = 'eandersson'

import time
import uuid
import logging

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from amqpstorm import Message
from amqpstorm import Channel
from amqpstorm import Connection
from amqpstorm import UriConnection
from amqpstorm import AMQPMessageError
from amqpstorm import AMQPChannelError

from tests import HOST
from tests import USERNAME
from tests import PASSWORD
from tests import URI


logging.basicConfig(level=logging.DEBUG)


class PublishAndGetMessagesTest(unittest.TestCase):
    def setUp(self):
        self.connection = Connection(HOST, USERNAME, PASSWORD)
        self.channel = self.connection.channel()
        self.channel.queue.declare('test.basic.get')
        self.channel.queue.purge('test.basic.get')

    def test_publish_and_get_five_messages(self):
        # Publish 5 Messages.
        for _ in range(5):
            self.channel.basic.publish(body=str(uuid.uuid4()),
                                       routing_key='test.basic.get')

        # Sleep for 0.5s to make sure RabbitMQ has time to catch up.
        time.sleep(0.5)

        # Get 5 messages.
        for _ in range(5):
            payload = self.channel.basic.get('test.basic.get')
            self.assertIsInstance(payload, dict)

    def tearDown(self):
        self.channel.queue.delete('test.basic.get')
        self.channel.close()
        self.connection.close()


class PublishWithPropertiesAndGetTest(unittest.TestCase):
    def setUp(self):
        self.connection = Connection(HOST, USERNAME, PASSWORD)
        self.channel = self.connection.channel()
        self.channel.queue.declare('test.basic.properties')
        self.channel.queue.purge('test.basic.properties')
        self.channel.confirm_deliveries()

    def test_publish_with_properties_and_get(self):
        message = str(uuid.uuid4())
        properties = {
            'headers': {
                'key': 1234567890,
                'alpha': 'omega'
            }
        }

        self.channel.basic.publish(body=message,
                                   routing_key='test.basic.properties',
                                   properties=properties)

        # Sleep for 0.5s to make sure RabbitMQ has time to catch up.
        time.sleep(0.5)

        # New way
        payload = self.channel.basic.get('test.basic.properties',
                                         to_dict=False)
        self.assertEqual(payload.properties['headers']['key'], 1234567890)
        self.assertEqual(payload.properties['headers']['alpha'], 'omega')

        # Old way
        result = payload.to_dict()
        self.assertEqual(result['properties']['headers'][b'key'], 1234567890)
        self.assertEqual(result['properties']['headers'][b'alpha'], b'omega')

    def tearDown(self):
        self.channel.queue.delete('test.basic.properties')
        self.channel.close()
        self.connection.close()


class PublishAndConsumeMessagesTest(unittest.TestCase):
    def setUp(self):
        self.connection = Connection(HOST, USERNAME, PASSWORD)
        self.channel = self.connection.channel()
        self.channel.queue.declare('test.basic.consume')
        self.channel.queue.purge('test.basic.consume')
        self.channel.confirm_deliveries()

    def test_publish_and_consume_five_messages(self):
        for _ in range(5):
            self.channel.basic.publish(body=str(uuid.uuid4()),
                                       routing_key='test.basic.consume')

        # Sleep for 0.5s to make sure RabbitMQ has time to catch up.
        time.sleep(0.5)

        # Store and inbound messages.
        inbound_messages = []

        def on_message(*args):
            self.assertIsInstance(args[0], (bytes, str))
            self.assertIsInstance(args[1], Channel)
            self.assertIsInstance(args[2], dict)
            self.assertIsInstance(args[3], dict)
            inbound_messages.append(args)

        self.channel.basic.consume(callback=on_message,
                                   queue='test.basic.consume',
                                   no_ack=True)
        self.channel.process_data_events()

        # Make sure all five messages were downloaded.
        self.assertEqual(len(inbound_messages), 5)

    def tearDown(self):
        self.channel.queue.delete('test.basic.consume')
        self.channel.close()
        self.connection.close()


class GeneratorConsumeMessagesTest(unittest.TestCase):
    def setUp(self):
        self.connection = Connection(HOST, USERNAME, PASSWORD)
        self.channel = self.connection.channel()
        self.channel.queue.declare('test.basic.generator')
        self.channel.queue.purge('test.basic.generator')
        self.channel.confirm_deliveries()
        for _ in range(5):
            self.channel.basic.publish(body=str(uuid.uuid4()),
                                       routing_key='test.basic.generator')
        self.channel.basic.consume(queue='test.basic.generator',
                                   no_ack=True)
        # Sleep for 0.5s to make sure RabbitMQ has time to catch up.
        time.sleep(0.5)

    def test_generator_consume(self):
        # Store and inbound messages.
        inbound_messages = []
        for message in \
                self.channel.build_inbound_messages(break_on_empty=True):
            self.assertIsInstance(message, Message)
            inbound_messages.append(message)

        # Make sure all five messages were downloaded.
        self.assertEqual(len(inbound_messages), 5)

    def tearDown(self):
        self.channel.queue.delete('test.basic.generator')
        self.channel.close()
        self.connection.close()


class ConsumeAndRedeliverTest(unittest.TestCase):
    def setUp(self):
        self.connection = Connection(HOST, USERNAME, PASSWORD)
        self.channel = self.connection.channel()
        self.channel.queue.declare('test.consume.redeliver')
        self.channel.queue.purge('test.consume.redeliver')
        self.message = str(uuid.uuid4())
        self.channel.confirm_deliveries()
        self.channel.basic.publish(body=self.message,
                                   routing_key='test.consume.redeliver')

        def on_message(message):
            message.reject()

        self.channel.basic.consume(callback=on_message,
                                   queue='test.consume.redeliver',
                                   no_ack=False)
        self.channel.process_data_events(to_tuple=False)

        # Sleep for 0.5s to make sure RabbitMQ has time to catch up.
        time.sleep(0.5)

    def test_consume_and_redeliver(self):
        # Store and inbound messages.
        inbound_messages = []

        def on_message(message):
            inbound_messages.append(message)
            self.assertEqual(message.body, self.message)
            message.ack()

        self.channel.basic.consume(callback=on_message,
                                   queue='test.consume.redeliver',
                                   no_ack=False)
        self.channel.process_data_events(to_tuple=False)
        self.assertEqual(len(inbound_messages), 1)

    def tearDown(self):
        self.channel.queue.delete('test.consume.redeliver')
        self.channel.close()
        self.connection.close()


class GetAndRedeliverTest(unittest.TestCase):
    def setUp(self):
        self.connection = Connection(HOST, USERNAME, PASSWORD)
        self.channel = self.connection.channel()
        self.channel.queue.declare('test.get.redeliver')
        self.channel.queue.purge('test.get.redeliver')
        self.channel.confirm_deliveries()
        self.message = str(uuid.uuid4())
        self.channel.basic.publish(body=self.message,
                                   routing_key='test.get.redeliver')
        payload = self.channel.basic.get('test.get.redeliver', no_ack=False)
        self.channel.basic.reject(
            delivery_tag=payload['method']['delivery_tag']
        )
        # Sleep for 0.5s to make sure RabbitMQ has time to catch up.
        time.sleep(0.5)

    def test_get_and_redeliver(self):
        payload = self.channel.basic.get('test.get.redeliver', no_ack=False)
        self.assertEqual(payload['body'].decode('utf-8'), self.message)

    def tearDown(self):
        self.channel.queue.delete('test.get.redeliver')
        self.channel.close()
        self.connection.close()


class PublisherConfirmsTest(unittest.TestCase):
    def setUp(self):
        self.connection = Connection(HOST, USERNAME, PASSWORD)
        self.channel = self.connection.channel()
        self.channel.queue.declare('test.basic.confirm')
        self.channel.queue.purge('test.basic.confirm')
        self.channel.confirm_deliveries()

    def test_publish_and_confirm(self):
        self.channel.basic.publish(body=str(uuid.uuid4()),
                                   routing_key='test.basic.confirm')

        # Sleep for 0.5s to make sure RabbitMQ has time to catch up.
        time.sleep(0.5)

        payload = self.channel.queue.declare('test.basic.confirm',
                                             passive=True)
        self.assertEqual(payload['message_count'], 1)

    def tearDown(self):
        self.channel.queue.delete('test.basic.confirm')
        self.channel.close()
        self.connection.close()


class PublisherConfirmFailsTest(unittest.TestCase):
    def setUp(self):
        self.connection = Connection(HOST, USERNAME, PASSWORD)
        self.channel = self.connection.channel()
        self.channel.confirm_deliveries()

    def test_publish_confirm_to_invalid_queue(self):
        self.assertRaises(AMQPMessageError,
                          self.channel.basic.publish,
                          body=str(uuid.uuid4()),
                          exchange='amq.direct',
                          mandatory=True,
                          routing_key='test.basic.confirm.fails')

    def tearDown(self):
        self.channel.close()
        self.connection.close()


class QueueCreateTest(unittest.TestCase):
    def setUp(self):
        self.connection = Connection(HOST, USERNAME, PASSWORD)
        self.channel = self.connection.channel()

    def test_queue_create(self):
        # Create the Queue.
        self.channel.queue.declare('test.queue.create')

        # Confirm that the Queue was declared.
        self.channel.queue.declare('test.queue.create', passive=True)

    def tearDown(self):
        self.channel.queue.delete('test.queue.create')
        self.channel.close()
        self.connection.close()


class QueueDeleteTest(unittest.TestCase):
    def setUp(self):
        self.connection = Connection(HOST, USERNAME, PASSWORD)
        self.channel = self.connection.channel()
        self.channel.queue.declare('test.queue.delete')

    def test_queue_delete(self):
        # Delete the Queue.
        self.channel.queue.delete('test.queue.delete')

        # Confirm that the Queue was deleted.
        self.assertRaises(AMQPChannelError, self.channel.queue.declare,
                          'test.queue.delete', passive=True)

    def tearDown(self):
        self.channel.close()
        self.connection.close()


class ExchangeCreateTest(unittest.TestCase):
    def setUp(self):
        self.connection = Connection(HOST, USERNAME, PASSWORD)
        self.channel = self.connection.channel()

    def test_exchange_create(self):
        # Create the Exchange.
        self.channel.exchange.declare('test.exchange.create')

        # Confirm that the Exchange was declared.
        self.channel.exchange.declare('test.exchange.create', passive=True)

    def tearDown(self):
        self.channel.exchange.delete('test.exchange.create')
        self.channel.close()
        self.connection.close()


class ExchangeDeleteTest(unittest.TestCase):
    def setUp(self):
        self.connection = Connection(HOST, USERNAME, PASSWORD)
        self.channel = self.connection.channel()
        self.channel.exchange.declare('test.exchange.delete')

    def test_exchange_delete(self):
        # Delete the Exchange.
        self.channel.exchange.delete('test.exchange.delete')

        # Confirm that the Exchange was deleted.
        self.assertRaises(AMQPChannelError, self.channel.exchange.declare,
                          'test.exchange.delete', passive=True)

    def tearDown(self):
        self.channel.close()
        self.connection.close()


class UriConnectionTest(unittest.TestCase):
    def test_uri_connection(self):
        self.connection = UriConnection(URI)
        self.channel = self.connection.channel()
        self.assertTrue(self.connection.is_open)
        self.channel.close()
        self.connection.close()
