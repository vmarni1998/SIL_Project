Copy

// =============================================================================
// Jenkinsfile  —  SIL Pipeline for Motor Speed Controller
// =============================================================================
//
// Trigger  : Every Pull Request (GitHub Branch Source / Multibranch Pipeline)
//            + fallback poll every 5 minutes
//
// Stages:
//   1. Checkout             — Clone the repo (merge commit of PR into target)
//   2. Verify Tools         — Confirm cmake / gcc / python3 / git are present
//   3. CMake Configure      — Run cmake -B build
//   4. Build Shared Library — cmake --build  →  libcontroller.so → tests/
//   5. Plant Model Self-Test— python3 plant/plant_model.py
//   6. SIL Tests            — python3 tests/run_tests.py  (6 closed-loop sims)
//   7. Archive Artifacts    — sil_junit.xml + sil_report.json
//
// Post (always):
//   • JUnit trend graphs in Jenkins UI
//   • Email to PR author + team DL  (HTML, with direct links to report/log)
//   • GitHub commit status  ✓ / ✗  posted back to the PR
//
// Agent requirements:
//   cmake >= 3.16 | gcc (C11) | python3 >= 3.8 | git
// =============================================================================
 
pipeline {
 
    // ── Agent ──────────────────────────────────────────────────────────────
    // Replace 'any' with a label (e.g. 'linux-sil') if you have dedicated nodes
    agent any
 
    // ── Global environment variables ───────────────────────────────────────
    environment {
        BUILD_DIR        = "build"
        TEST_DIR         = "tests"
        REPORT_DIR       = "tests"
        PYTHON           = "python3"          // use 'python' on Windows agents
        CMAKE_BUILD_TYPE = "Debug"            // Debug keeps -Wall / -Werror
 
        // ── Email recipients ───────────────────────────────────────────────
        // TEAM_EMAIL is loaded from a Jenkins credential (plain text secret).
        // This keeps real addresses out of the repo.
        // Create it under: Manage Jenkins → Credentials → Global
        //   Kind : Secret text
        //   ID   : SIL_TEAM_EMAIL
        //   Value: your-team-dl@yourcompany.com
        TEAM_EMAIL = credentials("vmarni@mtu.edu")
    }
 
    // ── Pipeline-wide options ──────────────────────────────────────────────
    options {
        timeout(time: 30, unit: "MINUTES")           // abort if hung
        buildDiscarder(logRotator(numToKeepStr: "10")) // keep last 10 builds
        ansiColor("xterm")                            // coloured console output
        disableConcurrentBuilds()                     // one build per branch
        timestamps()                                  // timestamps in log
    }
 
    // ── Triggers ───────────────────────────────────────────────────────────
    // PR triggers come from the GitHub Branch Source plugin (configured in
    // the Multibranch job, not here).  pollSCM is a fallback safety net.
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
                echo "━━━ Stage 1 / 7 : Checkout ━━━━━━━━━━━━━━━━━━━━━━━━"
                // For a PR, Jenkins checks out the merge commit of
                // PR-head into the target branch automatically.
                checkout scm
 
                echo "Branch    : ${env.BRANCH_NAME ?: env.GIT_BRANCH}"
                echo "Commit    : ${env.GIT_COMMIT}"
                echo "PR        : ${env.CHANGE_ID   ?: '(not a PR build)'}"
                echo "PR Title  : ${env.CHANGE_TITLE ?: 'N/A'}"
                echo "PR Author : ${env.CHANGE_AUTHOR ?: 'N/A'}"
                echo "Workspace : ${env.WORKSPACE}"
            }
        }
 
        // ------------------------------------------------------------------
        stage("Verify Tools") {
        // ------------------------------------------------------------------
            steps {
                echo "━━━ Stage 2 / 7 : Verify Tools ━━━━━━━━━━━━━━━━━━━━"
                sh """
                    echo "[tool] cmake  : \$(cmake --version | head -1)"
                    echo "[tool] gcc    : \$(gcc   --version | head -1)"
                    echo "[tool] python : \$(${PYTHON} --version)"
                    echo "[tool] git    : \$(git   --version)"
                """
            }
        }
 
        // ------------------------------------------------------------------
        stage("CMake Configure") {
        // ------------------------------------------------------------------
            steps {
                echo "━━━ Stage 3 / 7 : CMake Configure ━━━━━━━━━━━━━━━━━"
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
                echo "━━━ Stage 4 / 7 : Build ━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                sh """
                    cmake --build ${BUILD_DIR} --parallel 4
                    echo "[build] Shared library produced:"
                    ls -lh ${TEST_DIR}/libcontroller.so \
                            ${TEST_DIR}/libcontroller.dylib \
                            ${TEST_DIR}/controller.dll \
                            2>/dev/null || true
                """
            }
            post {
                failure {
                    echo "BUILD FAILED — see compiler errors above"
                }
            }
        }
 
        // ------------------------------------------------------------------
        stage("Plant Model Self-Test") {
        // ------------------------------------------------------------------
            steps {
                echo "━━━ Stage 5 / 7 : Plant Self-Test ━━━━━━━━━━━━━━━━━"
                sh "${PYTHON} plant/plant_model.py"
            }
        }
 
        // ------------------------------------------------------------------
        stage("SIL Tests") {
        // ------------------------------------------------------------------
            steps {
                echo "━━━ Stage 6 / 7 : SIL Tests ━━━━━━━━━━━━━━━━━━━━━━"
                sh """
                    ${PYTHON} ${TEST_DIR}/run_tests.py \
                        --output-dir ${REPORT_DIR}
                """
            }
            post {
                always {
                    // JUnit plugin parses XML and draws trend graphs
                    junit allowEmptyResults: true,
                          testResults: "${REPORT_DIR}/sil_junit.xml"
                }
                success { echo "All SIL tests passed ✓" }
                failure { echo "SIL TESTS FAILED — see report above" }
            }
        }
 
        // ------------------------------------------------------------------
        stage("Archive Artifacts") {
        // ------------------------------------------------------------------
            steps {
                echo "━━━ Stage 7 / 7 : Archive ━━━━━━━━━━━━━━━━━━━━━━━━━"
                archiveArtifacts artifacts: "${REPORT_DIR}/sil_report.json",
                                 fingerprint: true,
                                 allowEmptyArchive: true
                archiveArtifacts artifacts: "${REPORT_DIR}/sil_junit.xml",
                                 fingerprint: true,
                                 allowEmptyArchive: true
            }
        }
 
    } // end stages
 
    // ======================================================================
    // POST  —  runs after all stages, no matter what happened
    // ======================================================================
    post {
 
        // ── 1. Workspace cleanup ───────────────────────────────────────────
        always {
            echo "━━━ Post : Cleanup ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            sh "rm -rf ${BUILD_DIR} || true"
        }
 
        // ── 2. GitHub commit status ────────────────────────────────────────
        // Requires: GitHub plugin + a credential with repo:status scope.
        // The Multibranch / GitHub Branch Source plugin usually does this
        // automatically, but the explicit calls below give you full control.
        success {
            echo "✓  Pipeline PASSED"
            // Uncomment after adding the 'github-token' credential:
            // githubNotify status: 'SUCCESS',
            //              description: 'SIL tests passed',
            //              context: 'ci/sil',
            //              credentialsId: 'github-token'
        }
 
        failure {
            echo "✗  Pipeline FAILED"
            // githubNotify status: 'FAILURE',
            //              description: 'SIL tests failed',
            //              context: 'ci/sil',
            //              credentialsId: 'github-token'
        }
 
        unstable {
            echo "⚠  Pipeline UNSTABLE — some tests skipped or flaky"
        }
 
        // ── 3. Email notification (always — pass AND fail) ─────────────────
        //
        // Uses the Email Extension plugin (email-ext).
        // Install: Manage Jenkins → Plugins → "Email Extension Plugin"
        //
        // SMTP is configured globally under:
        //   Manage Jenkins → System → Extended E-mail Notification
        //
        // Variables that work inside Multibranch / GitHub Branch Source:
        //   env.CHANGE_ID            PR number  (e.g. "42")
        //   env.CHANGE_TITLE         PR title   (e.g. "Fix PID windup")
        //   env.CHANGE_AUTHOR        GitHub username of PR opener
        //   env.CHANGE_AUTHOR_EMAIL  Email of PR opener  ← used as "to"
        //   env.BRANCH_NAME          e.g. "PR-42"
        //   env.BUILD_URL            Full URL to this build
        //   env.BUILD_NUMBER         e.g. "17"
        //   currentBuild.result      "SUCCESS" | "FAILURE" | "UNSTABLE"
        //   currentBuild.duration    ms elapsed (divide by 1000 for seconds)
        // ------------------------------------------------------------------
        always {
            script {
 
                // ── Derive display values ──────────────────────────────────
                def result      = currentBuild.result ?: "SUCCESS"
                def isPR        = (env.CHANGE_ID != null)
                def prLine      = isPR
                    ? "PR #${env.CHANGE_ID} — ${env.CHANGE_TITLE ?: '(no title)'}"
                    : env.BRANCH_NAME
                def authorEmail = env.CHANGE_AUTHOR_EMAIL ?: ""
                def durationSec = (currentBuild.duration / 1000).toInteger()
 
                // ── Color / icon per result ────────────────────────────────
                def color, icon, banner
                switch (result) {
                    case "SUCCESS":
                        color = "#2ea44f"; icon = "✅"; banner = "All tests passed"; break
                    case "UNSTABLE":
                        color = "#d29922"; icon = "⚠️"; banner = "Some tests skipped"; break
                    default:
                        color = "#cb2431"; icon = "❌"; banner = "Build / tests failed"; break
                }
 
                // ── Recipient list ─────────────────────────────────────────
                // Always sends to the team DL.
                // On a PR build, also CC the PR author if their email is known.
                def recipients = env.TEAM_EMAIL
                if (authorEmail) { recipients = "${authorEmail}, ${recipients}" }
 
                // ── Send email ─────────────────────────────────────────────
                emailext(
                    subject: "${icon} [SIL ${result}] ${prLine} — Build #${env.BUILD_NUMBER}",
                    to: recipients,
                    replyTo: "jenkins-noreply@yourcompany.com",
                    mimeType: "text/html",
 
                    body: """
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f6f8fa;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f6f8fa;padding:24px 0;">
  <tr><td align="center">
  <table width="600" cellpadding="0" cellspacing="0"
         style="background:#ffffff;border:1px solid #e1e4e8;border-radius:8px;overflow:hidden;">
 
    <!-- Header banner -->
    <tr>
      <td style="background:${color};padding:20px 28px;">
        <span style="font-size:22px;font-weight:700;color:#ffffff;">
          ${icon} SIL Pipeline — ${banner}
        </span>
      </td>
    </tr>
 
    <!-- Build summary table -->
    <tr>
      <td style="padding:24px 28px 12px;">
        <table cellpadding="6" cellspacing="0" width="100%"
               style="border-collapse:collapse;font-size:14px;">
          <tr style="border-bottom:1px solid #e1e4e8;">
            <td style="color:#586069;width:130px;">Result</td>
            <td style="font-weight:700;color:${color};">${result}</td>
          </tr>
          <tr style="border-bottom:1px solid #e1e4e8;">
            <td style="color:#586069;">Job</td>
            <td>${env.JOB_NAME}</td>
          </tr>
          <tr style="border-bottom:1px solid #e1e4e8;">
            <td style="color:#586069;">Build</td>
            <td>#${env.BUILD_NUMBER}</td>
          </tr>
          <tr style="border-bottom:1px solid #e1e4e8;">
            <td style="color:#586069;">Branch</td>
            <td><code>${env.BRANCH_NAME}</code></td>
          </tr>
          <tr style="border-bottom:1px solid #e1e4e8;">
            <td style="color:#586069;">PR</td>
            <td>${prLine}</td>
          </tr>
          <tr style="border-bottom:1px solid #e1e4e8;">
            <td style="color:#586069;">Author</td>
            <td>${env.CHANGE_AUTHOR ?: 'N/A'}</td>
          </tr>
          <tr style="border-bottom:1px solid #e1e4e8;">
            <td style="color:#586069;">Commit</td>
            <td><code>${env.GIT_COMMIT?.take(8) ?: 'N/A'}</code></td>
          </tr>
          <tr>
            <td style="color:#586069;">Duration</td>
            <td>${durationSec}s</td>
          </tr>
        </table>
      </td>
    </tr>
 
    <!-- Quick links -->
    <tr>
      <td style="padding:12px 28px 28px;">
        <a href="${env.BUILD_URL}testReport"
           style="display:inline-block;margin-right:8px;padding:8px 16px;
                  background:#0366d6;color:#fff;border-radius:5px;
                  text-decoration:none;font-size:13px;">
          📊 Test report
        </a>
        <a href="${env.BUILD_URL}artifact/${REPORT_DIR}/sil_report.json"
           style="display:inline-block;margin-right:8px;padding:8px 16px;
                  background:#0366d6;color:#fff;border-radius:5px;
                  text-decoration:none;font-size:13px;">
          📄 SIL JSON
        </a>
        <a href="${env.BUILD_URL}console"
           style="display:inline-block;padding:8px 16px;
                  background:#586069;color:#fff;border-radius:5px;
                  text-decoration:none;font-size:13px;">
          📋 Console log
        </a>
      </td>
    </tr>
 
    <!-- Footer -->
    <tr>
      <td style="background:#f6f8fa;padding:14px 28px;border-top:1px solid #e1e4e8;
                 font-size:12px;color:#586069;">
        Sent by Jenkins CI — Motor Speed Controller SIL Pipeline
      </td>
    </tr>
 
  </table>
  </td></tr>
</table>
</body>
</html>
                    """
                ) // end emailext
 
            } // end script
        } // end always (email)
 
    } // end post
}