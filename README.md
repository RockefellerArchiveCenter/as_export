#Automated exports for ArchivesSpace
These scripts export updated data from ArchivesSpace and version all data in git.

##Dependencies
* [Python](https://www.python.org/) - tested on 2.7 but will probably work with other versions
* [lxml](http://lxml.de/)
* [requests](http://www.python-requests.org/en/latest/)
* [requests_toolbelt](https://github.com/sigmavirus24/requests-toolbelt)
* [gittle] (https://github.com/FriendCode/gittle)
* [git](https://git-scm.com/)

##Getting Started
1.  Get a copy of the repo

        git clone git@github.com:RockefellerArchiveCenter/asExportIncremental.git

    or just download the zip file of this repo
2.  Create a local configuration file at `local_settings.cfg` and add variables. A sample file looks like this:

        [ArchivesSpace]
        baseURL:http://localhost:8089
        repository:2
        user:admin
        password:admin

        [EADexport]
        exportUnpublished:false
        exportDaos:true
        exportNumbered:false
        exportPdf:false

        [LastExport]
        filepath:lastExport.pickle

        [PDFexport]
        filepath:ead2pdf.jar

        [Git]
        dataRemote:git@github.com:username/repository.git
        PDFRemote:git@github.com:username/repository.git

        [Logging]
        filename:log.txt
        format: %(asctime)s %(message)s
        datefmt: %m/%d/%Y %I:%M:%S %p
        level: WARNING

3.  Set up repositories
    * Install [git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
    * [Create local git repositories](https://git-scm.com/book/en/v2/Git-Basics-Getting-a-Git-Repository) at your data export locations
    * Create [Github](http://github.com) repositories to push to
    * [Add a remote](http://git-scm.com/docs/git-remote) in each of your local repositories pointing to the appropriate Github repository

4.  Set a cron job to run asExportIncremental.py at an interval of your choice

The first time you run this, the script may take some time to execute, since it will attempt to export all published resource records in your ArchivesSpace repository. If you ever want to do a complete export, simply delete the Pickle file specified in `lastExportFilepath` and the `lastExport` variable will be set to zero (i.e. the epoch, which was long before ArchivesSpace was a twinkle in [anarchivist's](https://github.com/anarchivist) eye).

##What's here

###asExportIncremental.py
Exports EAD files from published resource records updated since last export (including updates to any child components or associated agents and subjects), as well as METS records for digital object records associated with those resource records. If a resource record is unpublished, this script will remove the EAD, PDF and any associated METS records. Exported or deleted files are logged to a text file `log.txt`. (Python)

###ead2pdf.jar
Creates PDFs from an EAD file, forked from [ead2pdf](http://github.com/archivesspace/ead2pdf/) which includes the [Rockefeller Archive Center](https://github.com/RockefellerArchiveCenter) logo. You may want to replace this file and recompile the .jar for your local institution. (Java)
