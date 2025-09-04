# Quokka Regression Testing Documentation

## Quick Start

Run regression tests on HPC clusters:

```bash
# 1. Setup environment (load modules and activate venv)
source setup/env_setup_ucx.sh
source /home/agray/src/cas/quokka/mk2025a/.venv/bin/activate

# 2. Setup test environment (creates work directory structure)
regression_testing/regtest.py setup config_nt.ini

# 3. Submit batch jobs to cluster
regression_testing/regtest.py submit config_nt.ini

# 4. Check job status (can run multiple times)
regression_testing/regtest.py check config_nt.ini

# 5. Extract results after jobs complete
regression_testing/regtest.py extract config_nt.ini

# 6. Generate web report
regression_testing/regtest.py www

# 7. View results
firefox www/index.html
```

## A. Setup Virtual Environment

### Option 1: Using mk2025a virtual environment

The mk2025a repository provides a pre-configured virtual environment:

```bash
# Navigate to mk2025a directory
cd /home/agray/src/cas/quokka/mk2025a

# Create virtual environment from pyproject.toml
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# The environment includes:
# - hpc_performance_testing (for batch job management)
# - pandas, numpy (for data processing)
# - matplotlib (for plotting)
# - pyyaml (for configuration)
```

### Option 2: Using regression_testing requirements

Create a minimal environment for regression testing only:

```bash
# Navigate to regression testing directory
cd /home/agray/src/cas/quokka/work/regression_testing

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

## B. Setup authorized_keys for Remote Execution

The regression testing system can be triggered remotely using SSH with restricted keys. This allows CI systems or remote users to run tests securely.

### Example authorized_keys entry:

A complete example is provided in `authorized_keys_example`:

```
command="bash -l -c 'set -e; cd ${HOME}/src/cas/quokka/remote; [ -f setup/env.sh ] && source setup/env.sh; exec python regression_testing/regtest.py'",restrict ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFG21CqFMHf3gAt6dui9XkGbXDjenzvUJkgiRCYNQJK9 quokka
```

### Key components explained:

1. **`command="..."`** - Restricts this SSH key to only execute the specified command
   - `bash -l -c` - Runs bash as a login shell to load user environment
   - `set -e` - Exit immediately if any command fails
   - `cd ${HOME}/src/cas/quokka/remote` - Change to the remote working directory
   - `[ -f setup/env.sh ] && source setup/env.sh` - Source environment setup if it exists
   - `exec python regression_testing/regtest.py` - Execute regtest.py (replaces shell process)

2. **`restrict`** - Modern SSH restriction (equivalent to combining the following legacy options):
   - `no-port-forwarding` - Prevents SSH port forwarding
   - `no-X11-forwarding` - Prevents X11 display forwarding  
   - `no-agent-forwarding` - Prevents SSH agent forwarding
   - `no-pty` - Prevents interactive terminal allocation
   - `no-user-rc` - Prevents execution of ~/.ssh/rc

3. **SSH key** - The public key (ssh-ed25519 or ssh-rsa format)

### Setting up the restricted key:

1. **Add to ~/.ssh/authorized_keys**:
   ```bash
   cat authorized_keys_example >> ~/.ssh/authorized_keys
   ```

2. **Adjust the path in the command**:
   - Replace `${HOME}/src/cas/quokka/remote` with your actual work directory
   - The example uses `remote/` subdirectory for isolation

3. **Create the environment setup** (optional):
   ```bash
   # Create setup/env.sh in your work directory
   cat > ~/src/cas/quokka/remote/setup/env.sh << 'EOF'
   #!/bin/bash
   module load gcc/11.2.0
   module load cuda/12.0
   source /home/agray/src/cas/quokka/mk2025a/.venv/bin/activate
   EOF
   ```

### Valid remote commands:

When the SSH key is properly configured, remote commands are automatically passed to regtest.py via SSH_ORIGINAL_COMMAND:

```bash
# From remote system (the SSH command is parsed from SSH_ORIGINAL_COMMAND)
ssh -i ~/.ssh/quokka_key agray@hpc.example.com "submit config_nt.ini"
ssh -i ~/.ssh/quokka_key agray@hpc.example.com "check config_nt.ini" 
ssh -i ~/.ssh/quokka_key agray@hpc.example.com "extract config_nt.ini"
ssh -i ~/.ssh/quokka_key agray@hpc.example.com "www"  # INI file optional for www
ssh -i ~/.ssh/quokka_key agray@hpc.example.com "setup config_nt.ini"
```

The regtest.py script automatically detects it's running via SSH and parses the command from the SSH_ORIGINAL_COMMAND environment variable.

### Security notes:

- The `restrict` option is the modern way to apply all security restrictions at once
- The command restriction ensures the SSH key can ONLY run regtest.py
- Using `exec` replaces the shell process, preventing shell escape attempts
- The `set -e` ensures the command chain stops on any error
- Environment setup is optional but allows module loading if needed

## C. Folder Structure

The regression testing system uses the following directory structure:

```
quokka/
├── work/                          # Main working directory
│   ├── regression_testing/        # Testing scripts and tools
│   │   ├── regtest.py            # Main testing script
│   │   ├── web_generator.py      # Web report generation
│   │   ├── plotting.py           # Performance plotting
│   │   └── web_utils.py          # Web utilities
│   │
│   ├── config_nt.ini             # Configuration for test suite
│   ├── config_nt_A.ini           # Variant A configuration
│   ├── config_nt_B.ini           # Variant B configuration
│   │
│   ├── A/                        # Test variant A results
│   │   └── performance_test/
│   │       └── 20250831123050/   # Timestamp directory
│   │           ├── quokka/       # Quokka source (git repo)
│   │           ├── results/      # Test output files
│   │           │   ├── job_submission.parquet
│   │           │   ├── job_output.parquet
│   │           │   └── job_exit_status.parquet
│   │           └── test_*/       # Individual test directories
│   │
│   ├── B/                        # Test variant B results
│   ├── C/                        # Test variant C results
│   └── reference/                # Reference baseline results
│
├── www/                          # Web output directory
│   ├── index.html               # Main dashboard
│   ├── A/                       # Variant A web pages
│   │   ├── index.html          # Folder summary
│   │   ├── trends.html         # Performance trends
│   │   └── 20250831123050/     # Timestamp pages
│   │       └── index.html
│   ├── B/                       # Variant B web pages
│   ├── C/                       # Variant C web pages
│   └── reference/               # Reference web pages
│
├── setup/                       # Environment setup scripts
│   ├── env_setup_ucx.sh       # UCX-enabled MPI environment
│   └── env_setup_ompi.sh      # OpenMPI environment
│
└── mk2025a/                    # Performance testing package
    ├── pyproject.toml          # Python package configuration
    └── .venv/                  # Virtual environment
```

### Key directories:
- **work/**: Contains all test configurations and results
- **www/**: Generated HTML reports and visualizations
- **setup/**: Module loading and environment scripts
- **mk2025a/**: Python package for HPC performance testing

## D. Running regtest Commands

### regtest.py setup

Prepares the test environment:
```bash
regression_testing/regtest.py setup config_nt.ini
```

Actions:
1. Creates work directory structure
2. Validates configuration file
3. Copies test inputs to work directory
4. Prepares build directories

### regtest.py submit

Submits batch jobs to the HPC scheduler:
```bash
regression_testing/regtest.py submit config_nt.ini
```

Actions:
1. Converts INI config to YAML for hpc_performance_testing
2. Creates job submission scripts
3. Submits jobs to scheduler (SLURM/PBS)
4. Records job IDs in test_instance.yaml
5. Creates job_submission.parquet

### regtest.py check

Monitors job status:
```bash
regression_testing/regtest.py check config_nt.ini
```

Actions:
1. Queries scheduler for job status
2. Reports: WAIT, RUNNING, COMPLETE, FAILED
3. Updates job_exit_status.parquet when complete
4. Safe to run multiple times

### regtest.py extract

Processes completed job outputs:
```bash
regression_testing/regtest.py extract config_nt.ini
```

Actions:
1. Parses job output files
2. Extracts performance metrics
3. Creates job_output.parquet with:
   - Zone updates per second
   - Wall time measurements
   - Scaling efficiency
   - Memory usage

### regtest.py www

Generates web reports:
```bash
regression_testing/regtest.py www
```

Actions:
1. Scans for all INI files with useBatch=True
2. Aggregates data from all test folders
3. Creates HTML pages with:
   - Performance plots
   - Comparison tables
   - Trend analysis
   - Test status indicators
4. Includes Quokka version in titles

Note: INI file is optional for www command - it will discover all test folders automatically.

## E. Publishing Web Pages to GitHub Pages

### 1. Setup GitHub repository

Create a repository for hosting the web pages:
```bash
cd /home/agray/src/cas/quokka
git clone https://github.com/username/quokka-regression-results.git
cd quokka-regression-results
```

### 2. Enable GitHub Pages

In repository settings:
1. Go to Settings → Pages
2. Source: Deploy from a branch
3. Branch: main (or gh-pages)
4. Folder: / (root)

### 3. Copy and commit web pages

```bash
# Copy generated web pages to repository
cp -r /home/agray/src/cas/quokka/www/* ./

# Add and commit
git add .
git commit -m "Update regression test results $(date +%Y-%m-%d)"

# Push to GitHub
git push origin main
```

### 4. Automate with script

Create `publish_results.sh`:
```bash
#!/bin/bash
RESULTS_REPO="/home/agray/src/cas/quokka/quokka-regression-results"
WWW_DIR="/home/agray/src/cas/quokka/www"

cd "$RESULTS_REPO"
git pull
cp -r "$WWW_DIR"/* ./
git add .
git commit -m "Auto-update: $(date +%Y-%m-%d\ %H:%M:%S)"
git push
```

### 5. View published pages

After pushing, pages will be available at:
```
https://username.github.io/quokka-regression-results/
```

## F. Simple CI Setup

### Basic CI workflow to trigger regression tests

#### 1. GitHub Actions example (.github/workflows/regression.yml):

```yaml
name: Run Regression Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:      # Manual trigger

jobs:
  trigger-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger regression tests
        env:
          SSH_KEY: ${{ secrets.HPC_SSH_KEY }}
        run: |
          echo "$SSH_KEY" > ssh_key
          chmod 600 ssh_key
          
          # Submit tests
          ssh -i ssh_key -o StrictHostKeyChecking=no \
            agray@hpc.example.com "submit config_nt.ini"
          
          # Wait and check (simplified - real CI would loop)
          sleep 300
          ssh -i ssh_key -o StrictHostKeyChecking=no \
            agray@hpc.example.com "check config_nt.ini"
```

#### 2. GitLab CI example (.gitlab-ci.yml):

```yaml
stages:
  - test
  - report

run-regression:
  stage: test
  script:
    - echo "$HPC_SSH_KEY" > ~/.ssh/id_rsa
    - chmod 600 ~/.ssh/id_rsa
    - ssh agray@hpc.example.com "submit config_nt.ini"
    - sleep 300
    - ssh agray@hpc.example.com "check config_nt.ini"
  only:
    - schedules
    - main

generate-report:
  stage: report
  script:
    - ssh agray@hpc.example.com "extract config_nt.ini"
    - ssh agray@hpc.example.com "www"
  needs: ["run-regression"]
```

#### 3. Simple cron job on HPC:

```bash
# Add to crontab with: crontab -e
# Run regression tests daily at 2 AM
0 2 * * * cd /home/agray/src/cas/quokka/work && ./run_regression.sh

# run_regression.sh:
#!/bin/bash
source setup/env_setup_ucx.sh
source mk2025a/.venv/bin/activate

regression_testing/regtest.py submit config_nt.ini
# Wait for completion (check every 5 minutes for 2 hours)
for i in {1..24}; do
  sleep 300
  status=$(regression_testing/regtest.py check config_nt.ini | grep "Status:")
  if [[ $status == *"COMPLETE"* ]]; then
    break
  fi
done

regression_testing/regtest.py extract config_nt.ini
regression_testing/regtest.py www

# Optional: publish results
./publish_results.sh
```

### Security considerations for CI:

1. Use dedicated SSH keys with command restrictions
2. Store keys as encrypted secrets in CI platform
3. Limit key permissions to only required commands
4. Monitor usage through HPC logs
5. Rotate keys periodically

## Appendix: Configuration File Examples

### Minimal config_nt.ini:
```ini
[main]
useBatch = True
cluster = NT
scheduler = slurm
gpu_build = cuda
ntasks_per_node = 4
max_cores = 64

[test1]
name = hydro_blast
target = HydroBlast3D/test_hydro3d_blast
inputFile = blast.in
walltime = 00:10:00
```

### Environment setup script (env_setup_ucx.sh):
```bash
#!/bin/bash
module purge
module load gcc/11.2.0
module load cuda/12.0
module load openmpi/4.1.4-ucx
module load hdf5/1.14.0

export OMP_NUM_THREADS=1
export OMPI_MCA_btl=^openib
```

## Troubleshooting

### Common issues:

1. **Module not found**: Ensure environment script is sourced before running regtest.py
2. **Jobs stuck in WAIT**: Check cluster queue limits and resource availability
3. **Missing parquet files**: Ensure extract command completed successfully
4. **Web pages not updating**: Clear browser cache or use private/incognito mode
5. **SSH command fails**: Verify authorized_keys entry and key permissions (600)

### Debug commands:

```bash
# Check job details
squeue -u $USER

# View job output
cat A/performance_test/*/results/test_*/stdout.txt

# Verify parquet files
ls -la A/performance_test/*/results/*.parquet

# Test SSH restricted command
ssh -v agray@hpc.example.com "check config_nt.ini"
```

For additional help, check the regression_testing logs in `runtime_err.log` or contact the Quokka development team.