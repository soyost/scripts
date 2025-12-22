#!/bin/bash
user=$USER
pwd=$(pwd)
number=$(ls -al | wc -l | xargs)
processes=$(ps aux | wc -l | xargs)
echo "Hello,$user you are currently in $pwd which has $number files." 
echo "There are $processes processes running $(hostname -s)"