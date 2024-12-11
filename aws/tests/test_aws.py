import unittest
from unittest.mock import MagicMock, patch

from botocore.exceptions import BotoCoreError, ClientError
from hap.aws import AWS


class TestAWS(unittest.TestCase):

    @patch("boto3.client")
    def setUp(self, mock_boto_client):
        # Mocking the boto3 client to return a mock client
        self.mock_boto_client = MagicMock()
        mock_boto_client.return_value = self.mock_boto_client

        # Set up AWS instance
        self.aws = AWS(service="s3", config_file="config.toml", logging_file="logging.conf")

        # Mocking the logger to prevent actual logging
        self.aws.logger = MagicMock()

    @patch.object(AWS, "_load_class_config")
    def test_initialize_with_service(self, mock_load_class_config):
        # Mocking the config loading method
        mock_load_class_config.side_effect = lambda section: {"aws": {"key": "value"}} if section == "aws" else {}

        self.assertEqual(self.aws.service, "s3")
        self.assertIsNotNone(self.aws.client)
        self.mock_boto_client.assert_called_once_with("s3")

    @patch.object(AWS, "_get_client")
    def test_initialize_without_service(self, mock_get_client):
        self.aws_no_service = AWS(config_file="config.toml", logging_file="logging.conf")

        self.assertIsNone(self.aws_no_service.service)
        self.assertIsNone(self.aws_no_service.client)
        mock_get_client.assert_not_called()

    @patch("boto3.client")
    def test_check_account(self, mock_boto_client):
        mock_sts_client = MagicMock()
        mock_boto_client.return_value = mock_sts_client
        self.aws.sts_client = mock_sts_client
        mock_sts_client.get_caller_identity.return_value = {"Account": "123456789012"}

        # Mocking the AFT configuration
        self.aws.aft_config = {
            "dev": [{"management_account_id": "123456789012", "payer_account_id": "987654321098"}],
            "prod": [{"management_account_id": "223344556677", "payer_account_id": "665544332211"}],
        }

        # Test case where account matches management account
        result = self.aws.check_account(account_type="management", environment="dev")
        self.assertTrue(result)

        # Test case where account does not match management account
        result = self.aws.check_account(account_type="management", environment="prod")
        self.assertFalse(result)

    @patch("boto3.client")
    def test_failed_check_account(self, mock_boto_client):
        mock_sts_client = MagicMock()
        mock_boto_client.return_value = mock_sts_client
        self.aws.sts_client = mock_sts_client
        mock_sts_client.get_caller_identity.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}, "GetCallerIdentity"
        )

        # Test failed account check due to AWS error
        result = self.aws.check_account(account_type="management")
        self.assertFalse(result)

    @patch("boto3.client")
    def test_perform_service_action(self, mock_boto_client):
        mock_service_response = {"ResponseMetadata": {"RequestId": "abcd-1234"}}
        self.mock_boto_client.some_action.return_value = mock_service_response

        # Test action execution
        response = self.aws.perform_service_action("some_action", Param1="value1")
        self.assertEqual(response, mock_service_response)
        self.mock_boto_client.some_action.assert_called_with(Param1="value1")

    @patch("boto3.client")
    def test_failed_perform_service_action(self, mock_boto_client):
        self.mock_boto_client.some_action.side_effect = BotoCoreError("Error occurred")

        with self.assertRaises(BotoCoreError):
            self.aws.perform_service_action("some_action", Param1="value1")


if __name__ == "__main__":
    unittest.main()
