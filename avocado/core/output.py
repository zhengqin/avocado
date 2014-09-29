# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

"""
Manages output and logging in avocado applications.
"""
import logging
import os
import sys

from avocado.utils import process


class ProgressStreamHandler(logging.StreamHandler):

    """
    Handler class that allows users to skip new lines on each emission.
    """

    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            skip_newline = False
            if hasattr(record, 'skip_newline'):
                skip_newline = record.skip_newline
            stream.write(msg)
            if not skip_newline:
                stream.write('\n')
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


class PagerNotFoundError(Exception):
    pass


class Paginator(object):

    """
    Paginator that uses less to display contents on the terminal.

    Contains cleanup handling for when user presses 'q' (to quit less).
    """

    def __init__(self):
        try:
            paginator = "%s -FRSX" % process.find_command('less')
        except process.CmdNotFoundError:
            paginator = None

        paginator = os.environ.get('PAGER', paginator)
        if paginator is None:
            raise PagerNotFoundError("Could not find a paginator program "
                                     "('less' not found and env "
                                     "variable $PAGER not set)")

        self.pipe = os.popen(paginator, 'w')

    def __del__(self):
        try:
            self.pipe.close()
        except IOError:
            pass

    def write(self, msg):
        try:
            self.pipe.write(msg)
        except IOError:
            pass


def get_paginator():
    """
    Get a paginator. If we can't do that, return stdout.

    The paginator is whatever the user sets as $PAGER, or 'less'. It is a useful
    feature inspired in programs such as git, since it lets you scroll up and down
    large buffers of text, increasing the program's usability.
    """
    try:
        return Paginator()
    except PagerNotFoundError:
        return sys.stdout


def add_console_handler(logger):
    """
    Add a console handler to a logger.

    :param logger: `logging.Logger` instance.
    """
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter(fmt='%(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


class TermSupport(object):

    COLOR_BLUE = '\033[94m'
    COLOR_GREEN = '\033[92m'
    COLOR_YELLOW = '\033[93m'
    COLOR_RED = '\033[91m'

    CONTROL_END = '\033[0m'

    MOVE_BACK = '\033[1D'
    MOVE_FORWARD = '\033[1C'

    """
    Class to help applications to colorize their outputs for terminals.

    This will probe the current terminal and colorize ouput only if the
    stdout is in a tty or the terminal type is recognized.
    """

    allowed_terms = ['linux', 'xterm', 'xterm-256color', 'vt100', 'screen',
                     'screen-256color']

    def __init__(self):
        self.HEADER = self.COLOR_BLUE
        self.PASS = self.COLOR_GREEN
        self.SKIP = self.COLOR_YELLOW
        self.FAIL = self.COLOR_RED
        self.ERROR = self.COLOR_RED
        self.NOT_FOUND = self.COLOR_YELLOW
        self.WARN = self.COLOR_YELLOW
        self.PARTIAL = self.COLOR_YELLOW
        self.ENDC = self.CONTROL_END
        term = os.environ.get("TERM")
        if (not os.isatty(1)) or (term not in self.allowed_terms):
            self.disable()

    def disable(self):
        """
        Disable colors from the strings output by this class.
        """
        self.HEADER = ''
        self.PASS = ''
        self.SKIP = ''
        self.FAIL = ''
        self.ERROR = ''
        self.NOT_FOUND = ''
        self.WARN = ''
        self.PARTIAL = ''
        self.ENDC = ''

    def header_str(self, msg):
        """
        Print a header string (blue colored).

        If the output does not support colors, just return the original string.
        """
        return self.HEADER + msg + self.ENDC

    def fail_header_str(self, msg):
        """
        Print a fail header string (red colored).

        If the output does not support colors, just return the original string.
        """
        return self.FAIL + msg + self.ENDC

    def healthy_str(self, msg):
        """
        Print a healthy string (green colored).

        If the output does not support colors, just return the original string.
        """
        return self.PASS + msg + self.ENDC

    def partial_str(self, msg):
        """
        Print a string that denotes partial progress (yellow colored).

        If the output does not support colors, just return the original string.
        """
        return self.PARTIAL + msg + self.ENDC

    def pass_str(self):
        """
        Print a pass string (green colored).

        If the output does not support colors, just return the original string.
        """
        return self.MOVE_BACK + self.PASS + 'PASS' + self.ENDC

    def skip_str(self):
        """
        Print a skip string (yellow colored).

        If the output does not support colors, just return the original string.
        """
        return self.MOVE_BACK + self.SKIP + 'SKIP' + self.ENDC

    def fail_str(self):
        """
        Print a fail string (red colored).

        If the output does not support colors, just return the original string.
        """
        return self.MOVE_BACK + self.FAIL + 'FAIL' + self.ENDC

    def error_str(self):
        """
        Print a not found string (yellow colored).

        If the output does not support colors, just return the original string.
        """
        return self.MOVE_BACK + self.ERROR + 'ERROR' + self.ENDC

    def not_found_str(self):
        """
        Print an error string (red colored).

        If the output does not support colors, just return the original string.
        """
        return self.MOVE_BACK + self.NOT_FOUND + 'NOT_FOUND' + self.ENDC

    def warn_str(self):
        """
        Print an warning string (yellow colored).

        If the output does not support colors, just return the original string.
        """
        return self.MOVE_BACK + self.WARN + 'WARN' + self.ENDC


term_support = TermSupport()


class LoggingFile(object):

    """
    File-like object that will receive messages pass them to logging.
    """

    def __init__(self, prefix='', level=logging.DEBUG,
                 logger=logging.getLogger()):
        """
        Constructor. Sets prefixes and which logger is going to be used.

        :param prefix - The prefix for each line logged by this object.
        """

        self._prefix = prefix
        self._level = level
        self._buffer = []
        self._logger = logger

    def write(self, data):
        """"
        Writes data only if it constitutes a whole line. If it's not the case,
        store it in a buffer and wait until we have a complete line.
        :param data - Raw data (a string) that will be processed.
        """
        # splitlines() discards a trailing blank line, so use split() instead
        data_lines = data.split('\n')
        if len(data_lines) > 1:
            self._buffer.append(data_lines[0])
            self._flush_buffer()
        for line in data_lines[1:-1]:
            self._log_line(line)
        if data_lines[-1]:
            self._buffer.append(data_lines[-1])

    def writelines(self, lines):
        """"
        Writes itertable of lines

        :param lines: An iterable of strings that will be processed.
        """
        for data in lines:
            self.write(data)

    def _log_line(self, line):
        """
        Passes lines of output to the logging module.
        """
        self._logger.log(self._level, self._prefix + line)

    def _flush_buffer(self):
        if self._buffer:
            self._log_line(''.join(self._buffer))
            self._buffer = []

    def flush(self):
        self._flush_buffer()

    def isatty(self):
        return False


class View(object):

    """
    Takes care of both disk logs and stdout/err logs.
    """

    THROBBER_STEPS = ['-', '\\', '|', '/']
    THROBBER_MOVES = [term_support.MOVE_BACK + THROBBER_STEPS[0],
                      term_support.MOVE_BACK + THROBBER_STEPS[1],
                      term_support.MOVE_BACK + THROBBER_STEPS[2],
                      term_support.MOVE_BACK + THROBBER_STEPS[3]]

    def __init__(self, console_logger='avocado.app', list_mode=False):
        self.list_mode = list_mode
        self.console_log = logging.getLogger(console_logger)
        self.paginator = get_paginator()
        self.throbber_pos = 0

    def log(self, msg, level=logging.INFO, skip_newline=False):
        """
        Write a message to the avocado.app logger or the paginator.

        :param msg: Message to write
        :type msg: string
        """
        extra = {'skip_newline': skip_newline}
        if self.list_mode:
            if not skip_newline:
                msg += '\n'
            self.paginator.write(msg)
        else:
            self.console_log.log(level=level, msg=msg, extra=extra)

    def _log_ui_info(self, msg, skip_newline=False):
        """
        Log a :mod:`logging.INFO` message to the UI.

        :param msg: Message to write.
        """
        self.log(msg, level=logging.INFO, skip_newline=skip_newline)

    def _log_ui_error(self, msg, skip_newline=False):
        """
        Log a :mod:`logging.ERROR` message to the UI.

        :param msg: Message to write.
        """
        self.log(msg, level=logging.ERROR, skip_newline=skip_newline)

    def log_ui_healthy(self, msg, skip_newline=False):
        """
        Log a message that indicates that things are going as expected.

        :param msg: Message to write.
        """
        self._log_ui_info(term_support.healthy_str(msg), skip_newline)

    def log_ui_partial(self, msg, skip_newline=False):
        """
        Log a message that indicates something (at least) partially OK

        :param msg: Message to write.
        """
        self._log_ui_info(term_support.partial_str(msg), skip_newline)

    def log_ui_header(self, msg):
        """
        Log a header message.

        :param msg: Message to write.
        """
        self._log_ui_info(term_support.header_str(msg))

    def log_ui_error(self, msg):
        """
        Log an error message (useful for critical errors).

        :param msg: Message to write.
        """
        self._log_ui_info(term_support.fail_header_str(msg))

    def log_ui_status_pass(self, t_elapsed):
        """
        Log a PASS status message for a given operation.

        :param t_elapsed: Time it took for the operation to complete.
        """
        normal_pass_msg = term_support.pass_str() + " (%.2f s)" % t_elapsed
        self._log_ui_info(normal_pass_msg)

    def log_ui_status_error(self, t_elapsed):
        """
        Log an ERROR status message for a given operation.

        :param t_elapsed: Time it took for the operation to complete.
        """
        normal_error_msg = term_support.error_str() + " (%.2f s)" % t_elapsed
        self._log_ui_error(normal_error_msg)

    def log_ui_status_not_found(self, t_elapsed):
        """
        Log a NOT_FOUND status message for a given operation.

        :param t_elapsed: Time it took for the operation to complete.
        """
        normal_error_msg = term_support.not_found_str() + " (%.2f s)" % t_elapsed
        self._log_ui_error(normal_error_msg)

    def log_ui_status_fail(self, t_elapsed):
        """
        Log a FAIL status message for a given operation.

        :param t_elapsed: Time it took for the operation to complete.
        """
        normal_fail_msg = term_support.fail_str() + " (%.2f s)" % t_elapsed
        self._log_ui_error(normal_fail_msg)

    def log_ui_status_skip(self, t_elapsed):
        """
        Log a SKIP status message for a given operation.

        :param t_elapsed: Time it took for the operation to complete.
        """
        normal_skip_msg = term_support.skip_str()
        self._log_ui_info(normal_skip_msg)

    def log_ui_status_warn(self, t_elapsed):
        """
        Log a WARN status message for a given operation.

        :param t_elapsed: Time it took for the operation to complete.
        """
        normal_warn_msg = term_support.warn_str() + " (%.2f s)" % t_elapsed
        self._log_ui_error(normal_warn_msg)

    def log_ui_throbber_progress(self, progress_from_test=False):
        """
        Give an interactive indicator of the test progress

        :param progress_from_test: if indication of progress came explicitly
                                   from the test. If false, it means the test
                                   process is running, but not communicating
                                   test specific progress.
        :type progress_from_test: bool
        :rtype: None
        """
        if progress_from_test:
            self.log_ui_healthy(self.THROBBER_MOVES[self.throbber_pos], True)
        else:
            self.log_ui_partial(self.THROBBER_MOVES[self.throbber_pos], True)

        if self.throbber_pos == (len(self.THROBBER_MOVES) - 1):
            self.throbber_pos = 0
        else:
            self.throbber_pos += 1

    def start_file_logging(self, logfile, loglevel, unique_id):
        """
        Start the main file logging.

        :param logfile: Path to file that will receive logging.
        :param loglevel: Level of the logger. Example: :mod:`logging.DEBUG`.
        :param unique_id: job.Job() unique id attribute.
        """
        self.job_unique_id = unique_id
        self.debuglog = logfile
        self.file_handler = logging.FileHandler(filename=logfile)
        self.file_handler.setLevel(loglevel)

        fmt = '%(asctime)s %(module)-10.10s L%(lineno)-.4d %(levelname)-5.5s| %(message)s'
        formatter = logging.Formatter(fmt=fmt, datefmt='%H:%M:%S')

        self.file_handler.setFormatter(formatter)
        test_logger = logging.getLogger('avocado.test')
        linux_logger = logging.getLogger('avocado.linux')
        test_logger.addHandler(self.file_handler)
        linux_logger.addHandler(self.file_handler)

    def stop_file_logging(self):
        """
        Simple helper for removing a handler from the current logger.
        """
        test_logger = logging.getLogger('avocado.test')
        linux_logger = logging.getLogger('avocado.linux')
        test_logger.removeHandler(self.file_handler)
        linux_logger.removeHandler(self.file_handler)
        self.file_handler.close()
