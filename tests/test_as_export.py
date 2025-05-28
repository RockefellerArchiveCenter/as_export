from os import getenv
from unittest.mock import patch

import boto3
import botocore
import pytest
from moto import mock_aws

from src.export import DataExporter


@mock_aws
@pytest.fixture
@patch('src.export.DataExporter.get_config')
@patch('src.export.ASnakeClient.authorize')
def mock_exporter(mock_authorize, mock_config):
    mock_authorize.return_value = True
    mock_config.return_value = {
        "AS_BASEURL": "baseurl",
        "AS_USERNAME": "username",
        "AS_PASSWORD": "password",
        "AS_REPO_ID": "2",
        "INCLUDE_UNPUBLISHED": False,
        "INCLUDE_DAOS": True,
        "NUMBERED_CS": False,
        "EAD_DIR": "ead",
        "AWS_BUCKET": "test-bucket",
        "LAST_EXPORT_FILENAME": "last-export.txt"}
    return DataExporter()


@patch('src.export.DataExporter.get_config')
@patch('src.export.DataExporter.get_client_with_role')
@patch('src.export.ASnakeClient.authorize')
def test_init(mock_authorize, mock_s3, mock_config):
    mock_authorize.return_value = True
    mock_config.return_value = {
        "AS_BASEURL": "baseurl",
        "AS_USERNAME": "username",
        "AS_PASSWORD": "password",
        "AS_REPO_ID": "2",
        "EAD_DIR": "ead",
        "AS_REPO_ID": "2",
        "EAD_DIR": "ead",
        "AWS_BUCKET": "test-bucket",
        "LAST_EXPORT_FILENAME": "last-export.txt"}

    DataExporter()

    mock_s3.assert_called_once_with('s3', getenv('AWS_S3_ROLE'))
    mock_config.assert_called_once_with(getenv('ENVIRONMENT'))


@patch('src.export.DataExporter.get_last_export_time')
@patch('src.export.DataExporter.get_updated_resource_ids')
@patch('src.export.DataExporter.handle_resource_id')
@patch('src.export.DataExporter.store_last_export_time')
@patch('src.export.DataExporter.__init__')
def test_export_all(mock_init, mock_update_time, mock_handle, mock_updated_ids, mock_get_time):
    mock_init.return_value = None
    mock_get_time.return_value = 123456789
    mock_updated_ids.return_value = ["1"]

    DataExporter().export_all()

    mock_get_time.assert_called_once()
    mock_updated_ids.assert_called_once_with(123456789)
    mock_handle.assert_called_once_with("1")
    mock_update_time.assert_called_once()


# TODO add data
@patch('src.export.ASnakeClient.get')
def test_get_updated_resource_ids(mock_get, mock_exporter):
    mock_get.return_value.json.side_effect = [
        [1, 2, 3],  # updated resources
        [4, 5, 6],  # updated archival objects
        [
            {"resource": {"ref": "/repositories/2/resources/4"}},
            {"resource": {"ref": "/repositories/2/resources/4"}},
            {"resource": {"ref": "/repositories/2/resources/4"}}],  # id_set
    ]
    updated_resources = mock_exporter.get_updated_resource_ids(123456789)
    assert set(updated_resources) == set([1, 2, 3, 4])


@patch('src.export.ASnakeClient.get')
@patch('src.export.DataExporter.save_ead')
@patch('src.export.DataExporter.remove_file')
def test_handle_resource_id(mock_remove, mock_save, mock_get, mock_exporter):
    mock_get.return_value.json.return_value = {"id_0": "foo", "publish": True}
    mock_exporter.ead_dir = "ead"
    mock_exporter.as_repo_id = 2

    mock_exporter.handle_resource_id(1)
    mock_remove.assert_not_called()
    mock_save.assert_called_once_with(1, "ead/foo.xml")
    mock_get.assert_called_once_with('/repositories/2/resources/1')

    for m in [mock_save, mock_remove, mock_get]:
        m.reset_mock()
    mock_get.return_value.json.return_value = {"id_0": "foo", "publish": False}
    mock_exporter.handle_resource_id(1)
    mock_remove.assert_called_once_with("ead/foo.xml")
    mock_save.assert_not_called()
    mock_get.assert_called_once_with('/repositories/2/resources/1')


@mock_aws
@patch('src.export.ASnakeClient.get')
@patch('src.export.DataExporter.remove_file')
def test_save_ead(mock_remove, mock_get, mock_exporter):
    aws_bucket = "test-bucket"
    filepath = "ead/foo.xml"
    s3 = boto3.client('s3')
    s3.create_bucket(Bucket=aws_bucket)
    mock_get.return_value = "xml"
    mock_exporter.save_ead("1", filepath)
    s3.head_object(Bucket=aws_bucket, Key=filepath)

    mock_get.side_effect = Exception("bar")
    mock_exporter.save_ead("1", filepath)
    mock_remove.assert_called_once_with(filepath)


@mock_aws
def test_remove_file(mock_exporter):
    aws_bucket = "test-bucket"
    filepath = "ead/foo.xml"
    s3 = boto3.client('s3')
    s3.create_bucket(Bucket=aws_bucket)
    s3.put_object(
        Bucket=aws_bucket,
        Key=filepath,
        Body=bytes("xml", 'utf-8'))
    mock_exporter.remove_file(filepath)
    with pytest.raises(botocore.exceptions.ClientError) as e:
        s3.head_object(Bucket=aws_bucket, Key=filepath)
    assert str(e.value) == "An error occurred (404) when calling the HeadObject operation: Not Found"


@mock_aws
def test_get_last_export_time(mock_exporter):
    aws_bucket = "test-bucket"
    s3 = boto3.client('s3')
    s3.create_bucket(Bucket=aws_bucket)

    last_exported = mock_exporter.get_last_export_time()
    assert last_exported == 0

    s3.put_object(
        Bucket=aws_bucket,
        Key="last-export.txt",
        Body=bytes("123456789", "utf-8"))

    last_exported = mock_exporter.get_last_export_time()
    assert last_exported == 123456789


@mock_aws
def test_store_last_export_time(mock_exporter):
    aws_bucket = "test-bucket"
    s3 = boto3.client('s3')
    s3.create_bucket(Bucket=aws_bucket)

    mock_exporter.store_last_export_time(123456789)

    last_exported = mock_exporter.get_last_export_time()
    assert last_exported == 123456789
