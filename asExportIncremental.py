#!/usr/bin/env python

import os, requests, json, sys, time, pickle, logging, ConfigParser, re
from lxml import etree

# local config file, containing variables
config = ConfigParser.ConfigParser()
config.read('local_settings.cfg')

dictionary = {'baseURL': config.get('ArchivesSpace', 'baseURL'), 'repository':config.get('ArchivesSpace', 'repository'), 'user': config.get('ArchivesSpace', 'user'), 'password': config.get('ArchivesSpace', 'password')}
repositoryBaseURL = '{baseURL}/repositories/{repository}/'.format(**dictionary)

lastExportFilepath = config.get('LastExport', 'filepath')
# EAD Export options
exportUnpublished = config.get('EADexport', 'exportUnpublished')
exportDaos = config.get('EADexport', 'exportDaos')
exportNumbered = config.get('EADexport', 'exportNumbered')
exportPdf = config.get('EADexport', 'exportPdf')
# URI lists (to be populated by URIs of exported or deleted resource records)
uriExportList = []
uriDeleteList = []
# PDF export utility filePath
PDFConvertFilepath = config.get('PDFexport', 'filepath')
# logging configs
logging.basicConfig(filename=config.get('Logging', 'filename'),format=config.get('Logging', 'format', 1), datefmt=config.get('Logging', 'datefmt', 1), level=config.get('Logging', 'level', 0))

# export destinations, should end with a trailing slash
dataDestination = '/Users/harnold/Desktop/data/'
EADdestination = dataDestination + 'ead/'
METSdestination = dataDestination + 'mets/'
PDFdestination = '/Users/harnold/Desktop/pdf/'

def makeDestinations():
    destinations = [EADdestination, PDFdestination, METSdestination]
    for d in destinations:
        if not os.path.exists(d):
            os.makedirs(d)

# authenticates the session
def authenticate():
    try:
        auth = requests.post('{baseURL}/users/{user}/login?password={password}'.format(**dictionary)).json()
        token = {'X-ArchivesSpace-Session':auth["session"]}
        return token
    except ConnectionError:
        logging.error('Authentication failed!')

# gets time of last export
def readTime():
    # last export time in Unix epoch time, for example 1439563523
    if os.path.isfile(lastExportFilepath):
        with open(lastExportFilepath, 'rb') as pickle_handle:
            lastExport = str(pickle.load(pickle_handle))
    else:
        lastExport = 0
    return lastExport

# store the current time in Unix epoch time, for example 1439563523
def updateTime():
    with open(lastExportFilepath, 'wb') as pickle_handle:
        pickle.dump(exportStartTime, pickle_handle)

# formats XML files
def prettyPrintXml(filePath, resourceID, identifier):
    assert filePath is not None
    parser = etree.XMLParser(resolve_entities=False, strip_cdata=False, remove_blank_text=True)
    try:
        etree.parse(filePath, parser)
        document = etree.parse(filePath, parser)
        document.write(filePath, pretty_print=True, encoding='utf-8')
        createPDF(resourceID)
    except:
        logging.warning('%s is invalid and will be removed', resourceID)
        removeEAD(resourceID, identifier)

# creates pdf from EAD
def createPDF(resourceID):
    if not os.path.exists(PDFdestination+resourceID):
        os.makedirs(PDFdestination+resourceID)
    os.system("java -jar "+PDFConvertFilepath+" "+EADdestination+resourceID+'/'+resourceID+'.xml'+" "+PDFdestination+resourceID+'/'+resourceID+'.pdf')
    logging.warning('%s%s/%s.pdf created', PDFdestination, resourceID, resourceID)

# Exports EAD file
def exportEAD(resourceID, identifier, headers):
    ead = requests.get(repositoryBaseURL+'resource_descriptions/'+str(identifier)+'.xml?include_unpublished={exportUnpublished}&include_daos={exportDaos}&numbered_cs={exportNumbered}&print_pdf={exportPdf}'.format(exportUnpublished=exportUnpublished, exportDaos=exportDaos, exportNumbered=exportNumbered, exportPdf=exportPdf), headers=headers, stream=True)
    if not os.path.exists(EADdestination+resourceID+'/'):
        os.makedirs(EADdestination + resourceID+'/')
    with open(EADdestination+resourceID+'/'+resourceID+'.xml', 'wb') as f:
        for chunk in ead.iter_content(10240):
            f.write(chunk)
    f.close
    logging.warning('%s exported to %s', resourceID, EADdestination)
    #validate here
    prettyPrintXml(EADdestination+resourceID+'/'+resourceID+'.xml', resourceID)

# Exports METS file
def exportMETS(doID, headers):
    mets = requests.get(repositoryBaseURL+'digital_objects/mets/'+str(doID)+'.xml', headers=headers).text
    if not os.path.exists(METSdestination+doID+'/'):
        os.makedirs(METSdestination+doID+'/')
    f = open(METSdestination+doID+'/'+doID+'.xml', 'w')
    f.write(mets.encode('utf-8'))
    f.close
    logging.warning('%s exported to %s', doID, METSdestination)
    #validate here

# Deletes EAD file if it exists
def removeEAD(resourceID):
    if os.path.isfile(EADdestination+resourceID+'/'+resourceID+'.xml'):
        os.remove(EADdestination+resourceID+'/'+resourceID+'.xml')
        os.rmdir(EADdestination+resourceID+'/')
        logging.warning('%s.xml deleted from %s%s', resourceID, EADdestination, resourceID)
    else:
        logging.warning('%s.xml does not exist, no need to delete', resourceID)

# Deletes METS file if it exists
def removeMETS(doID):
    if os.path.isfile(METSdestination+doID+'/'+doID+'.xml'):
        os.remove(METSdestination+doID+'/'+doID+'.xml')
        os.rmdir(METSdestination+doID+'/')
        logging.warning('%s.xml deleted from %s%s', doID, METSdestination, doID)
    else:
        logging.warning('%s.xml does not exist, no need to delete', doID)

def handleResource(resource, headers):
    resourceID = resource["id_0"]
    identifier = re.split('^/repositories/[1-9]*/resources/',resource["uri"])[1]
    if resource["publish"] and not ('LI' in resourceID):
        exportEAD(resourceID, identifier, headers)
        uriExportList.append(resource["uri"])
    else:
        removeEAD(resourceID)
        uriDeleteList.append(resource["uri"])

def handleDigitalObject(digital_object, headers):
    doID = digital_object["digital_object_id"]
    if digital_object["publish"]:
        component = (requests.get(baseURL + digital_object["linked_instances"][0]["ref"], headers=headers)).json()
        if component["jsonmodel_type"] == 'resource':
            resource = digital_object["linked_instances"][0]["ref"]
        else:
            resource = component["resource"]["ref"]
        if resource in uriExportList:
            exportMETS(doID, headers)
        elif resource in uriDeleteList:
            removeMETS(doID)
    else:
        removeMETS(doID)

# Looks for updated resources
def findUpdatedResources(lastExport):
    headers = authenticate()
    resourceIds = requests.get(repositoryBaseURL+'resources?all_ids=true&modified_since='+str(lastExport), headers=headers)
    logging.warning('*** Checking resources ***')
    for r in resourceIds.json():
        if not requests.get(repositoryBaseURL+'resources/' + str(r), headers=headers):
            headers = authenticate()
        resource = (requests.get(repositoryBaseURL+'resources/' + str(r), headers=headers)).json()
        handleResource(resource, headers)

# Looks for updated components
def findUpdatedObjects(lastExport):
    headers = authenticate()
    archival_objects = requests.get(repositoryBaseURL+'archival_objects?all_ids=true&modified_since='+str(lastExport), headers=headers)
    logging.warning('*** Checking archival objects ***')
    for a in archival_objects.json():
        if not requests.get(repositoryBaseURL+'archival_objects/'+str(a), headers=headers):
            headers = authenticate()
        archival_object = requests.get(repositoryBaseURL+'archival_objects/'+str(a), headers=headers).json()
        resource = (requests.get(baseURL +archival_object["resource"]["ref"], headers=headers)).json()
        if not resource["uri"] in uriExportList and not resource["uri"] in uriDeleteList:
            handleResource(resource, headers)

# Looks for updated digital objects
def findUpdatedDigitalObjects(lastExport):
    headers = authenticate()
    doIds = requests.get(repositoryBaseURL+'digital_objects?all_ids=true&modified_since='.format(**dictionary)+str(lastExport), headers=headers)
    logging.warning('*** Checking digital objects ***')
    for d in doIds.json():
        if not requests.get(repositoryBaseURL+'digital_objects/' + str(d), headers=headers):
            headers = authenticate()
        digital_object = (requests.get(repositoryBaseURL+'digital_objects/' + str(d), headers=headers)).json()
        handleDigitalObject(digital_object, headers)

# Looks for digital objects associated with updated resource records
def findAssociatedDigitalObjects():
    headers = authenticate()
    doIds = requests.get(repositoryBaseURL+'digital_objects?all_ids=true', headers=headers)
    logging.warning('*** Checking associated digital objects ***')
    for d in doIds.json():
        if not requests.get(repositoryBaseURL+'digital_objects/' + str(d), headers=headers):
            headers = authenticate()
        digital_object = (requests.get(repositoryBaseURL+'digital_objects/' + str(d), headers=headers)).json()
        handleDigitalObject(digital_object, headers)

#run script to version using git
def versionFiles():
    logging.warning('*** Versioning files and pushing to Github ***')
    destinations = [dataDestination, PDFdestination]
    for d in destinations:
        os.system("./gitVersion.sh "+d)

def main():
    logging.warning('=========================================')
    logging.warning('*** Export started ***')
    exportStartTime = int(time.time())
    lastExport = readTime()
    makeDestinations()
    findUpdatedResources(lastExport)
    findUpdatedObjects(lastExport)
    findUpdatedDigitalObjects(lastExport)
    if len(uriExportList) > 0 or len(uriDeleteList) > 0:
        findAssociatedDigitalObjects()
    else:
        logging.warning('*** Nothing was exported ***')
    #versionFiles()
    logging.warning('*** Export completed ***')
    updateTime()

main()
