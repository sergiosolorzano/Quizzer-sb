#!/bin/bash

# Pull changes from the remote repository
git pull origin main

# Stage all changes for commit
git add .

# Commit the changes with a commit message
git commit -m "test"

# Push the committed changes to the remote repository
git push origin main
