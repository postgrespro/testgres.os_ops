import typing
import signal as os_signal


T_OS_CMD = typing.Union[str, typing.List[str]]

T_OS_SIGNAL = typing.Union[int, os_signal.Signals]
T_OS_TIMEOUT = typing.Union[int, float]
T_OS_IO = typing.IO[typing.Any]
T_OS_IO_ID = typing.Union[int, T_OS_IO]
T_OS_RUN_INPUT = typing.Union[str, bytes]
