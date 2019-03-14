pipeline {
  agent any
      steps {
        sh 'docker build -t richardx/python-35-centos:1.0 -f ./docker/docker-python/Dockerfile .'
      }  stages {
    stage('Build Docker images') {
      agent any
      }

    }
  }
