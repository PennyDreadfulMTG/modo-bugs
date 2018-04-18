// This is the hourly cron script that Jenkins will execute.
node('linux') {
    stage('checkout'){
        checkout([$class: 'GitSCM', branches: [[name: '*/master']], doGenerateSubmoduleConfigurations: false, extensions: [], submoduleCfg: [], userRemoteConfigs: [[credentialsId: '61235359-4c9e-4d64-b63a-7717e51f3069', url: 'https://github.com/PennyDreadfulMTG/modo-bugs.git']]])
    }
    stage('setup') {
        withCredentials([usernamePassword(credentialsId: 'd61f34a1-4929-406d-b4c5-ec380d823780', passwordVariable: 'github_password', usernameVariable: 'github_user')]) {
        sh 'git config user.email "jenkins@katelyngigante.com"'
        sh 'git config user.name "Vorpal Buildbot"'
        sh 'git checkout master'
        sh 'git pull'
        sh 'python3 -m pip install --user pipenv'
        sh 'pipenv install'
        }
    }
    stage('Scrape') {
        withCredentials([usernamePassword(credentialsId: 'd61f34a1-4929-406d-b4c5-ec380d823780', passwordVariable: 'github_password', usernameVariable: 'github_user')]) {
            sh returnStatus: true, script: 'pipenv run python scrape_bugblog.py'
        }
    }
    stage('Update'){
        sh 'pipenv run python update.py'
    }
    stage('Verification') {
        withCredentials([usernamePassword(credentialsId: 'd61f34a1-4929-406d-b4c5-ec380d823780', passwordVariable: 'github_password', usernameVariable: 'github_user')]) {
            sh returnStatus: true, script: 'pipenv run python verification.py'
        }
    }
    stage('Push changes'){
        def updated = sh returnStatus: true, script: 'git diff --exit-code'
        if (updated){
            sh 'git commit -a -m "Updated Bug List from Issues"'
            sh 'git pull'
        }
        withCredentials([usernamePassword(credentialsId: 'd61f34a1-4929-406d-b4c5-ec380d823780', passwordVariable: 'github_password', usernameVariable: 'github_user')]) {
            sh 'git push https://$github_user:$github_password@github.com/PennyDreadfulMTG/modo-bugs.git'
        }
    }
}
