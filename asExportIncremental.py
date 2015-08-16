#!/usr/bin/env python

import os, requests, json, sys, time, pickle, logging, ConfigParser, re, subprocess
from lxml import etree

# local config file, containing variables
config = ConfigParser.ConfigParser()
config.read('local_settings.cfg')
# URL parameters dictionary, used to manage common URL patterns
dictionary = {'baseURL': config.get('ArchivesSpace', 'baseURL'), 'repository':config.get('ArchivesSpace', 'repository'), 'user': config.get('ArchivesSpace', 'user'), 'password': config.get('ArchivesSpace', 'password')}
baseURL = '{baseURL}'.format(**dictionary)
repositoryBaseURL = '{baseURL}/repositories/{repository}/'.format(**dictionary)
# Location of Pickle file which contains last export time
lastExportFilepath = config.get('LastExport', 'filepath')
# EAD Export options
exportUnpublished = config.get('EADexport', 'exportUnpublished')
exportDaos = config.get('EADexport', 'exportDaos')
exportNumbered = config.get('EADexport', 'exportNumbered')
exportPdf = config.get('EADexport', 'exportPdf')
# URI lists (to be populated by URIs of exported or deleted records)
uriExportList = []
uriDeleteList = []
doExportList = []
doDeleteList = []
# EAD to PDF export utility filePath
PDFConvertFilepath = config.get('PDFexport', 'filepath')
# Logging configuration
logging.basicConfig(filename=config.get('Logging', 'filename'),format=config.get('Logging', 'format', 1), datefmt=config.get('Logging', 'datefmt', 1), level=config.get('Logging', 'level', 0))
# Sets logging of requests to WARNING to avoid unneccessary info
logging.getLogger("requests").setLevel(logging.WARNING)

# export destinations, os.path.sep makes these absolute URLs
dataDestination = os.path.join(os.path.sep,'Users','harnold','Desktop','data')
EADdestination = os.path.join(dataDestination,'ead')
METSdestination = os.path.join(dataDestination,'mets')
PDFdestination = os.path.join(os.path.sep,'Users','harnold','Desktop','pdf')

def makeDestinations():
    destinations = [EADdestination, PDFdestination, METSdestination]
    for d in destinations:
        if not os.path.exists(d):
            os.makedirs(d)

# authenticates the session
def authenticate():
    try:
        auth = requests.post('{baseURL}/users/{user}/login?password={password}&expiring=false'.format(**dictionary)).json()
        token = {'X-ArchivesSpace-Session':auth["session"]}
        return token
    except ConnectionError:
        logging.error('Authentication failed!')

# logs out non-expiring session (not yet in AS core, so commented out)
def logout(headers):
    requests.post('{baseURL}/logout'.format(**dictionary), headers=headers)
    logging.info('You have been logged out of your session')

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
def updateTime(exportStartTime):
    with open(lastExportFilepath, 'wb') as pickle_handle:
        pickle.dump(exportStartTime, pickle_handle)

# formats XML files
def prettyPrintXml(filePath, resourceID):
    assert filePath is not None
    parser = etree.XMLParser(resolve_entities=False, strip_cdata=False, remove_blank_text=True)
    try:
        etree.parse(filePath, parser)
        document = etree.parse(filePath, parser)
        document.write(filePath, pretty_print=True, encoding='utf-8')
        createPDF(resourceID)
    except:
        logging.warning('%s is invalid and will be removed', resourceID)
        #removeEAD(resourceID)

# creates pdf from EAD
def createPDF(resourceID):
    if not os.path.exists(os.path.join(PDFdestination,resourceID)):
        os.makedirs(os.path.join(PDFdestination,resourceID))
    subprocess.call(['java', '-jar', PDFConvertFilepath, os.path.join(EADdestination, resourceID, resourceID+'.xml'), os.path.join(PDFdestination, resourceID, resourceID+'.pdf')])
    logging.info('%s.pdf created at %s', resourceID, os.path.join(PDFdestination,resourceID))

# Exports EAD file
def exportEAD(resourceID, identifier, headers):
    ead = requests.get(repositoryBaseURL+'resource_descriptions/'+str(identifier)+'.xml?include_unpublished={exportUnpublished}&include_daos={exportDaos}&numbered_cs={exportNumbered}&print_pdf={exportPdf}'.format(exportUnpublished=exportUnpublished, exportDaos=exportDaos, exportNumbered=exportNumbered, exportPdf=exportPdf), headers=headers, stream=True)
    if not os.path.exists(os.path.join(EADdestination,resourceID)):
        os.makedirs(os.path.join(EADdestination,resourceID))
    with open(os.path.join(EADdestination,resourceID,resourceID+'.xml'), 'wb') as f:
        for chunk in ead.iter_content(10240):
            f.write(chunk)
    f.close
    logging.info('%s.xml exported to %s', resourceID, os.path.join(EADdestination,resourceID))
    #validate here
    prettyPrintXml(os.path.join(EADdestination,resourceID,resourceID+'.xml'), resourceID)

# Exports METS file
def exportMETS(doID, headers):
    mets = requests.get(repositoryBaseURL+'digital_objects/mets/'+str(doID)+'.xml', headers=headers).text
    if not os.path.exists(os.path.join(METSdestination,doID)):
        os.makedirs(os.path.join(METSdestination,doID))
    f = open(os.path.join(METSdestination,doID,doID+'.xml'), 'w')
    f.write(mets.encode('utf-8'))
    f.close
    logging.info('%s.xml exported to %s', doID, os.path.join(METSdestination,doID))
    #validate here

# Deletes EAD file if it exists
def removeEAD(resourceID):
    if os.path.isfile(os.path.join(EADdestination,resourceID,resourceID+'.xml')):
        os.remove(os.path.join(EADdestination,resourceID,resourceID+'.xml'))
        os.rmdir(os.path.join(EADdestination,resourceID))
        logging.info('%s.xml deleted from %s%s', resourceID, EADdestination, resourceID)
    else:
        logging.info('%s.xml does not already exist, no need to delete', resourceID)

# Deletes METS file if it exists
def removeMETS(doID):
    if os.path.isfile(os.path.join(METSdestination,doID,doID+'.xml')):
        os.remove(os.path.join(METSdestination,doID,doID+'.xml'))
        os.rmdir(os.path.join(METSdestination,doID))
        logging.info('%s.xml deleted from %s%s', doID, METSdestination, doID)
    else:
        logging.info('%s.xml does not exist, no need to delete', doID)

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
    try:
        digital_object["publish"]
        exportMETS(doID, headers)
        doExportList.append(digital_object["uri"])
    except:
        removeMETS(doID)
        doDeleteList.append(digital_object["uri"])

def handleAssociatedDigitalObject(digital_object, headers):
    doID = digital_object["digital_object_id"]
    try:
        digital_object["publish"]
        component = (requests.get(baseURL + digital_object["linked_instances"][0]["ref"], headers=headers)).json()
        if component["jsonmodel_type"] == 'resource':
            resource = digital_object["linked_instances"][0]["ref"]
        else:
            resource = component["resource"]["ref"]
        if resource in uriExportList:
            exportMETS(doID, headers)
            doExportList.append(digital_object["uri"])
        elif resource in uriDeleteList:
            removeMETS(doID)
            doDeleteList.append(digital_object["uri"])
    except:
        removeMETS(doID)
        doDeleteList.append(digital_object["uri"])

# Looks for updated resources
def findUpdatedResources(lastExport, headers):
    resourceIds = requests.get(repositoryBaseURL+'resources?all_ids=true&modified_since='+str(lastExport), headers=headers)
    logging.info('*** Checking resources ***')
    for r in resourceIds.json():
        resource = (requests.get(repositoryBaseURL+'resources/' + str(r), headers=headers)).json()
        handleResource(resource, headers)

# Looks for updated components
def findUpdatedObjects(lastExport, headers):
    archival_objects = requests.get(repositoryBaseURL+'archival_objects?all_ids=true&modified_since='+str(lastExport), headers=headers)
    logging.info('*** Checking archival objects ***')
    for a in archival_objects.json():
        archival_object = requests.get(repositoryBaseURL+'archival_objects/'+str(a), headers=headers).json()
        resource = (requests.get(baseURL+archival_object["resource"]["ref"], headers=headers)).json()
        if not resource["uri"] in uriExportList and not resource["uri"] in uriDeleteList:
            handleResource(resource, headers)

# Looks for updated digital objects
def findUpdatedDigitalObjects(lastExport, headers):
    doIds = requests.get(repositoryBaseURL+'digital_objects?all_ids=true&modified_since='.format(**dictionary)+str(lastExport), headers=headers)
    logging.info('*** Checking digital objects ***')
    for d in doIds.json():
        digital_object = (requests.get(repositoryBaseURL+'digital_objects/' + str(d), headers=headers)).json()
        handleDigitalObject(digital_object, headers)

# Looks for digital objects associated with updated resource records
def findAssociatedDigitalObjects(headers):
    doIds = requests.get(repositoryBaseURL+'digital_objects?all_ids=true', headers=headers)
    logging.info('*** Checking associated digital objects ***')
    for d in doIds.json():
        digital_object = (requests.get(repositoryBaseURL+'digital_objects/' + str(d), headers=headers)).json()
        handleAssociatedDigitalObject(digital_object, headers)

#run script to version using git
def versionFiles():
    logging.info('*** Versioning files and pushing to Github ***')
    destinations = [dataDestination, PDFdestination]
    for d in destinations:
        os.system("./gitVersion.sh "+d)

def main():
    logging.info('=========================================')
    logging.info('*** Export started ***')
    exportStartTime = int(time.time())
    lastExport = readTime()
    makeDestinations()
    headers = authenticate()
    findUpdatedResources(lastExport, headers)
    findUpdatedObjects(lastExport, headers)
    findUpdatedDigitalObjects(lastExport, headers)
    if len(uriExportList) > 0 or len(uriDeleteList):
        findAssociatedDigitalObjects(headers)
    #versionFiles()
    logging.info('*** Export completed ***')
    #logout(headers)
    updateTime(exportStartTime)

main()
