#!/usr/bin/env python

import logging
import time
import traceback
from os import getenv

import boto3
from asnake.client import ASnakeClient
from aws_assume_role_lib import assume_role

logging.basicConfig(
    level=int(getenv('LOGGING_LEVEL', logging.INFO)),
    format='%(filename)s::%(funcName)s::%(lineno)s %(message)s')


class DataExporter:

    def __init__(self):
        """Sets up clients and class attributes."""
        self.service_name = 'as_export'
        self.config = self.get_config(getenv('ENVIRONMENT'))
        self.as_client = ASnakeClient(
            baseurl=self.config['AS_BASEURL'],
            username=self.config['AS_USERNAME'],
            password=self.config['AS_PASSWORD'])
        if not self.as_client.authorize():
            logging.error('Could not authorize ArchivesSpace client, check credentials and try again.')
            raise Exception('Could not authorize ArchivesSpace client, check credentials and try again.')
        self.as_repo_id = self.config['AS_REPO_ID']
        self.s3_client = self.get_client_with_role('s3', getenv('AWS_S3_ROLE'))
        self.page_size = 25

    def get_config(self, environment):
        """Fetch config values from Parameter Store.

        Args:
            ssm_parameter_path (str): Path to parameters

        Returns:
            configuration (dict): all parameters found at the supplied path.
        """
        ssm_parameter_path = f"/{environment}/{self.service_name}"
        configuration = {}
        ssm_client = self.get_client_with_role('ssm', getenv('AWS_SSM_ROLE'))
        try:
            paginator = ssm_client.get_paginator('get_parameters_by_path')
            response_iterator = paginator.paginate(Path=ssm_parameter_path)
            for page in response_iterator:
                for entry in page['Parameters']:
                    param_path_array = entry.get('Name').split("/")
                    section_position = len(param_path_array) - 1
                    section_name = param_path_array[section_position]
                    configuration[section_name] = entry.get('Value')
        except BaseException:
            print("Encountered an error loading config from SSM.")
            traceback.print_exc()
        finally:
            return configuration

    def get_client_with_role(self, resource, role_arn):
        """Gets Boto3 client which authenticates with a specific IAM role.

        Args:
            resource (str): client resource, such as s3
            role_arn: ARN of the role to be assumed

        Returns:
            client with assumed role
        """
        session = boto3.Session()
        assumed_role_session = assume_role(session, role_arn)
        return assumed_role_session.client(resource)

    def export_all(self):
        """Main method which calls all other logic."""
        logging.info('Export of updated resources started')
        start_time = int(time.time())
        last_export_time = self.get_last_export_time()
        updated_resources = self.get_updated_resource_ids(last_export_time)
        for resource_id in updated_resources:
            self.handle_resource_id(resource_id)
        self.store_last_export_time(start_time)
        logging.info(f'{len(updated_resources)} updated resources processed.')

    def list_chunks(self, lst, n):
        """Yield successive n-sized chunks from list.

        Args:
            lst (list): list to chunkify
            n (integer): size of chunk to produce
        """
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    def get_updated_resource_ids(self, last_updated):
        """
        Creates a list of all resources that have been updated,
        or have updated objects within them.

        Args:
            last_updated (int): timestamp after which objects were updated

        Returns:
            updated (list): List of resource ids.
        """
        updated_resources = self.as_client.get(
            f'/repositories/{self.as_repo_id}/resources',
            params={'all_ids': True, "updated_since": last_updated}).json()
        updated_archival_objects = self.as_client.get(
            f'/repositories/{self.as_repo_id}/archival_objects',
            params={'all_ids': True, "updated_since": last_updated}).json()
        for id_chunk in self.list_chunks(updated_archival_objects, self.page_size):
            params = {"id_set": id_chunk, "fields": "resource"}
            ao_chunk = self.as_client.get(f'/repositories/{self.as_repo_id}/archival_objects', params=params).json()
            for archival_object in ao_chunk:
                updated_resources.append(int(archival_object['resource']['ref'].split('/')[-1]))
        return list(set(updated_resources))

    def handle_resource_id(self, resource_id):
        """Handles export of updated resource

        Args:
            resource_id (int): ArchivesSpace ID for a resource record
        """
        logging.debug(f'Handling resource id {resource_id}')
        resource = self.as_client.get(f'/repositories/{self.as_repo_id}/resources/{resource_id}').json()
        filepath = f"{self.config['EAD_DIR']}/{resource['id_0']}.xml"
        if resource['publish']:
            self.save_ead(resource_id, filepath)
        else:
            self.remove_file(filepath)

    def save_ead(self, resource_id, filepath):
        """Saves EAD XML to S3 bucket

        Args:
            resource_id (int): ArchivesSpace ID for a resource record
            filepath (str): Path in which file will be created
        """
        try:
            uri = f'/repositories/{self.as_repo_id}/resource_descriptions/{resource_id}.xml'
            xml = self.as_client.get(
                uri,
                params={
                    'include_unpublished': self.config.get('INCLUDE_UNPUBLISHED'),
                    'include_daos': self.config.get('INCLUDE_DAOS'),
                    'numbered_cs': self.config.get('NUMBERED_CS')
                }
            )
            xml.raise_for_status()
            self.s3_client.put_object(
                Bucket=self.config['AWS_BUCKET'],
                Key=filepath,
                Body=bytes(xml.text, 'utf-8'))
            logging.debug(f'EAD file {filepath} saved')
        except Exception as e:
            logging.error(f'Error saving EAD file {filepath}: {e}')
            self.remove_file(filepath)

    def remove_file(self, filepath):
        """Removes file from bucket if it exists.

        Args:
            filepath (str): filepath to be removed.
        """
        self.s3_client.delete_object(
            Key=filepath,
            Bucket=self.config['AWS_BUCKET'])
        logging.debug(f'File {filepath} removed from bucket {self.config["AWS_BUCKET"]}')

    def get_last_export_time(self):
        """Gets last exported time.

        Returns:
            last_export (int): timestamp of last export time
        """
        try:
            object = self.s3_client.get_object(
                Bucket=self.config['AWS_BUCKET'],
                Key=self.config['LAST_EXPORT_FILENAME'])
            last_export = object['Body'].read().decode("utf-8")
        except Exception:
            last_export = 0
        logging.debug(f'Last export datestamp {last_export} fetched')
        return int(last_export)

    def store_last_export_time(self, last_updated):
        """Sets last exported time.

        Args:
            last_updated (int): timestamp of last export
        """
        self.s3_client.put_object(
            Bucket=self.config['AWS_BUCKET'],
            Key=self.config['LAST_EXPORT_FILENAME'],
            Body=bytes(str(last_updated), 'utf-8'))
        logging.debug(f'Last export time updated to {last_updated}')


if __name__ == "__main__":
    DataExporter().export_all()
