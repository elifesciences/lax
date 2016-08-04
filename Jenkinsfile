elifePipeline {
    stage 'Checkout'
    checkout scm
    def commit = elifeGitRevision()
 
    stage 'Project tests'
    lock('lax--ci') {
        builderDeployRevision 'lax--ci', commit
        def testArtifact = "${env.BUILD_TAG}.junit.xml"
        builderProjectTests 'lax--ci', '/srv/lax'
        builderTestArtifact testArtifact, 'lax--ci', '/srv/lax/build/junit.xml'
        elifeVerifyJunitXml testArtifact
    }
    
    elifeMainlineOnly {
        stage 'End2end tests'
        elifeEnd2EndTest {
            builderDeployRevision 'lax--end2end', commit
        }
     
        stage 'Approval'
        elifeGitMoveToBranch commit, 'approved'
    }
}
