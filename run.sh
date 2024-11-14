#!/bin/bash

pdm run api update $(test "$1" == '-a' && echo '-a') && pdm run api stats
