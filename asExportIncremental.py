#!/usr/bin/env python

import os, requests, json, sys, time, pickle, logging
from lxml import etree

# the base URL of your ArchivesSpace installation
baseURL = 'http://localhost:8089'
# the id of your repository
repository = '2'
# the username to authenticate with
user = 'admin'
# the password for the username above
password = 'admin'
# export destinations, should end with a trailing slash
dataDestination = '/Users/harnold/Desktop/data/'
EADdestination = dataDestination + 'ead/'
METSdestination = dataDestination + 'mets/'
PDFdestination = '/Users/harnold/Desktop/pdf/'
# EAD Export options
exportUnpublished = 'false'
exportDaos = 'true'
exportNumbered = 'false'
exportPdf = 'false'
# URI lists (to be populated by URIs of exported or deleted resource records)
uriExportList = []
uriDeleteList = []
# stores a variable for the last time this script was run
lastExportFilepath = 'lastExport.pickle'
# PDF export utility filePath
PDFConvertFilepath = 'ead2pdf.jar'
# logging configs
logging.basicConfig(filename='log.txt',format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.WARNING)

def makeDestinations():
    destinations = [EADdestination, PDFdestination, METSdestination]
    for d in destinations:
        if not os.path.exists(d):
            os.makedirs(d)

# authenticates the session
def authenticate():
    try:
        auth = requests.post(baseURL + '/users/'+user+'/login?password='+password).json()
        token = {'X-ArchivesSpace-Session':auth["session"]}
        return token
    except:
        logging.error('Authentication failed!')

# gets time of last export
def handleTime():
    # last export time in Unix epoch time, for example 1439563523
    if os.path.isfile(lastExportFilepath):
        with open(lastExportFilepath, 'rb') as pickle_handle:
            lastExport = str(pickle.load(pickle_handle))
    else:
        lastExport = 0
    # store the current time in Unix epoch time, for example 1439563523
    with open(lastExportFilepath, 'wb') as pickle_handle:
        pickle.dump(int(time.time()), pickle_handle)
    return lastExport

# formats XML files
def prettyPrintXml(filePath, resourceID, id):
    assert filePath is not None
    parser = etree.XMLParser(resolve_entities=False, strip_cdata=False, remove_blank_text=True)
    try:
        etree.parse(filePath, parser)
        document = etree.parse(filePath, parser)
        document.write(filePath, pretty_print=True, encoding='utf-8')
        createPDF(resourceID)
    except:
        logging.warning('%s is invalid and should be removed', resourceID)
        #removeEAD(resourceID, id)

# creates pdf from EAD
def createPDF(resourceID):
    if not os.path.exists(PDFdestination+resourceID):
        os.makedirs(PDFdestination+resourceID)
    os.system("java -jar "+PDFConvertFilepath+" "+EADdestination+resourceID+'/'+resourceID+'.xml'+" "+PDFdestination+resourceID+'/'+resourceID+'.pdf')
    logging.warning('%s%s/%s.pdf created', PDFdestination, resourceID, resourceID)

# Exports EAD file
def exportEAD(resourceID, id, headers):
    ead = requests.get(baseURL + '/repositories/'+repository+'/resource_descriptions/'+str(id)+'.xml?include_unpublished='+exportUnpublished+'&include_daos='+exportDaos+'&numbered_cs='+exportNumbered+'&print_pdf='+exportPdf, headers=headers, stream=True)
    if not os.path.exists(EADdestination+resourceID+'/'):
        os.makedirs(EADdestination + resourceID+'/')
    with open(EADdestination+resourceID+'/'+resourceID+'.xml', 'wb') as f:
        for chunk in ead.iter_content(10240):
            f.write(chunk)
    f.close
    logging.warning('%s exported to %s', resourceID, EADdestination)
    #validate here
    prettyPrintXml(EADdestination+resourceID+'/'+resourceID+'.xml', resourceID, id)

# Exports METS file
def exportMETS(doID, headers):
    mets = requests.get(baseURL + '/repositories/'+repository+'/digital_objects/mets/'+str(id)+'.xml', headers=headers).text
    if not os.path.exists(METSdestination+doID+'/'):
        os.makedirs(METSdestination+doID+'/')
    f = open(METSdestination+doID+'/'+doID+'.xml', 'w')
    f.write(mets.encode('utf-8'))
    f.close
    logging.warning('%s exported to %s', doID, METSdestination)
    #validate here

# Deletes EAD file if it exists
def removeEAD(resourceID, id):
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
    identifier = resource["uri"].split('/repositories/'+repository+'/resources/',1)[1]
    if resource["publish"] and not ('LI' in resourceID):
        exportEAD(resourceID, identifier, headers)
        uriExportList.append(resource["uri"])
    else:
        removeEAD(resourceID, identifier)
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
def checkResources(lastExport):
    headers = authenticate()
    resourceIds = requests.get(baseURL + '/repositories/'+repository+'/resources?all_ids=true&modified_since='+str(lastExport), headers=headers)
    logging.warning('*** Checking resources ***')
    for id in resourceIds.json():
        if not requests.get(baseURL + '/repositories/'+repository+'/resources/' + str(id), headers=headers):
            headers = authenticate()
        resource = (requests.get(baseURL + '/repositories/'+repository+'/resources/' + str(id), headers=headers)).json()
        handleResource(resource, headers)

# Looks for updated components
def checkObjects(lastExport):
    headers = authenticate()
    archival_objects = requests.get(baseURL + '/repositories/'+repository+'/archival_objects?all_ids=true&modified_since='+str(lastExport), headers=headers)
    logging.warning('*** Checking archival objects ***')
    for id in archival_objects.json():
        if not requests.get(baseURL + '/repositories/'+repository+'/archival_objects/'+str(id), headers=headers):
            headers = authenticate()
        archival_object = requests.get(baseURL + '/repositories/'+repository+'/archival_objects/'+str(id), headers=headers).json()
        resource = (requests.get(baseURL +archival_object["resource"]["ref"], headers=headers)).json()
        if not resource["uri"] in uriExportList and not resource["uri"] in uriDeleteList:
            handleResource(resource, headers)

# Looks for updated digital objects
def checkDigital(lastExport):
    headers = authenticate()
    doIds = requests.get(baseURL + '/repositories/'+repository+'/digital_objects?all_ids=true&modified_since='+str(lastExport), headers=headers)
    logging.warning('*** Checking digital objects ***')
    for id in doIds.json():
        if not requests.get(baseURL + '/repositories/'+repository+'/digital_objects/' + str(id), headers=headers):
            headers = authenticate()
        digital_object = (requests.get(baseURL + '/repositories/'+repository+'/digital_objects/' + str(id), headers=headers)).json()
        handleDigitalObject(digital_object, headers)

# Looks for digital objects associated with updated resource records
def associatedDigital():
    headers = authenticate()
    doIds = requests.get(baseURL + '/repositories/'+repository+'/digital_objects?all_ids=true', headers=headers)
    logging.warning('*** Checking associated digital objects ***')
    for id in doIds.json():
        if not requests.get(baseURL + '/repositories/'+repository+'/digital_objects/' + str(id), headers=headers):
            headers = authenticate()
        digital_object = (requests.get(baseURL + '/repositories/'+repository+'/digital_objects/' + str(id), headers=headers)).json()
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
    lastExport = handleTime()
    makeDestinations()
    checkResources(lastExport)
    checkObjects(lastExport)
    checkDigital(lastExport)
    if len(uriExportList) > 0 or len(uriDeleteList) > 0:
        associatedDigital()
    else:
        logging.warning('*** Nothing was exported ***')
    versionFiles()
    logging.warning('*** Export completed ***')

main()
