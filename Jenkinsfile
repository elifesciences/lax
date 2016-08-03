elifePipeline {
    stage 'Checkout'
    checkout scm
    def commit = elifeGitRevision()
 
    stage 'Project tests'
    builderDeployRevision 'lax--ci', commit
    def testArtifact = "${env.BUILD_TAG}.junit.xml"
    builderProjectTests 'lax--ci', '/srv/lax'
    builderTestArtifact testArtifact, 'lax--ci', '/srv/lax/build/junit.xml'
    elifeVerifyJunitXml testArtifact
    
    stage 'End2end tests'
    elifeEnd2EndTest {
        elifeSwitchRevision 'elife-lax-develop--end2end', commit
    }
 
    stage 'Approval'
    elifeGitMoveToBranch commit, 'approved'
}
