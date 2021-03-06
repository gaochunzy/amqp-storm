__author__ = 'eandersson'

import sys
import logging

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from amqpstorm import compatibility


logging.basicConfig(level=logging.DEBUG)


class CompatibilityTests(unittest.TestCase):
    def test_basic_integer(self):
        x = 0
        self.assertTrue(compatibility.is_integer(x))

    def test_not_integer(self):
        x = ''
        self.assertFalse(compatibility.is_integer(x))

    @unittest.skipIf(sys.version_info[0] == 3, 'No long obj in Python 3')
    def test_long_integer(self):
        x = long(1)
        self.assertTrue(compatibility.is_integer(x))

    def test_normal_string(self):
        x = ''
        self.assertTrue(compatibility.is_string(x))

    def test_byte_string(self):
        x = b''
        self.assertTrue(compatibility.is_string(x))

    @unittest.skipIf(sys.version_info[0] == 3, 'No unicode obj in Python 3')
    def test_unicode_string(self):
        x = unicode('')
        self.assertTrue(compatibility.is_string(x))

    def test_is_not_string(self):
        x = 0
        self.assertFalse(compatibility.is_string(x))

    @unittest.skipIf(sys.version_info[0] == 3, 'No unicode obj in Python 3')
    def test_is_unicode(self):
        x = unicode('')
        self.assertTrue(compatibility.is_unicode(x))

    def test_is_not_unicode(self):
        x = ''
        self.assertFalse(compatibility.is_unicode(x))

    @unittest.skipIf(sys.version_info[0] == 3, 'No unicode obj in Python 3')
    def test_py2_try_utf8_decode(self):
        x = unicode('hello world')
        self.assertEqual(str(x), compatibility.try_utf8_decode(x))

    @unittest.skipIf(sys.version_info[0] == 2, 'No bytes decoding in Python 2')
    def test_py3_try_utf8_decode(self):
        x = bytes('hello world', 'utf-8')
        self.assertEqual(x.decode('utf-8'), compatibility.try_utf8_decode(x))

    def test_try_utf8_decode_on_integer(self):
        x = 5
        self.assertEqual(x, compatibility.try_utf8_decode(x))

    def test_try_utf8_decode_on_dict(self):
        x = dict(hello='world')
        self.assertEqual(x, compatibility.try_utf8_decode(x))