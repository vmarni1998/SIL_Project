// =============================================================================
// Jenkinsfile  —  SIL Pipeline for Motor Speed Controller
// =============================================================================
//
// Trigger: Every Pull Request (via GitHub Branch Source or Multibranch Pipeline)
//
// Stages:
//   1. Checkout        — Clone the repo
//   2. Build           — CMake configure + compile shared library
//   3. Plant Self-Test — Verify the Python plant model runs cleanly
//   4. SIL Tests       — Run the full closed-loop test suite
//   5. Publish Results — Archive reports, show JUnit graphs in Jenkins
//   6. Notify          — (optional) update GitHub PR status
//
// Requirements on the Jenkins agent:
//   - cmake  >= 3.16
//   - gcc    (or clang) with C11 support
//   - python3 >= 3.8
//   - git
// =============================================================================

pipeline {

    // ── Run on any available agent ─────────────────────────────────────────
    // Replace 'any' with a label like 'linux-sil' if you have dedicated agents
    agent any

    // ── Environment variables available to all stages ──────────────────────
    environment {
        BUILD_DIR        = "build"
        TEST_DIR         = "tests"
        REPORT_DIR       = "tests"
        PYTHON           = "python3"   // change to 'python' on Windows agents
        CMAKE_BUILD_TYPE = "Debug"     // Debug enables extra -Wall/-Werror
    }

    // ── Pipeline-wide options ──────────────────────────────────────────────
    options {
        // Abort if the whole pipeline takes more than 30 minutes
        timeout(time: 30, unit: "MINUTES")

        // Keep last 10 builds with their artifacts (saves disk space)
        buildDiscarder(logRotator(numToKeepStr: "10"))

        // Colour ANSI codes in the Jenkins console log
        ansiColor("xterm")

        // Do not allow concurrent builds on the same branch
        disableConcurrentBuilds()

        // Show timestamps in console log
        timestamps()
    }

    // ── Triggers ───────────────────────────────────────────────────────────
    // When using GitHub Branch Source Plugin (Multibranch Pipeline),
    // PR triggers are configured in Jenkins, not here.
    // This section adds a fallback poll every 5 minutes.
    triggers {
        pollSCM("H/5 * * * *")
    }

    // ======================================================================
    // STAGES
    // ======================================================================
    stages {

        // ------------------------------------------------------------------
        stage("Checkout") {
        // ------------------------------------------------------------------
            steps {
                echo "━━━ Stage: Checkout ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                // When triggered by a PR, Jenkins already checks out the
                // merge commit of PR-head into the target branch.
                checkout scm

                echo "Branch    : ${env.BRANCH_NAME ?: env.GIT_BRANCH}"
                echo "Commit    : ${env.GIT_COMMIT}"
                echo "Workspace : ${env.WORKSPACE}"
            }
        }

        // ------------------------------------------------------------------
        stage("Verify Tools") {
        // ------------------------------------------------------------------
        // Quick sanity check that all required tools are installed on agent.
        // This fails fast with a clear error before wasting time building.
            steps {
                echo "━━━ Stage: Verify Tools ━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                sh """
                    echo "[tool check] cmake  : \$(cmake --version | head -1)"
                    echo "[tool check] gcc    : \$(gcc --version   | head -1)"
                    echo "[tool check] python3: \$(${PYTHON} --version)"
                    echo "[tool check] git    : \$(git --version)"
                """
            }
        }

        // ------------------------------------------------------------------
        stage("CMake Configure") {
        // ------------------------------------------------------------------
            steps {
                echo "━━━ Stage: CMake Configure ━━━━━━━━━━━━━━━━━━━━━━━━━"
                sh """
                    mkdir -p ${BUILD_DIR}
                    cmake -B ${BUILD_DIR} -S . \
                        -DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE} \
                        -DCMAKE_VERBOSE_MAKEFILE=ON
                """
            }
        }

        // ------------------------------------------------------------------
        stage("Build Shared Library") {
        // ------------------------------------------------------------------
            steps {
                echo "━━━ Stage: Build ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                sh """
                    cmake --build ${BUILD_DIR} --parallel 4
                    echo "[build] Shared library files produced:"
                    ls -lh ${TEST_DIR}/libcontroller.so \
                            ${TEST_DIR}/libcontroller.dylib \
                            ${TEST_DIR}/controller.dll \
                            2>/dev/null || true
                """
            }
            post {
                failure {
                    echo "BUILD FAILED — check compiler errors above"
                }
            }
        }

        // ------------------------------------------------------------------
        stage("Plant Model Self-Test") {
        // ------------------------------------------------------------------
        // Run the plant model standalone to verify Python is working and
        // the model does not crash before we involve the C library.
            steps {
                echo "━━━ Stage: Plant Self-Test ━━━━━━━━━━━━━━━━━━━━━━━━"
                sh "${PYTHON} plant/plant_model.py"
            }
        }

        // ------------------------------------------------------------------
        stage("SIL Tests") {
        // ------------------------------------------------------------------
        // This is the core stage: run the full closed-loop simulation.
        // The script exits with code 1 if any test case fails, which
        // makes Jenkins mark this build as FAILED.
            steps {
                echo "━━━ Stage: SIL Tests ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                sh """
                    ${PYTHON} ${TEST_DIR}/run_tests.py \
                        --output-dir ${REPORT_DIR}
                """
            }
            post {
                always {
                    // JUnit plugin reads sil_junit.xml and draws trend graphs
                    junit allowEmptyResults: true,
                          testResults: "${REPORT_DIR}/sil_junit.xml"
                }
                failure {
                    echo "SIL TESTS FAILED — see test report above"
                }
                success {
                    echo "All SIL tests passed!"
                }
            }
        }

        // ------------------------------------------------------------------
        stage("Archive Artifacts") {
        // ------------------------------------------------------------------
        // Save reports so they can be downloaded from the Jenkins build page.
            steps {
                echo "━━━ Stage: Archive Artifacts ━━━━━━━━━━━━━━━━━━━━━━"
                archiveArtifacts artifacts: "${REPORT_DIR}/sil_report.json",
                                 fingerprint: true,
                                 allowEmptyArchive: true
                archiveArtifacts artifacts: "${REPORT_DIR}/sil_junit.xml",
                                 fingerprint: true,
                                 allowEmptyArchive: true
            }
        }
    }

    // ======================================================================
    // POST — runs after all stages regardless of result
    // ======================================================================
    post {

        always {
            echo "━━━ Post: Cleanup ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            // Remove build artefacts to keep the workspace clean
            // (comment out if you want to inspect build artefacts locally)
            sh "rm -rf ${BUILD_DIR} || true"
        }

        success {
            echo "✓  Pipeline PASSED — all SIL tests green"
            // Uncomment to post a GitHub commit status (requires credentials):
            // githubNotify status: 'SUCCESS', description: 'SIL tests passed',
            //              context: 'ci/sil'
        }

        failure {
            echo "✗  Pipeline FAILED — check stages above"
            // Uncomment to send email on failure:
            // mail to: 'your-team@example.com',
            //      subject: "FAILED: SIL Pipeline — ${env.JOB_NAME} #${env.BUILD_NUMBER}",
            //      body: "See ${env.BUILD_URL}"
        }

        unstable {
            echo "⚠  Pipeline UNSTABLE — some tests failed or were skipped"
        }
    }
}
