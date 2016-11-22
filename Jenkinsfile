elifePipeline {
    stage 'Checkout'
    checkout scm
    def commit = elifeGitRevision()
 
    stage 'Project tests'
    lock('lax--ci') {
        builderDeployRevision 'lax--ci', commit
        builderProjectTests 'lax--ci', '/srv/lax', ['/srv/lax/build/junit.xml']
    }
    
    elifeMainlineOnly {
        stage 'End2end tests'
        elifeEnd2EndTest {
            builderDeployRevision 'lax--end2end', commit
            builderSmokeTests 'lax--end2end', '/srv/lax'
        }
     
        stage 'Approval'
        elifeGitMoveToBranch commit, 'approved'
    }
}
