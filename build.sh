#!/bin/sh
RELEASE="1.0"

#PLATFORM="linux & win64"
#PYINSTALLER_IMG_VERSION="1.0"
cd src
num=`echo ${PLATFORM} | grep linux | wc -l`
if [ $num == 1 ]; then
  DOCKER_IMG="richardx/pyinstaller-34-linux:${PYINSTALLER_IMG_VERSION}"

  num_img=`docker images -q ${DOCKER_IMG} | wc -l`
  if [ $num_img == 0 ]; then
    docker pull ${DOCKER_IMG}
  fi

  for i in `ls *.py`
  do
    docker run -v "$(pwd):/src/" docker.io/${DOCKER_IMG} "pyinstaller --onefile --clean $i"
  done
fi

num=`echo ${PLATFORM} | grep win64 | wc -l`
if [ $num == 1 ]; then
  DOCKER_IMG="richardx/pyinstaller-34-win64:${PYINSTALLER_IMG_VERSION}"

  num_img=`docker images -q ${DOCKER_IMG} | wc -l`
  if [ $num_img == 0 ]; then
    docker pull ${DOCKER_IMG}
  fi
  
  for i in `ls *.py`
  do
    docker run -v "$(pwd):/src/" docker.io/${DOCKER_IMG} "pyinstaller --onefile --clean $i"
  done
fi

# Remove docker image from local
