#!/usr/bin/env python

import argparse
import configparser
import logging
import os
import random
import shutil
import subprocess
import time
from asnake.aspace import ASpace
from lxml import etree
from requests_toolbelt.downloadutils import stream

base_dir = os.path.normpath(os.path.abspath(os.path.join(os.path.dirname(__file__))))
logging.basicConfig(filename='log.txt', format='%(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)


class XMLException(Exception): pass
class VersionException(Exception): pass


class Updater:
    def __init__(self, update_time=False, archival=False, library=False,
                 digital=False, resource=False, resource_digital=False):
        self.pid_filepath = os.path.join(base_dir, 'daemon.pid')
        if self.is_running():
            raise Exception("Process is still running.")
        else:
            self.write_pid()
        self.update_time = update_time
        self.archival_only = archival
        self.library_only = library
        self.digital_only = digital
        self.target_resource_id = resource
        self.digital_resource_id = resource_digital
        self.log = logging.getLogger(__name__)
        self.config = configparser.ConfigParser()
        self.config.read(os.path.join(base_dir, 'local_settings.cfg'))
        self.data_root = self.config.get('DESTINATIONS', 'data')
        self.ead_dir = os.path.join(self.data_root, self.config.get('DESTINATIONS', 'ead'))
        self.mets_dir = os.path.join(self.data_root, self.config.get('DESTINATIONS', 'mets'))
        self.mods_dir = os.path.join(self.data_root, self.config.get('DESTINATIONS', 'mods'))
        self.pdf_dir = self.config.get('DESTINATIONS', 'pdf')
        self.last_export_filepath = self.config.get('LAST_EXPORT', 'filepath')
        self.repository = self.config.get('ARCHIVESSPACE', 'repository')
        for dir in [self.data_root, self.pdf_dir]:
            if not os.path.isdir(dir):
                os.makedirs(dir)
        try:
            aspace = ASpace(
                baseurl=self.config.get('ARCHIVESSPACE', 'baseurl'),
                user=self.config.get('ARCHIVESSPACE', 'user'),
                password=self.config.get('ARCHIVESSPACE', 'password'))
            self.as_repo = aspace.repositories(self.repository)
            self.client = aspace.client
        except Exception as e:
            raise Exception(e)

    def _run(self):
        self.log.info("Update started")
        self.start_time = int(time.time())
        self.last_export_time = self.get_last_export_time()
        self.changed_list = []
        if self.update_time:
            self.store_last_export_time()
        elif self.archival_only or self.library_only:
            self.export_resources(archival=self.archival_only, library=self.library_only)
        elif self.digital_only or self.digital_resource_id:
            self.export_digital_objects(resource=self.digital_resource_id)
        elif self.target_resource_id:
            r = self.as_repo.resources(self.target_resource_id)
            self.save_ead(r)
            self.save_pdf(r)
        else:
            self.export_resources(archival=True, library=True, updated=self.last_export_time)
            self.export_resources_from_objects(updated=self.last_export_time)
            self.export_digital_objects(updated=self.last_export_time)
            self.store_last_export_time()
        if len(self.changed_list):
            self.version_data()
        self.log.info("Update finished, {} objects changed.".format(len(self.changed_list)))

    def version_data(self):
        try:
            for d in [self.data_root, self.pdf_dir]:
                os.chdir(os.path.join(base_dir, d))
                subprocess.call(['git', 'add', '.'])
                subprocess.call(['git', 'commit', '-a', '-m', '{}'.format(random.choice(open(os.path.join(base_dir, 'quotes.txt')).readlines()))])
                subprocess.call(['git', 'push'])
        except Exception as e:
            self.log.error("Error versioning files: {}".format(e))
            raise VersionException(e)

    def export_resources(self, archival=False, library=False, updated=0):
        for r in self.as_repo.resources.with_params(all_ids=True, modified_since=updated):
            if r.publish:
                if archival and r.id_0.startswith('FA'):
                    self.save_ead(r)
                    self.save_pdf(r)
                elif library and r.id_0.startswith('LI'):
                    self.save_mods(r)
            else:
                if self.remove_file(os.path.join(self.ead_dir, r.id_0, "{}.xml".format(r.id_0))):
                    self.changed_list.append(r.uri)
                    self.log.debug("Resource {} was unpublished and removed".format(r.id_0))

    def export_resources_from_objects(self, updated=0):
        for o in self.as_repo.archival_objects.with_params(all_ids=True, modified_since=updated):
            r = o.resource
            if r.publish:
                if r.uri not in self.changed_list:
                    self.save_ead(r)
                    self.save_pdf(r)
            else:
                if self.remove_file(os.path.join(self.ead_dir, r.id_0, "{}.xml".format(r.id_0))):
                    self.changed_list.append(r.uri)
                    self.log.debug("Resource {} was unpublished and removed".format(r.id_0))

    def export_digital_objects(self, updated=0, resource=None):
        if resource:
            self.log.debug("Exporting digital objects for resource {}".format(resource))
            digital_objects = []
            for component in self.as_repo.resources(resource).tree.walk:
                for instance in component.instances:
                    if instance.instance_type == 'digital_object':
                        digital_objects.append(instance.digital_object)
        else:
            self.log.debug("Exporting digital objects updated since {}".format(updated))
            digital_objects = self.as_repo.digital_objects.with_params(all_ids=True, modified_since=updated)
        for d in digital_objects:
            if d.publish:
                self.save_mets(d)
            else:
                if self.remove_file(os.path.join(self.mets_dir, d.digital_object_id, "{}.xml".format(d.digital_object_id))):
                    self.changed_list.append(d.uri)
                    self.log.debug("Digital object {} was unpublished and removed".format(d.digital_object_id))

    def save_ead(self, resource):
        target_dir = self.make_target_dir(os.path.join(self.ead_dir, resource.id_0))
        try:
            self.save_xml_to_file(os.path.join(target_dir, "{}.xml".format(resource.id_0)),
                                  '/repositories/{}/resource_descriptions/{}.xml'
                                    .format(self.repository, os.path.split(resource.uri)[1]))
            self.changed_list.append(resource.uri)
            self.log.debug("EAD file {} saved".format(resource.id_0))
        except Exception as e:
            self.log.error("Error saving EAD file {}: {}".format(resource.id_0, e))
            if self.remove_file(os.path.join(target_dir, "{}.xml".format(resource.id_0))):
                self.changed_list.append(resource.uri)

    def save_mods(self, resource):
        target_dir = self.make_target_dir(os.path.join(self.mods_dir, resource.id_0))
        try:
            self.save_xml_to_file(os.path.join(target_dir, "{}.xml".format(resource.id_0)),
                                  '/repositories/{}/resource_descriptions/{}.xml'
                                    .format(self.repository, os.path.split(resource.uri)[1]),
                                  mods=True)
            self.changed_list.append(resource.uri)
            self.log.debug("MODS file {} saved".format(resource.id_0))
        except Exception as e:
            self.log.error("Error saving MODS file {}: {}".format(resource.id_0, e))
            if self.remove_file(os.path.join(target_dir, "{}.xml".format(resource.id_0))):
                self.changed_list.append(resource.uri)

    def save_mets(self, digital):
        target_dir = self.make_target_dir(os.path.join(self.mets_dir, digital.digital_object_id))
        try:
            self.save_xml_to_file(os.path.join(target_dir, "{}.xml".format(digital.digital_object_id)),
                                  '/repositories/{}/digital_objects/mets/{}.xml'
                                    .format(self.repository, os.path.split(digital.uri)[1]))
            self.changed_list.append(digital.uri)
            self.log.debug("METS file {} saved".format(digital.digital_object_id))
        except Exception as e:
            self.log.error("Error saving METS file {}: {}".format(digital.digital_object_id, e))
            if self.remove_file(os.path.join(target_dir, "{}.xml".format(digital.digital_object_id))):
                self.changed_list.append(digital.uri)

    def save_pdf(self, resource):
        target_dir = self.make_target_dir(os.path.join(self.pdf_dir, resource.id_0))
        subprocess.call(['java', '-jar', 'ead2pdf.jar',
                         os.path.join(self.ead_dir, resource.id_0, "{}.xml".format(resource.id_0)),
                         os.path.join(target_dir, "{}.pdf".format(resource.id_0))])
        self.log.debug("PDF for {} generated".format(resource.id_0))

    def remove_file(self, file_path):
        if os.path.isfile(file_path):
            shutil.rmtree(os.path.split(file_path)[0])
            self.log.debug("{} removed".format(file_path))
            if self.ead_dir in file_path:
                pdf_path = file_path.replace(self.ead_dir, self.pdf_dir).replace('.xml', '.pdf')
                if os.path.isfile(pdf_path):
                    shutil.rmtree(os.path.split(pdf_path)[0])
                    self.log.debug("{} removed".format(pdf_path))
            return True
        return False

    def make_target_dir(self, target):
        if not os.path.exists(target):
            os.makedirs(target)
        return target

    def is_running(self):
        if os.path.isfile(self.pid_filepath):
            with open(self.pid_filepath, "r") as f:
                for line in f:
                    try:
                        os.kill(int(line.strip()), 0)
                        self.log.error("Process is already running with PID {}".format(int(line.strip())))
                        return True
                    except OSError:
                        pass
                return False

    def write_pid(self):
        with open(self.pid_filepath, 'w') as f:
            f.write(str(os.getpid()))

    def get_last_export_time(self):
        last_export = 0
        if os.path.isfile(self.last_export_filepath):
            with open(self.last_export_filepath, 'r') as f:
                last_export = f.read()
        return int(last_export)

    def store_last_export_time(self):
        with open(self.last_export_filepath, 'w') as f:
            f.write(str(self.start_time))
        self.log.debug("Last export time updated to {}".format(self.start_time))

    def save_xml_to_file(self, filepath, uri, mods=False):
        try:
            with open(filepath, 'wb') as f:
                xml = self.client.get(uri, params={"include_unpublished": self.config.get('EAD', 'unpublished'),
                                                   "include_daos": self.config.get('EAD', 'daos'),
                                                   "numbered_cs": self.config.get('EAD', 'numbered')})
                parser = etree.XMLParser(resolve_entities=False, strip_cdata=False, remove_blank_text=True)
                parsed = etree.fromstring(xml.text.encode(), parser)
                xsl = etree.XSLT(etree.parse('ead_to_mods.xsl'))
                f.write(xsl(parsed)) if mods else stream.stream_response_to_file(xml, path=f)
        except Exception as e:
            self.log.error("XML error: {}".format(e))
            raise XMLException(e)


def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--update_time', action='store_true', help='Updates last_export time and exits')
    parser.add_argument('--archival', action='store_true', help='Exports finding aids only')
    parser.add_argument('--library', action='store_true', help='Exports library records only')
    parser.add_argument('--digital', action='store_true', help='Exports digital objects only')
    parser.add_argument('--resource', help='Exports a single resource record only')
    parser.add_argument('--resource_digital', help='Exports the digital objects associated with a resource record only')
    args = parser.parse_args()

    Updater(update_time=args.update_time, archival=args.archival, library=args.library, digital=args.digital,
            resource=args.resource, resource_digital=args.resource_digital)._run()

main()
