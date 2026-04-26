#!/bin/bash

if [ $# -eq 1 ]; then
	PROG=$1
else 
	echo "Invalid usage"
	exit 0
fi

mkdir -p out 

python3 snipersim/run-sniper --sde-arch=future -d ./out  --roi $PROG 
