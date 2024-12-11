#!/usr/bin/env python3

from functools import lru_cache, wraps
from typing import Optional

import boto3
from botocore.exceptions import (BotoCoreError, ClientError,
                                 NoCredentialsError, PartialCredentialsError)
from hap.base import Base


def handle_aws_exceptions(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except NoCredentialsError as e:
            self.logger.error(f"Missing AWS credentials: {e}")
            raise
        except PartialCredentialsError as e:
            self.logger.error(f"Partial AWS credentials: {e}")
            raise
        except (BotoCoreError, ClientError) as e:
            self.logger.error(f"AWS error in {func.__name__}: {e}")
            raise

    return wrapper


class AWS(Base):
    """Class for managing AWS sessions, clients, and service interactions."""

    def __init__(
        self, profile: Optional[str] = None, region=None, service: Optional[str] = None, *args, **kwargs
    ) -> None:
        """Initialize the AWS class with a specified profile and service."""
        super().__init__(*args, **kwargs)
        self.logger.info("Initializing AWS class")
        self.session = self.get_session(profile)
        self.service = service
        self.region = region or self.get_region()
        self.client = self.get_client(service) if service else None
        self._load_config("aws")
        self._load_config("aft")

    def __str__(self) -> str:
        """Return a string representation of the AWS object."""
        return str({"account_id": self.account_id, "account_name": self.account_name, "service": self.service})

    @property
    def account_name(self) -> str:
        """Lazy-loaded property for AWS account name."""
        if not hasattr(self, "_account_name"):
            self._account_name = self.get_account_name(self.account_id)
        return self._account_name

    def get_region(self) -> str:
        """Determine the current region based on Availability Zones."""
        try:
            ec2_client = self.get_client("ec2")
            azs = ec2_client.describe_availability_zones()
            if "AvailabilityZones" in azs and azs["AvailabilityZones"]:
                region = azs["AvailabilityZones"][0]["RegionName"]
                self.logger.info(f"Determined region: {region}")
                return region
            else:
                self.logger.warning("No Availability Zones found in the account.")
                return None
        except (ClientError, BotoCoreError) as e:
            self.logger.warning(f"Failed to get region based on AZs: {e}")
            return None

    @lru_cache
    def get_session(self, profile: Optional[str] = None) -> boto3.Session:
        """Create and return a boto3 session."""
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.account_id = session.client("sts").get_caller_identity()["Account"]
        self.logger.info(f"Created boto3 session for: {self.account_id}")
        return session

    @lru_cache
    def get_client(self, service: str, region: Optional[str] = None) -> boto3.client:
        """Return a boto3 client for the specified service, optionally in a specific region."""
        if not region:
            region = self.region if hasattr(self, 'region') else None
        return self.session.client(service, region_name=region)


    @handle_aws_exceptions
    def get_account_name(self, account_id: str) -> Optional[str]:
        """Retrieve the AWS account name using Organizations or IAM alias."""
        try:
            account_info = self.session.client("organizations").describe_account(AccountId=account_id)
            return account_info["Account"]["Name"]
        except (ClientError, BotoCoreError):
            self.logger.warning("Organizations access failed, falling back to IAM account alias.")

        try:
            aliases = self.session.client("iam").list_account_aliases()
            if aliases["AccountAliases"]:
                return aliases["AccountAliases"][0]
        except (ClientError, BotoCoreError) as e:
            self.logger.warning(f"Failed to get account alias: {e}")

        return None

    def _load_config(self, section: str) -> None:
        """Load configuration for the specified section and set attributes."""
        config = self.config_data.get(section, {})
        for key, value in config.items():
            setattr(self, key, value.copy() if isinstance(value, list) else value)
        self.logger.info(f"Loaded {section} configuration into attributes")

    def check_account(
        self,
        account_type: str = "management",
        environment: Optional[str] = None,
        session: Optional[boto3.Session] = None,
    ) -> bool:
        """Check if the current AWS account matches the specified type and environment."""
        self.logger.info(f"Checking account type: {account_type}, environment: {environment}")
        sts_client = session.client("sts") if session else self.get_client("sts")
        current_account_id = sts_client.get_caller_identity()["Account"]
        self.logger.info(f"Current AWS account ID: {current_account_id}")

        account_type_ids = {"payer": [], "management": []}
        for env in self.aft_config.get("dev", []) + self.aft_config.get("prod", []):
            account_type_ids["management"].append(env["management_account_id"])
            account_type_ids["payer"].append(env["payer_account_id"])

        if current_account_id in account_type_ids.get(account_type, []):
            if environment:
                environment_key = f"{current_account_id}_{environment}"
                if self._check_account_environment(environment_key):
                    self.logger.info(f"Account {current_account_id} matches environment {environment}")
                    return True
            else:
                self.logger.info(f"Account {current_account_id} matches account type {account_type}")
                return True

        self.logger.info(f"Account {current_account_id} does not match account type {account_type}")
        return False

    def _check_account_environment(self, environment_key: str) -> bool:
        """Check if the specified environment key exists in account mappings."""
        return environment_key in self.config_data.get("account_environment_mappings", {})

    @handle_aws_exceptions
    def perform_service_action(self, action: str, **kwargs) -> dict:
        """Perform an action on the AWS service client and return the response."""
        method = getattr(self.client, action, None)
        if not method:
            self.logger.error(f"Action {action} is not available for service {self.service}")
            raise AttributeError(f"Invalid action: {action}")
        response = method(**kwargs)
        self.logger.info(f"Performed action {action} on service {self.service}")
        return response

    def try_aws_action(self, client, action: str, **kwargs) -> dict:
        """Helper function to attempt an AWS action with error logging."""
        try:
            return getattr(client, action)(**kwargs)
        except NoCredentialsError as e:
            self.logger.error(f"Missing AWS credentials during {action}: {e}")
            raise
        except PartialCredentialsError as e:
            self.logger.error(f"Partial AWS credentials during {action}: {e}")
            raise
        except (ClientError, BotoCoreError) as e:
            self.logger.error(f"Error during {action}: {e}")
            raise
