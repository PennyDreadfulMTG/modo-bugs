// This is the hourly cron script that Jenkins will execute.
node('linux') {
    stage('checkout'){
        checkout([$class: 'GitSCM', branches: [[name: '*/master']], doGenerateSubmoduleConfigurations: false, extensions: [], submoduleCfg: [], userRemoteConfigs: [[credentialsId: '61235359-4c9e-4d64-b63a-7717e51f3069', url: 'https://github.com/PennyDreadfulMTG/Penny-Dreadful-Tools.git']]])
    }

    stage('setup') {
        sh 'python3 -m pip install --user -r requirements.txt'
        withCredentials([usernamePassword(credentialsId: 'd61f34a1-4929-406d-b4c5-ec380d823780', passwordVariable: 'github_password', usernameVariable: 'github_user')]) {
            sh 'python3 run.py modo_bugs init'
            dir('modo_bugs_repo') {
                sh 'git config user.email "jenkins@katelyngigante.com"'
                sh 'git config user.name "Vorpal Buildbot"'
                sh 'git checkout master'
                sh 'git pull'
            }
        }
    }
    stage('Scrape') {
        withCredentials([usernamePassword(credentialsId: 'd61f34a1-4929-406d-b4c5-ec380d823780', passwordVariable: 'github_password', usernameVariable: 'github_user'), usernamePassword(credentialsId: 'modo_bugs_webhook_id_and_token', passwordVariable: 'bugs_webhook_token', usernameVariable: 'bugs_webhook_id')]) {
            sh returnStatus: true, script: 'python3 run.py modo_bugs scrape'
        }
    }
    stage('Update'){
        withCredentials([usernamePassword(credentialsId: 'd61f34a1-4929-406d-b4c5-ec380d823780', passwordVariable: 'github_password', usernameVariable: 'github_user')]) {
            sh 'python3 run.py modo_bugs update'
        }
    }
    stage('Verification') {
        withCredentials([usernamePassword(credentialsId: 'd61f34a1-4929-406d-b4c5-ec380d823780', passwordVariable: 'github_password', usernameVariable: 'github_user')]) {
            sh returnStatus: true, script: 'python3 run.py modo_bugs verify'
        }
    }
    stage('Push changes'){
        dir('modo_bugs_repo') {
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
}
