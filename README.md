#Automated exports for ArchivesSpace
These scripts export updated data from ArchivesSpace and version all data in git.

##Dependencies
* [Python](https://www.python.org/) - tested on 2.7 but will probably work with other versions
* [lxml](http://lxml.de/)
* [requests](http://www.python-requests.org/en/latest/)
* [git](https://git-scm.com/)

##Getting Started
1.  Get a copy of the repo

        git clone git@github.com:RockefellerArchiveCenter/asExportIncremental.git

    or just download the zip file of this repo
2.  Update variables in asExportIncremental.py
    ArchivesSpace variables, including URL, repository, username and password
    Export destinations: point these to where you want your exported data to go
3.  Set up repositories
    Install [git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
    [Create local git repositories](https://git-scm.com/book/en/v2/Git-Basics-Getting-a-Git-Repository) at your data export locations
    Create [Github](http://github.com) repositories to push to
    [Add a remote](http://git-scm.com/docs/git-remote) in each of your local repositories pointing to the appropriate Github repository
4.  Update variables in gitVersion.sh
    `remote` should match the name of your remote github repository
    `branch` should match the name of the [branch]() you want to push to in your remote repository
5.  Set a cron job to run asExportIncremental.py at an interval of your choice

The first time you run this, the script may take some time to execute, since it will attempt to export all published resource records in your ArchivesSpace repository. If you ever want to do a complete export, simply delete the Pickle file specified in `lastExportFilepath` and the `lastExport` variable will be set to zero (i.e. the epoch, which was long before ArchivesSpace was a twinkle in [anarchivist's](https://github.com/anarchivist) eye).

##What's here

###asExportIncremental.py
Exports EAD files from published resource records updated since last export (including updates to any child components or associated agents and subjects), as well as METS records for digital object records associated with those resource records. If a resource record is unpublished, this script will remove the EAD, PDF and any associated METS records. Exported or deleted files are logged to a text file `log.txt`. (Python)

###gitVersion.sh
Versions a local git repository and pushes commits to a remote repository. (Bash)

###ead2pdf.jar
Creates PDFs from an EAD file, forked from [ead2pdf](http://github.com/archivesspace/ead2pdf/) which includes the [Rockefeller Archive Center](https://github.com/RockefellerArchiveCenter) logo. You may want to replace this file and recompile the .jar for your local institution. (Java)
