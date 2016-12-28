# -*- coding: utf-8  -*-
"""Unit tests for converters."""
from __future__ import unicode_literals

import unittest
from wikidataStuff.helpers import (
    is_int,
    is_pos_int,
    sig_fig_error
)


class TestIsInt(unittest.TestCase):

    """Test the is_int method."""

    def test_is_int_empty_string_fail(self):
        s = ''
        result = is_int(s)
        self.assertEqual(result, False)

    def test_is_int_none_fail(self):
        s = None
        result = is_int(s)
        self.assertEqual(result, False)

    def test_is_int_random_string_fail(self):
        s = 'random_string'
        result = is_int(s)
        self.assertEqual(result, False)

    def test_is_int_float_fail(self):
        s = '123.456'
        result = is_int(s)
        self.assertEqual(result, False)

    def test_is_int_valid_negative_int_succeed(self):
        s = '-123'
        result = is_int(s)
        self.assertEqual(result, True)

    def test_is_int_valid_int_succeed(self):
        s = '123'
        result = is_int(s)
        self.assertEqual(result, True)


class TestIsPosInt(unittest.TestCase):

    """Test the is_pos_int method."""

    def test_is_pos_int_empty_string_fail(self):
        s = ''
        result = is_pos_int(s)
        self.assertEqual(result, False)

    def test_is_pos_int_none_fail(self):
        s = None
        result = is_pos_int(s)
        self.assertEqual(result, False)

    def test_is_pos_int_random_string_fail(self):
        s = 'random_string'
        result = is_pos_int(s)
        self.assertEqual(result, False)

    def test_is_pos_int_float_fail(self):
        s = '123.456'
        result = is_pos_int(s)
        self.assertEqual(result, False)

    def test_is_pos_int_negative_int_fail(self):
        s = '-123'
        result = is_pos_int(s)
        self.assertEqual(result, False)

    def test_is_pos_int_valid_int_succeed(self):
        s = '123'
        result = is_pos_int(s)
        self.assertEqual(result, True)


class TestSigFigError(unittest.TestCase):

    """Test sig_fig_error()."""

    def test_sig_fig_error_zero(self):
        self.assertEqual(sig_fig_error("0"), 0.5)

    def test_sig_fig_error_one(self):
        self.assertEqual(sig_fig_error("1"), 0.5)

    def test_sig_fig_error_big_int(self):
        self.assertEqual(sig_fig_error("200"), 50.0)

    def test_sig_fig_error_exact_int(self):
        self.assertEqual(sig_fig_error("1010"), 5.0)

    def test_sig_fig_error_negative_int(self):
        self.assertEqual(sig_fig_error("-220"), 5.0)

    def test_sig_fig_error_zero_padded_int(self):
        self.assertEqual(sig_fig_error("03300"), 50.0)

    def test_sig_fig_error_decimal_zero(self):
        self.assertEqual(sig_fig_error("0.0"), 0.05)

    def test_sig_fig_error_with_decimal(self):
        self.assertEqual(sig_fig_error("11.0"), 0.05)

    def test_sig_fig_error_with_only_decimal(self):
        self.assertEqual(sig_fig_error("0.1"), 0.05)

    def test_sig_fig_error_negative_with_decimal(self):
        self.assertEqual(sig_fig_error("-0.1234"), 0.00005)
