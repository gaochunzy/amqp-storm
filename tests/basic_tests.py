__author__ = 'eandersson'

import uuid
import logging

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from pamqp.body import ContentBody
from pamqp.header import ContentHeader
from pamqp.specification import Basic as spec_basic

from amqpstorm import exception
from amqpstorm.channel import Basic
from amqpstorm.channel import Channel

from tests.utility import FakeConnection


logging.basicConfig(level=logging.DEBUG)


class BasicBasicTests(unittest.TestCase):
    def test_basic_publish(self):
        message = str(uuid.uuid4())
        exchange = 'test'
        routing_key = 'hello'
        properties = {'headers': {
            'key': 'value'
        }}

        connection = FakeConnection()
        channel = Channel(9, connection, 0.0001)
        channel.set_state(Channel.OPEN)
        basic = Basic(channel)
        basic.publish(body=message,
                      routing_key=routing_key,
                      exchange=exchange,
                      properties=properties,
                      mandatory=True,
                      immediate=True)

        channel_id, payload = connection.frames_out.pop()
        basic_publish, content_header, content_body = payload

        # Verify Channel ID
        self.assertEqual(channel_id, 9)

        # Verify Classes
        self.assertIsInstance(basic_publish, spec_basic.Publish)
        self.assertIsInstance(content_header, ContentHeader)
        self.assertIsInstance(content_body, ContentBody)

        # Verify Content
        self.assertEqual(message, content_body.value.decode('utf-8'))
        self.assertEqual(exchange, basic_publish.exchange)
        self.assertEqual(routing_key, basic_publish.routing_key)
        self.assertTrue(basic_publish.immediate)
        self.assertTrue(basic_publish.mandatory)
        self.assertIn('key', dict(content_header.properties)['headers'])

    def test_basic_return(self):
        basic = Basic(None)

        message = b'Hello World!'
        results = []
        for frame in basic._create_content_body(message):
            results.append(frame)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].value, message)

    def test_basic_return_long_string(self):
        basic = Basic(None)

        message = b'Hello World!' * 80960
        results = []
        for frame in basic._create_content_body(message):
            results.append(frame)

        self.assertEqual(len(results), 8)

        # Rebuild the string
        result_body = b''
        for frame in results:
            result_body += frame.value

        # Confirm that it matches the original string.
        self.assertEqual(result_body, message)

    def test_get_content_body(self):
        message = b'Hello World!'
        body = ContentBody(value=message)
        channel = Channel(0, FakeConnection(), 360)
        channel.set_state(Channel.OPEN)
        basic = Basic(channel)
        uuid = channel.rpc.register_request([body.name])
        channel.rpc.on_frame(body)
        self.assertEqual(basic._get_content_body(uuid, len(message)),
                         message)

    def test_get_content_body_timeout_error(self):
        message = b'Hello World!'
        body = ContentBody(value=message)
        channel = Channel(0, FakeConnection(), 0.0001)
        channel.set_state(Channel.OPEN)
        basic = Basic(channel)
        uuid = channel.rpc.register_request([body.name])
        self.assertRaises(exception.AMQPChannelError, basic._get_content_body,
                          uuid, len(message))

