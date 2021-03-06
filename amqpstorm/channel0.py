"""AMQP-Storm Connection.Channel0."""
__author__ = 'eandersson'

import locale
import logging
import platform

from pamqp.heartbeat import Heartbeat
from pamqp import specification as pamqp_spec
from pamqp.specification import Connection as pamqp_connection

from amqpstorm import __version__
from amqpstorm.base import Stateful
from amqpstorm.base import FRAME_MAX
from amqpstorm.exception import AMQPConnectionError


LOGGER = logging.getLogger(__name__)


class Channel0(object):
    """Connection.Channel0."""

    def __init__(self, connection):
        super(Channel0, self).__init__()
        self.is_blocked = False
        self.server_properties = {}
        self.parameters = connection.parameters
        self._connection = connection
        self._heartbeat = self.parameters['heartbeat']

    def on_frame(self, frame_in):
        """Handle frame sent to channel 0.

        :param frame_in: Amqp frame.
        :return:
        """
        LOGGER.debug('Frame Received: %s', frame_in.name)
        if frame_in.name == 'Heartbeat':
            self._write_frame(Heartbeat())
        elif frame_in.name == 'Connection.Start':
            self.server_properties = frame_in.server_properties
            self._send_start_ok_frame()
        elif frame_in.name == 'Connection.Tune':
            self._send_tune_ok_frame()
            self._send_open_connection()
        elif frame_in.name == 'Connection.OpenOk':
            self._set_connection_state(Stateful.OPEN)
        elif frame_in.name == 'Connection.Close':
            self._close_connection(frame_in)
        elif frame_in.name == 'Connection.Blocked':
            self.is_blocked = True
            LOGGER.warning('Connection was blocked by remote server: %s',
                           frame_in.reason.decode('utf-8'))
        elif frame_in.name == 'Connection.Unblocked':
            self.is_blocked = False
            LOGGER.info('Connection is no longer blocked by remote server.')
        else:
            LOGGER.error('Unhandled Frame: %s -- %s',
                         frame_in.name, dict(frame_in))

    def send_close_connection_frame(self):
        """Send Connection Close frame.

        :return:
        """
        self._write_frame(pamqp_spec.Connection.Close())

    def _close_connection(self, frame_in):
        """Close Connection.

        :param pamqp_spec.Connection.Close frame_in: Amqp frame.
        :return:
        """
        self._set_connection_state(Stateful.CLOSED)
        if frame_in.reply_code != 200:
            message = 'Connection was closed by remote server: %s' \
                      % frame_in.reply_text.decode('utf-8')
            why = AMQPConnectionError(message)
            self._connection.exceptions.append(why)

    def _set_connection_state(self, state):
        """Set Connection state.

        :param state:
        :return:
        """
        self._connection.set_state(state)

    def _write_frame(self, frame_out):
        """Write a pamqp frame from channel0.

        :param frame_out: Amqp frame.
        :return:
        """
        self._connection.write_frame(0, frame_out)

    def _send_start_ok_frame(self):
        """Send Start OK frame.

        :param pamqp_spec.Frame frame_out: Amqp frame.
        :return:
        """
        _locale = locale.getdefaultlocale()[0] or 'en_US'
        frame = pamqp_connection.StartOk(
            client_properties=self._client_properties(),
            response=self._credentials(),
            locale=_locale)
        self._write_frame(frame)

    def _send_tune_ok_frame(self):
        """Send Tune OK frame.

        :return:
        """
        frame = pamqp_connection.TuneOk(channel_max=0,
                                        frame_max=FRAME_MAX,
                                        heartbeat=self._heartbeat)
        self._write_frame(frame)

    def _send_open_connection(self):
        """Send Open Connection frame.

        :return:
        """
        frame = pamqp_connection.Open(
            virtual_host=self.parameters['virtual_host']
        )
        self._write_frame(frame)

    def _credentials(self):
        """AMQP Plain Credentials.

        :rtype: str
        """
        return '\0{0}\0{1}'.format(self.parameters['username'],
                                   self.parameters['password'])

    @staticmethod
    def _client_properties():
        """AMQP Library Properties.

        :rtype: dict
        """
        return {'product': 'AMQP-Storm',
                'platform': 'Python %s' % platform.python_version(),
                'capabilities': {
                    'basic.nack': True,
                    'connection.blocked': True,
                    'publisher_confirms': True,
                    'consumer_cancel_notify': True,
                    'authentication_failure_close': True,
                },
                'information': 'See https://github.com/eandersson/amqp-storm',
                'version': __version__}
