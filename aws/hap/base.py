#!/usr/bin/env python3

import json
import logging.config
import os
from typing import Optional

import tomli
import yaml


class Base:
    def __init__(self, config_file: Optional[str] = None, logging_file: Optional[str] = None) -> None:
        """
        Initialize the Base class with optional configuration and logging file paths.
        If no file paths are provided, default values are used.
        """
        self.config_file = config_file or os.getenv(
            "CONFIG_FILE", os.path.join(os.path.dirname(__file__), "..", "config.toml")
        )
        self.logging_file = logging_file or os.getenv(
            "LOGGING_FILE", os.path.join(os.path.dirname(__file__), "logging.conf")
        )

        self.setup_logging()
        self.logger.debug("Initializing Base class")

        self.config_data = self.load_config()

    def load_config(self):
        """
        Load configuration from the specified file.
        Supports TOML, JSON, and YAML formats.
        """
        file_extension = os.path.splitext(self.config_file)[1].lower()

        try:
            with open(self.config_file, "rb") as f:
                if file_extension == ".toml":
                    return tomli.load(f)
                elif file_extension == ".json":
                    return json.load(f)
                elif file_extension in (".yaml", ".yml"):
                    return yaml.safe_load(f)
                else:
                    raise RuntimeError(f"Unsupported config file format: {file_extension}")

        except FileNotFoundError:
            self.logger.error(f"{self.config_file} not found.")
            raise RuntimeError(f"{self.config_file} not found.")
        except (tomli.TOMLDecodeError, json.JSONDecodeError, yaml.YAMLError) as e:
            self.logger.error(f"Failed to parse {self.config_file}: {e}")
            raise RuntimeError(f"Failed to parse {self.config_file}: {e}")

    def setup_logging(self):
        """
        Set up logging configuration from the specified logging file.
        """
        try:
            logging.config.fileConfig(self.logging_file)
            self.logger = logging.getLogger(self.__class__.__name__)
            self.logger.debug(f"Logging configured using {self.logging_file}")
        except Exception as e:
            raise RuntimeError(f"Logging setup failed: {e}")

    def reload_config(self):
        """
        Reload the configuration file.
        This will reinitialize the config data in case of updates.
        """
        self.logger.info(f"Reloading configuration from {self.config_file}")
        self.config_data = self.load_config()

    def update_logging_config(self, new_logging_file: Optional[str] = None):
        """
        Update the logging configuration during runtime.
        This is useful for dynamically changing log levels, handlers, etc.
        """
        new_logging_file = new_logging_file or self.logging_file
        try:
            logging.config.fileConfig(new_logging_file)
            self.logger.debug(f"Logging updated using {new_logging_file}")
        except Exception as e:
            self.logger.error(f"Failed to update logging configuration: {e}")
