# as_export
A script to automate and version the export of updated data from ArchivesSpace.

## Dependencies

*   [Python 3.4 or higher](https://www.python.org/) Make sure you install the correct version. On some operating systems, this may require additional steps. It is also helpful to have [pip](https://pypi.python.org/pypi/pip) installed.
*   [ArchivesSnake](https://github.com/archivesspace-labs/ArchivesSnake/)
*   [requests_toolbelt](https://github.com/sigmavirus24/requests-toolbelt)
*   [git](https://git-scm.com/)

## Getting Started

1.  Install dependencies
2.  Get a copy of the repo

        git clone git@github.com:RockefellerArchiveCenter/as_export.git

    or just download the zip file of this repo
3.  Create a local configuration file named `local_settings.cfg` in the same directory as the script and add variables. A sample file looks like this:

        [ARCHIVESSPACE]
        baseurl:http://localhost:8089
        repository:2
        user:admin
        password:admin

        [EAD]
        unpublished:false
        daos:true
        numbered:false

        [LAST_EXPORT]
        filepath:last_export.txt

        [DESTINATIONS]
        data = data
        ead = ead
        mets = mets

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

5.  Set a cron job to run `as_export.py` at an interval of your choice. This should be done in the crontab of the user whose SSH key has been added to Github.

The first time you run this, the script may take some time to execute, since it will attempt to export all published resource records in your ArchivesSpace repository. If you ever want to do a complete export, simply delete `last_export.txt` and the `last_export` variable will be set to zero (i.e. the epoch, which was long before ArchivesSpace or any of the resources in it existed).

## Optional arguments
The script supports a few arguments, which will include or exclude specific functions. These arguments are also available via the command line by typing `as_export -h`.

`--update_time` updates last exported time stored in external file to current time. Useful when you want to avoid exporting everything after you've run reindexing when migrating to a new version.

`--digital` exports METS for all digital object records, regardless of when those resources were last updated. When this argument is used, the script does not update the last run time.

`--resource %identifier%` exports EAD for a specific resource record matching the ArchivesSpace  `%identifier%`, regardless of when that resource was last updated. When this argument is used, the script does not update the last run time.

`--resource_digital %identifier%` exports METS digital object records associated with the the resource record matching the ArchivesSpace %identifier%, regardless of when those records were last updated. When this argument is used, the script does not update the last run time.


## What's here

### as_export.py
Exports EAD files from published resource records updated since last export (including updates to any child components or associated agents and subjects), as well as METS records for digital object records associated with those resource records. If a resource record is unpublished, this script will remove the EAD, PDF and any associated METS records. Exported or deleted files are logged to a text file `log.txt`. (Python)

## Development
This repository contains a configuration file for git [pre-commit](https://pre-commit.com/) hooks which help ensure that code is linted before it is checked into version control. It is strongly recommended that you install these hooks locally by installing pre-commit and running `pre-commit install`.

## License
This code is released under the MIT License. See `LICENSE.md` for more information.
