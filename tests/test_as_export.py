#!/usr/bin/env python

import os
from unittest.mock import patch

from as_export.updater import Updater

base_dir = os.path.abspath(__file__ + "/../../")
pid_filepath = os.path.join(base_dir, 'daemon.pid')


def remove_pid_file():
    if os.path.isfile(pid_filepath):
        os.remove(pid_filepath)


def setup_function():
    remove_pid_file()


@patch("as_export.updater.ASpace")
def test_last_export_time(mock_aspace):
    initial_time = 12345
    updater = Updater(False, False, False, False)
    updater.start_time = initial_time
    updater.store_last_export_time()
    updated_time = updater.get_last_export_time()
    assert updated_time == initial_time


@patch("as_export.updater.ASpace")
@patch("as_export.updater.Updater.store_last_export_time")
@patch("as_export.updater.Updater.export_digital_objects")
@patch("as_export.updater.Updater.export_resources")
@patch("as_export.updater.Updater.export_resources_from_objects")
@patch("as_export.updater.Updater.version_data")
def test_argument_handling(
        mock_version_data,
        mock_export_resources_from_objects,
        mock_export_resources,
        mock_export_digital_objects,
        mock_store_last_export_time,
        mock_aspace):

    # Update time
    Updater(True, False, False, False)._run()
    mock_store_last_export_time.assert_called_once()
    for mock in [
            mock_export_digital_objects,
            mock_export_resources,
            mock_export_resources_from_objects]:
        assert mock.call_count == 0
    mock_store_last_export_time.reset_mock()

    # Digital
    remove_pid_file()
    Updater(False, True, False, False)._run()
    mock_export_digital_objects.assert_called_once()
    for mock in [
            mock_store_last_export_time,
            mock_export_resources,
            mock_export_resources_from_objects]:
        assert mock.call_count == 0
    mock_export_digital_objects.reset_mock()

    # Resource digital
    remove_pid_file()
    Updater(False, False, False, True)._run()
    mock_export_digital_objects.assert_called_once()
    mock_export_digital_objects.assert_called_with(resource=True)
    for mock in [
            mock_store_last_export_time,
            mock_export_resources,
            mock_export_resources_from_objects]:
        assert mock.call_count == 0
    mock_export_digital_objects.reset_mock()

    # No args
    remove_pid_file()
    Updater(False, False, False, False)._run()
    for mock in [
            mock_export_resources,
            mock_export_resources_from_objects,
            mock_export_digital_objects,
            mock_store_last_export_time]:
        assert mock.call_count == 1


@patch("as_export.updater.ASpace")
def test_is_running(mock_aspace):
    updater = Updater(False, False, False, False)
    assert updater.is_running() is True
    remove_pid_file()
    assert updater.is_running() is False
