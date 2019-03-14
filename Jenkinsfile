pipeline {
  agent any
  stages {
    stage('Build Docker images') {
      agent any
      steps {
        sh 'python -m py_compile sources/add2vals.py sources/calc.py sources/LogfileMonitor.py'
      }
    }
  }
}
