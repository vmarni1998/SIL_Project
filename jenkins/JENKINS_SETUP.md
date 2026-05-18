# Jenkins Setup Guide — SIL Project
## Step-by-step: from zero to automatic PR testing

---

## What you will have at the end

- Jenkins checks out your repo automatically when a PR is opened
- Jenkins builds the C library, runs all SIL tests, and reports PASS/FAIL
- The PR page on GitHub shows a green ✓ or red ✗ from Jenkins
- Test results are graphed over time inside Jenkins

---

## Step 1 — Install Jenkins

### Option A: Docker (recommended for learning)

```bash
# Pull and run Jenkins with Docker
docker run -d \
  --name jenkins \
  -p 8080:8080 \
  -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  jenkins/jenkins:lts-jdk17

# Get the initial admin password
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Open http://localhost:8080 in your browser and paste the password.

### Option B: Install on Ubuntu/Debian directly

```bash
# Add Jenkins apt repository
curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key \
  | sudo tee /usr/share/keyrings/jenkins-keyring.asc > /dev/null

echo deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] \
  https://pkg.jenkins.io/debian-stable binary/ \
  | sudo tee /etc/apt/sources.list.d/jenkins.list > /dev/null

sudo apt update
sudo apt install -y jenkins
sudo systemctl start jenkins
sudo systemctl enable jenkins

# Get admin password
sudo cat /var/jenkins_home/secrets/initialAdminPassword
```

Open http://localhost:8080

---

## Step 2 — Install required tools on the Jenkins agent

These must be present on whichever machine Jenkins runs builds on.

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y \
    cmake \
    gcc \
    g++ \
    make \
    python3 \
    python3-pip \
    git

# Verify
cmake --version    # must be >= 3.16
gcc --version
python3 --version  # must be >= 3.8
git --version
```

---

## Step 3 — Install Jenkins plugins

In Jenkins UI → **Manage Jenkins** → **Plugin Manager** → **Available**

Search for and install these plugins:

| Plugin | Why |
|--------|-----|
| **Pipeline** | Enables Jenkinsfile-based pipelines |
| **GitHub Branch Source** | Discovers PRs automatically from GitHub |
| **JUnit** | Reads sil_junit.xml and draws test graphs |
| **AnsiColor** | Coloured terminal output in logs |
| **Timestamper** | Adds timestamps to console |
| **GitHub** | Posts build status back to GitHub PR |
| **Workspace Cleanup** | Keeps agent workspace tidy |

After installing, click **Restart Jenkins**.

---

## Step 4 — Add GitHub credentials to Jenkins

Jenkins needs a token to:
- Clone your (private) repository
- Post the ✓ / ✗ status back to the PR on GitHub

### 4a — Create a GitHub Personal Access Token (PAT)

1. On GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. Click **Generate new token (classic)**
3. Name it: `jenkins-sil-ci`
4. Select scopes:
   - `repo` (full repo access — needed to post status)
   - `admin:repo_hook` (needed for webhook auto-creation)
5. Copy the token — you will not see it again

### 4b — Store it in Jenkins

1. Jenkins → **Manage Jenkins** → **Credentials** → **System** → **Global credentials**
2. Click **Add Credentials**
3. Fill in:
   - **Kind**: Username with password
   - **Username**: your GitHub username
   - **Password**: paste the PAT you just created
   - **ID**: `github-credentials`   ← this ID is referenced in the Jenkinsfile
   - **Description**: GitHub PAT for SIL CI
4. Click **OK**

---

## Step 5 — Create a Multibranch Pipeline job

A **Multibranch Pipeline** automatically discovers all branches and PRs in your repo.

1. Jenkins home → **New Item**
2. Enter name: `sil-motor-controller`
3. Select **Multibranch Pipeline**
4. Click **OK**

### Configure Branch Sources

In the job configuration page:

1. Under **Branch Sources** → click **Add source** → **GitHub**
2. Fill in:
   - **Credentials**: select `github-credentials` (from Step 4)
   - **Repository HTTPS URL**: `https://github.com/<your-org>/sil_project.git`
3. Under **Behaviours** → **Add** → **Discover pull requests from origin**
   - Strategy: **Merging the pull request with the current target branch revision**
4. Under **Build Configuration**:
   - **Mode**: by Jenkinsfile
   - **Script Path**: `Jenkinsfile`   ← default, already correct
5. Under **Scan Multibranch Pipeline Triggers**:
   - Check **Periodically if not otherwise run** → Interval: **1 minute**
6. Click **Save**

Jenkins will immediately scan the repo and show all branches.

---

## Step 6 — Configure the GitHub webhook (automatic PR triggering)

A webhook tells GitHub to push a notification to Jenkins the instant a PR is opened  
or updated — instead of Jenkins polling every minute.

### 6a — Find your Jenkins URL

If running locally: you need a public URL.  
Use **ngrok** to expose localhost temporarily:

```bash
# Install ngrok (https://ngrok.com/download)
ngrok http 8080
# You get a URL like: https://a1b2c3d4.ngrok.io
```

In production Jenkins is on a server with a real domain (e.g. `https://ci.yourcompany.com`).

### 6b — Add the webhook in GitHub

1. Go to your GitHub repo → **Settings** → **Webhooks** → **Add webhook**
2. Fill in:
   - **Payload URL**: `https://<your-jenkins-url>/github-webhook/`
     (note the trailing slash — it is required)
   - **Content type**: `application/json`
   - **Secret**: leave blank (or add one and configure it in Jenkins too)
   - **Which events**: select **Let me select individual events**
     - ✓ Pull requests
     - ✓ Pushes
3. Click **Add webhook**

GitHub will send a test ping; you should see a green tick.

### 6c — Configure Jenkins GitHub server

1. Jenkins → **Manage Jenkins** → **Configure System**
2. Scroll to **GitHub** section → **Add GitHub Server**
3. Fill in:
   - **Name**: `GitHub`
   - **API URL**: `https://api.github.com`
   - **Credentials**: select `github-credentials`
4. Click **Test connection** — should say "Credentials verified"
5. Check **Manage hooks** (lets Jenkins auto-create webhooks)
6. Click **Save**

---

## Step 7 — Test the pipeline

### 7a — Run manually first

1. In Jenkins, open the `sil-motor-controller` job
2. Click **Scan Multibranch Pipeline Now** to detect the main branch
3. Click on `main` branch → **Build Now**
4. Watch the **Console Output** — you should see all 6 SIL tests pass

### 7b — Test PR triggering

1. On your local machine, create a new branch:

```bash
git checkout -b feature/test-jenkins-trigger
# Make a trivial change
echo "# trigger" >> README.md
git add README.md
git commit -m "test: trigger Jenkins via PR"
git push origin feature/test-jenkins-trigger
```

2. On GitHub, open a Pull Request from `feature/test-jenkins-trigger` → `main`
3. Within ~30 seconds (webhook) or ~1 minute (poll), Jenkins starts a build
4. The PR page on GitHub shows:

```
✓  ci/sil — All SIL tests passed  —  Details
```

or if a test fails:

```
✗  ci/sil — SIL tests FAILED  —  Details
```

---

## Step 8 — Protect the main branch (optional but recommended)

This prevents merging a PR that fails SIL tests.

1. GitHub repo → **Settings** → **Branches**
2. Click **Add branch protection rule**
3. **Branch name pattern**: `main`
4. Check:
   - ✓ **Require status checks to pass before merging**
   - Search for `ci/sil` and add it
   - ✓ **Require branches to be up to date before merging**
5. Click **Save changes**

Now GitHub will block the **Merge** button until Jenkins reports success.

---

## Viewing test results in Jenkins

After a build completes:

| What | Where |
|------|-------|
| Console log | Build → Console Output |
| Test trend graph | Job page → Test Result Trend |
| Per-test results | Build → Test Results |
| JSON report | Build → Artifacts → sil_report.json |
| JUnit XML | Build → Artifacts → sil_junit.xml |

---

## Troubleshooting

### "libcontroller.so not found"
The CMake build did not run or the POST_BUILD copy failed.  
Check the **Build Shared Library** stage in the console log.

### "python3: command not found"
Install Python 3 on the agent (`sudo apt install python3`) and restart Jenkins.

### "cmake: command not found"
Install CMake on the agent (`sudo apt install cmake`) and restart Jenkins.

### GitHub webhook not firing
- Check **Settings → Webhooks** — the last delivery should show 200 OK
- Check your Jenkins URL is reachable from the internet (use ngrok for local)
- Check Jenkins logs: **Manage Jenkins → System Log**

### PR check not appearing on GitHub
- Ensure the GitHub plugin is installed and the server is configured (Step 6c)
- Ensure the PAT has `repo` scope
- Try clicking **Rescan** on the Multibranch Pipeline job

---

## Full pipeline flow diagram

```
Developer opens PR on GitHub
        │
        ▼
GitHub sends webhook POST to Jenkins
        │
        ▼
Jenkins checks out PR merge commit
        │
        ▼
┌───────────────────────────────────────────┐
│  cmake -B build -S .                      │
│  cmake --build build                      │
│  → produces libcontroller.so in tests/    │
└───────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────┐
│  python3 plant/plant_model.py             │
│  → plant self-test (verify no crash)      │
└───────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────┐
│  python3 tests/run_tests.py               │
│  → 6 closed-loop SIL test cases          │
│  → writes sil_report.json                │
│  → writes sil_junit.xml                  │
└───────────────────────────────────────────┘
        │
        ├── ALL PASS → Jenkins: SUCCESS → GitHub PR: ✓ green
        │
        └── ANY FAIL → Jenkins: FAILED  → GitHub PR: ✗ red
                                        → Merge button blocked
```
