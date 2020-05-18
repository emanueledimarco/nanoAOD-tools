#!/bin/csh

# Please setup python 2.7 and ROOT into your environment first

set CWD=$PWD
cd $PWD

if ( -f standalone/env_standalone.csh ) then
    if ( ! -d build ) then
	if ( x$argv[1] == 'xbuild' ) then
            mkdir -p build/lib/python/PhysicsTools
            ln -s ../../../../python build/lib/python/PhysicsTools/NanoAODTools
	    echo "Build directory created, please source again standalone/env_standalone.csh without the build argument."
	else
	    echo "Build directory is not yet present, please source again standalone/env_standalone.csh with the build argument."
	endif
    else
	find build/lib/python python -type d -execdir touch '{}/__init__.py' \;
	setenv NANOAODTOOLS_BASE $PWD
	setenv PYTHONPATH $NANOAODTOOLS_BASE/build/lib/python:$PYTHON27PATH
            
	echo "Standalone environment set."
    endif
    cd $CWD
else
    echo "Error in moving to the NanoAODTools directory to setup the standalone environment"
    cd $CWD
endif


