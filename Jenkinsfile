pipeline {
    agent any

    //have to run job once manually before cron kicks in
    triggers {
        cron 'H 0 * * *'
    }

    environment {
        test_env = "TEST_VALUE"
        //would have to configure these in jenkins credential section
        //AWS_ACCESS_KEY_ID     = credentials('jenkins-aws-secret-key-id')
        //AWS_SECRET_ACCESS_KEY = credentials('jenkins-aws-secret-access-key')
    }
    //only keeps last 3 builds
    options {
        preserveStashes(buildCount: 3)
    }
    stages {
        stage('Build') {
            steps {
                //can use snippet generator to make one giant withCredentials method , must be set for every stage
                withCredentials(bindings: [certificate(credentialsId: 'jenkins-certificate-for-xyz', \
                                                       keystoreVariable: 'CERTIFICATE_FOR_XYZ', \
                                                       passwordVariable: 'XYZ-CERTIFICATE-PASSWORD')]) {
                  //
                }
                echo 'Building..'
            }
        }
        stage('Test') {
            steps {
                echo 'Testing..'
            }
        }
        stage('Deploy') {
            steps {
                echo 'Deploying....'
            }
        }
    }
}
