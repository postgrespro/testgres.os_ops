# coding: utf-8
from src.raise_error import RaiseError

import pytest


class TestRaiseError:
    def test_001__MethodIsNotImplemented(self):
        with pytest.raises(expected_exception=NotImplementedError) as x:
            RaiseError.MethodIsNotImplemented(str, "mymethod")

        assert type(x.value) is NotImplementedError
        assert str(x.value) == "Method str::mymethod is not implemented."
        return

    def test_002__PropertyIsNotImplemented(self):
        with pytest.raises(expected_exception=NotImplementedError) as x:
            RaiseError.PropertyIsNotImplemented(str, "get_myprop")

        assert type(x.value) is NotImplementedError
        assert str(x.value) == "Property str::get_myprop is not implemented."
        return
