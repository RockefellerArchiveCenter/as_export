#!/bin/bash

#location of local git repository for exported files
repo=????
#the remote repository to push to
remote=github
#the branch of the remote repository to push to
branch=master

if cd $repo
  then
  git add .
  git commit -m 'automated commit'
  git push $remote $branch;
fi
