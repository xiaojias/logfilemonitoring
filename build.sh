#!/bin/sh
RELEASE="1.0"

#PLATFORM="linux & win64"
#PYINSTALLER_IMG_VERSION="1.0"
num=`echo ${PLATFORM} | grep linux | wc -l`
if [ $num == 1 ]; then
  for i in `ls ./src/*.py`
  do
    docker run -v "$(pwd)/src:/src/" richardx/pyinstaller-34-linux:${PYINSTALLER_IMG_VERSION} "pyinstaller --onefile --clean $i"
  done
fi

num=`echo ${PLATFORM} | grep win64 | wc -l`
if [ $num == 1 ]; then
  for i in `ls *.py`
  do
    docker run -v "$(pwd)/src:/src/" richardx/pyinstaller-34-win64:${PYINSTALLER_IMG_VERSION} "pyinstaller --onefile --clean $i"
  done
fi

# Remove docker image from local
