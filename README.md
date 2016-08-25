#Automated exports for ArchivesSpace
These scripts export updated data from ArchivesSpace and version all data in git.

##Dependencies

*   [Python 2.7 or higher](https://www.python.org/) Make sure you install the correct version. On some operating systems, this may require additional steps. It is also helpful to have [pip](https://pypi.python.org/pypi/pip) installed.
*   [lxml](http://lxml.de/)
*   [requests](http://www.python-requests.org/en/latest/)
*   [requests_toolbelt](https://github.com/sigmavirus24/requests-toolbelt)
*   [psutil](https://github.com/giampaolo/psutil)
*   [gittle](https://github.com/FriendCode/gittle)
*   [git](https://git-scm.com/)

##Getting Started

1.  Install dependencies
2.  Get a copy of the repo

        git clone git@github.com:RockefellerArchiveCenter/asExportIncremental.git

    or just download the zip file of this repo
3.  Create a local configuration file named `local_settings.cfg` in the same directory as the script and add variables. A sample file looks like this:

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

        [MODSexport]
        # EAD to MODS XSL filepath
        filepath:eadToMods.xsl

        [Git]
        dataRemote:git@github.com:username/repository.git
        PDFRemote:git@github.com:username/repository.git

        [Logging]
        filename:log.txt
        format: %(asctime)s %(message)s
        datefmt: %m/%d/%Y %I:%M:%S %p
        level: WARNING

        [Destinations]
        dataDestination = /exports/data
        EADdestination = /exports/data/ead
        METSdestination = /exports/data/mets
        MODSdestination = /exports/data/mods
        PDFdestination = /exports/pdf

4.  Set up repositories

    * [Create local git repositories](https://git-scm.com/book/en/v2/Git-Basics-Getting-a-Git-Repository) at your data export locations

          git init

    * Create [Github](http://github.com) repositories to push to
    * [Add a remote](http://git-scm.com/docs/git-remote) named `github` in each of your local repositories pointing to the appropriate Github repository

          git remote add github git@github.com:YourGithubAccount/YourRepo.git

    * [Create](https://help.github.com/articles/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent/) (if necessary) and [add your SSH key](https://help.github.com/articles/adding-a-new-ssh-key-to-your-github-account/) to Github
    * Make sure your Github username and email are correctly configured on the server

          git config --global user.name "Your Name"
          git config --global user.email you@example.com

5.  Set a cron job to run asExportIncremental.py at an interval of your choice. This should be done in the crontab of the user who's SSH key has been added to Github.

The first time you run this, the script may take some time to execute, since it will attempt to export all published resource records in your ArchivesSpace repository. If you ever want to do a complete export, simply delete the Pickle file specified in `lastExportFilepath` and the `lastExport` variable will be set to zero (i.e. the epoch, which was long before ArchivesSpace was a twinkle in [anarchivist's](https://github.com/anarchivist) eye).

##Optional arguments
The script supports a few arguments, which will include or exclude specific functions.

`--update_time` updates last exported time stored in external file to current time. Useful when you want to avoid exporting everything after you re-sequence your AS instance.

`--archival` exports EAD for all resource records whose id_0 does not start with 'LI', regardless of when those resources were last updated. When this argument is used, the script does not update the last run time.

`--library` exports MODS for all resource records whose id_0 starts with 'LI', regardless of when those resources were last updated. When this argument is used, the script does not update the last run time.

`--digital` exports METS for all digital object records, regardless of when those resources were last updated. When this argument is used, the script does not update the last run time.

`--digital --resource %identifier%` exports METS digital object records associated with the the resource record whose id_0 matches %identifier%, regardless of when those records were last updated. When this argument is used, the script does not update the last run time.

`--resource %identifier%` exports EAD for the resource record whose `id_0` contains `%identifier%`, regardless of when those resources were last updated. This argument supports partial matches, for example if `FA00` is entered as the identifier, any resources whose `id_0` contains `FA00` would be exported, including for example `FA001`, `FA002` or `xFA001`. When this argument is used, the script does not update the last run time.

##What's here

###asExportIncremental.py
Exports EAD files from published resource records updated since last export (including updates to any child components or associated agents and subjects), as well as METS records for digital object records associated with those resource records. If a resource record is unpublished, this script will remove the EAD, PDF and any associated METS records. Exported or deleted files are logged to a text file `log.txt`. (Python)

###ead2pdf.jar
Creates PDFs from an EAD file, forked from [ead2pdf](http://github.com/archivesspace/ead2pdf/) which includes the [Rockefeller Archive Center](https://github.com/RockefellerArchiveCenter) logo. You may want to replace this file and recompile the .jar for your local institution. (Java)
