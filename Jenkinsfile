elifePipeline {
    def commit
    stage 'Checkout', {
        checkout scm
        commit = elifeGitRevision()
    }
 
    stage 'Project tests', {
        lock('lax--ci') {
            builderDeployRevision 'lax--ci', commit
            builderProjectTests 'lax--ci', '/srv/lax', ['/srv/lax/build/junit.xml']
        }
    }
    
    elifeMainlineOnly {
        stage 'End2end tests', {
            elifeSpectrum(
                deploy: [
                    stackname: 'lax--end2end',
                    revision: commit,
                    folder: '/srv/lax'
                ]
            )
        }

        stage 'Deploy on continuumtest', {
            lock('lax--continuumtest') {
                builderDeployRevision 'lax--continuumtest', commit
                builderSmokeTests 'lax--continuumtest', '/srv/lax'
            }
        }
     
        stage 'Approval', {
            elifeGitMoveToBranch commit, 'approved'
        }
    }
}
