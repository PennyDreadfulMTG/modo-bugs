// This is the hourly cron script that Jenkins will execute.
node {
    stage('checkout'){
        checkout([$class: 'GitSCM', branches: [[name: '*/master']], doGenerateSubmoduleConfigurations: false, extensions: [], submoduleCfg: [], userRemoteConfigs: [[credentialsId: '61235359-4c9e-4d64-b63a-7717e51f3069', url: 'https://github.com/PennyDreadfulMTG/modo-bugs.git']]])
    }
    stage('build') {
        sh 'python3 -m pip install --user -r requirements.txt'
        withCredentials([usernamePassword(credentialsId: '739d1f57-8568-4f0b-9d6c-e00cfcbb0c29', passwordVariable: 'github_password', usernameVariable: 'github_user')]) {
            sh 'git config user.email "jenkins@katelyngigante.com"'
            sh 'git config user.name "Vorpal Buildbot"'
            sh 'git checkout master'
            sh 'git pull'
            sh 'python3 scrape_bugblog.py'
            sh 'python3 update.py'
            def updated = sh returnStatus: true, script: 'git diff --exit-code'
            if (updated){
                sh 'git commit -a -m "Updated Bug List from Issues"'
            }
            sh 'git push https://$github_user:$github_password@github.com/PennyDreadfulMTG/modo-bugs.git'
        }
    }
}