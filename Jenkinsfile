pipeline {
  agent {
    label 'aly'
  }
  stages {
    stage('Build Docker images') {
      agent any
      steps {
        sh 'docker build -t richardx/python-35-centos7:1.0 -f ./docker/docker-python/Dockerfile .'
        sh 'docker pull richardx/python-35-centos7:1.0'
      }
    }
  }
}
