// =============================================================================
// Jenkinsfile  —  SIL Pipeline for Motor Speed Controller
// =============================================================================
pipeline {

    agent any

    environment {
        BUILD_DIR        = "build"
        TEST_DIR         = "tests"
        REPORT_DIR       = "tests"
        PYTHON           = "python3"
        CMAKE_BUILD_TYPE = "Debug"
        TEAM_EMAIL       = credentials("vmarni@mtu.edu")
    }

    options {
        timeout(time: 30, unit: "MINUTES")
        buildDiscarder(logRotator(numToKeepStr: "10"))
        ansiColor("xterm")
        disableConcurrentBuilds()
        timestamps()
    }

    triggers {
        pollSCM("H/5 * * * *")
    }

    // ======================================================================
    // STAGES
    // ======================================================================
    stages {

        stage("Checkout") {
            steps {
                echo "━━━ Stage 1 / 7 : Checkout ━━━━━━━━━━━━━━━━━━━━━━━━"
                checkout scm
                echo "Branch    : ${env.BRANCH_NAME ?: env.GIT_BRANCH}"
                echo "Commit    : ${env.GIT_COMMIT}"
                echo "PR        : ${env.CHANGE_ID   ?: '(not a PR build)'}"
                echo "PR Title  : ${env.CHANGE_TITLE ?: 'N/A'}"
                echo "PR Author : ${env.CHANGE_AUTHOR ?: 'N/A'}"
                echo "Workspace : ${env.WORKSPACE}"
            }
        }

        stage("Verify Tools") {
            steps {
                echo "━━━ Stage 2 / 7 : Verify Tools ━━━━━━━━━━━━━━━━━━━━"
                sh """
                    echo "[tool] cmake  : \$(cmake --version | head -1)"
                    echo "[tool] gcc    : \$(gcc   --version | head -1)"
                    echo "[tool] python : \$(python3 --version)"
                    echo "[tool] git    : \$(git   --version)"
                """
            }
        }

        stage("CMake Configure") {
            steps {
                echo "━━━ Stage 3 / 7 : CMake Configure ━━━━━━━━━━━━━━━━━"
                sh """
                    mkdir -p build
                    cmake -B build -S . \
                        -DCMAKE_BUILD_TYPE=Debug \
                        -DCMAKE_VERBOSE_MAKEFILE=ON
                """
            }
        }

        stage("Build Shared Library") {
            steps {
                echo "━━━ Stage 4 / 7 : Build ━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                sh """
                    cmake --build build --parallel 4
                    echo "[build] Shared library produced:"
                    ls -lh tests/libcontroller.so 2>/dev/null || true
                """
            }
            post {
                failure { echo "BUILD FAILED — see compiler errors above" }
            }
        }

        stage("Plant Model Self-Test") {
            steps {
                echo "━━━ Stage 5 / 7 : Plant Self-Test ━━━━━━━━━━━━━━━━━"
                sh "python3 plant/plant_model.py"
            }
        }

        stage("SIL Tests") {
            steps {
                echo "━━━ Stage 6 / 7 : SIL Tests ━━━━━━━━━━━━━━━━━━━━━━"
                sh "python3 tests/run_tests.py --output-dir tests"
            }
            post {
                always {
                    junit allowEmptyResults: true,
                          testResults: "tests/sil_junit.xml"
                }
                success { echo "All SIL tests passed ✓" }
                failure { echo "SIL TESTS FAILED — see report above" }
            }
        }

        stage("Archive Artifacts") {
            steps {
                echo "━━━ Stage 7 / 7 : Archive ━━━━━━━━━━━━━━━━━━━━━━━━━"
                archiveArtifacts artifacts: "tests/sil_report.json",
                                 fingerprint: true,
                                 allowEmptyArchive: true
                archiveArtifacts artifacts: "tests/sil_junit.xml",
                                 fingerprint: true,
                                 allowEmptyArchive: true
                sh "rm -rf build || true"
            }
        }

    } // end stages

    // ======================================================================
    // POST — all values hardcoded, no env vars that may be null
    // ======================================================================
    post {

        success  { echo "✓  Pipeline PASSED"    }
        failure  { echo "✗  Pipeline FAILED"    }
        unstable { echo "⚠  Pipeline UNSTABLE"  }

        always {
            script {
                def result      = currentBuild.result ?: "SUCCESS"
                def jobName     = env.JOB_NAME     ?: "SIL Pipeline"
                def buildNum    = env.BUILD_NUMBER  ?: "?"
                def buildUrl    = env.BUILD_URL     ?: ""
                def branchName  = env.BRANCH_NAME  ?: "unknown"
                def changeId    = env.CHANGE_ID
                def changeTitle = env.CHANGE_TITLE ?: ""
                def changeAuth  = env.CHANGE_AUTHOR ?: "N/A"
                def gitCommit   = env.GIT_COMMIT ? env.GIT_COMMIT.take(8) : "N/A"
                def teamEmail   = env.TEAM_EMAIL   ?: "vmarni@mtu.edu"
                def durationSec = (currentBuild.duration / 1000).toInteger()

                def isPR   = (changeId != null)
                def prLine = isPR
                    ? "PR #${changeId} — ${changeTitle ?: '(no title)'}"
                    : branchName

                def color, icon, banner
                switch (result) {
                    case "SUCCESS":
                        color = "#2ea44f"; icon = "✅"; banner = "All tests passed"; break
                    case "UNSTABLE":
                        color = "#d29922"; icon = "⚠️"; banner = "Some tests skipped"; break
                    default:
                        color = "#cb2431"; icon = "❌"; banner = "Build / tests failed"; break
                }

                emailext(
                    subject: "${icon} [SIL ${result}] ${prLine} — Build #${buildNum}",
                    to: teamEmail,
                    replyTo: "jenkins-noreply@example.com",
                    mimeType: "text/html",
                    body: """
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f6f8fa;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f6f8fa;padding:24px 0;">
  <tr><td align="center">
  <table width="600" cellpadding="0" cellspacing="0"
         style="background:#ffffff;border:1px solid #e1e4e8;border-radius:8px;overflow:hidden;">

    <tr>
      <td style="background:${color};padding:20px 28px;">
        <span style="font-size:22px;font-weight:700;color:#ffffff;">
          ${icon} SIL Pipeline — ${banner}
        </span>
      </td>
    </tr>

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
            <td>${jobName}</td>
          </tr>
          <tr style="border-bottom:1px solid #e1e4e8;">
            <td style="color:#586069;">Build</td>
            <td>#${buildNum}</td>
          </tr>
          <tr style="border-bottom:1px solid #e1e4e8;">
            <td style="color:#586069;">Branch</td>
            <td><code>${branchName}</code></td>
          </tr>
          <tr style="border-bottom:1px solid #e1e4e8;">
            <td style="color:#586069;">PR</td>
            <td>${prLine}</td>
          </tr>
          <tr style="border-bottom:1px solid #e1e4e8;">
            <td style="color:#586069;">Author</td>
            <td>${changeAuth}</td>
          </tr>
          <tr style="border-bottom:1px solid #e1e4e8;">
            <td style="color:#586069;">Commit</td>
            <td><code>${gitCommit}</code></td>
          </tr>
          <tr>
            <td style="color:#586069;">Duration</td>
            <td>${durationSec}s</td>
          </tr>
        </table>
      </td>
    </tr>

    <tr>
      <td style="padding:12px 28px 28px;">
        <a href="${buildUrl}testReport"
           style="display:inline-block;margin-right:8px;padding:8px 16px;
                  background:#0366d6;color:#fff;border-radius:5px;
                  text-decoration:none;font-size:13px;">
          📊 Test report
        </a>
        <a href="${buildUrl}artifact/tests/sil_report.json"
           style="display:inline-block;margin-right:8px;padding:8px 16px;
                  background:#0366d6;color:#fff;border-radius:5px;
                  text-decoration:none;font-size:13px;">
          📄 SIL JSON
        </a>
        <a href="${buildUrl}console"
           style="display:inline-block;padding:8px 16px;
                  background:#586069;color:#fff;border-radius:5px;
                  text-decoration:none;font-size:13px;">
          📋 Console log
        </a>
      </td>
    </tr>

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
                )
            }
        }

    } // end post
}
