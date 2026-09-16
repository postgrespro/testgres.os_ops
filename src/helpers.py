from __future__ import annotations

from .types import T_OS_RUN_INPUT

import locale
import typing


# Workaround for bug in Popen::_save_input:
#  it tries to call input.encode when text_mode is true
class _BinDataBox(bytes):
    def encode(self, *args, **kwargs) -> _BinDataBox:
        return self


class Helpers:
    @staticmethod
    def _make_get_default_encoding_func():
        # locale.getencoding is added in Python 3.11
        if hasattr(locale, 'getencoding'):
            return locale.getencoding

        # It must exist
        return locale.getpreferredencoding

    # Prepared pointer on function to get a name of system codepage
    _get_default_encoding_func = _make_get_default_encoding_func.__func__()

    @staticmethod
    def get_default_encoding():
        #
        #   Original idea/source was:
        #
        #   def os_ops.get_default_encoding():
        #       if not hasattr(locale, 'getencoding'):
        #       locale.getencoding = locale.getpreferredencoding
        #       return locale.getencoding() or 'UTF-8'
        #

        assert __class__._get_default_encoding_func is not None

        r = __class__._get_default_encoding_func()

        if r:
            assert r is not None
            assert type(r) is str
            assert r != ""
            return r

        # Is it an unexpected situation?
        return 'UTF-8'

    @staticmethod
    def prepare_process_input(
        input: typing.Optional[T_OS_RUN_INPUT],
        encoding: typing.Optional[str],
    ) -> typing.Optional[bytes]:
        assert encoding is None or type(encoding) is str

        if input is None:
            return None

        if type(input) is str:
            if encoding is None:
                b = input.encode(__class__.get_default_encoding())
            else:
                assert type(encoding) is str
                b = input.encode(encoding)
            return _BinDataBox(b)

        # It is expected!
        assert type(input) is bytes
        return _BinDataBox(input)

    # OLD NAMES [DEPRECATED SINCE OS_OPS 3.1.0] -------------------------

    @staticmethod
    def GetDefaultEncoding():
        #
        # Dependencies:
        #  - testgres.utils.execute_utility2 < 1.15
        #
        return __class__.get_default_encoding()

    @staticmethod
    def PrepareProcessInput(
        input: typing.Optional[typing.Union[str, bytes]],
        encoding: typing.Optional[str],
    ) -> typing.Optional[bytes]:
        #
        # Dependencies:
        #  - no information
        #
        return __class__.prepare_process_input(
            input,
            encoding,
        )
