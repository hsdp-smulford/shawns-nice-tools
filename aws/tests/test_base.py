import os
import unittest
from unittest.mock import mock_open, patch

from aws.hap import Base


class TestBase(unittest.TestCase):

    @patch("builtins.open", new_callable=mock_open, read_data='[aws]\nkey = "value"')
    @patch("tomli.load")
    @patch("logging.config.fileConfig")
    def test_base_initialization(self, mock_file_config, mock_tomli_load, mock_open):
        mock_tomli_load.return_value = {"aws": {"key": "value"}}

        base = Base()

        expected_config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config.toml"))
        expected_logging_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "hap", "logging.conf"))

        self.assertEqual(base.config_file, expected_config_path)
        self.assertEqual(base.logging_file, expected_logging_path)
        self.assertEqual(base.config_data, {"aws": {"key": "value"}})
        self.assertTrue(hasattr(base, "logger"))
        mock_file_config.assert_called_once_with(expected_logging_path)
        mock_tomli_load.assert_called_once()

    @patch("builtins.open", new_callable=mock_open, read_data='[aws]\nkey = "value"')
    @patch("tomli.load")
    @patch("logging.config.fileConfig")
    def test_load_config(self, mock_file_config, mock_tomli_load, mock_open):
        mock_tomli_load.return_value = {"aws": {"key": "value"}}

        base = Base()
        config_data = base.load_config()

        self.assertEqual(config_data, {"aws": {"key": "value"}})
        mock_open.assert_called_once_with(base.config_file, "rb")
        mock_tomli_load.assert_called_once()

    @patch("logging.config.fileConfig")
    def test_setup_logging(self, mock_file_config):
        base = Base()
        base.setup_logging()

        self.assertTrue(hasattr(base, "logger"))
        mock_file_config.assert_called_once_with(base.logging_file)


if __name__ == "__main__":
    unittest.main()
