# Quokka Regression Testing Documentation

## Setup

The script `quokka-setup.sh` illustrates the configuration of regression testing
*via* a batch queue. This file explains how this script works.
`quokka-setup.sh` has been tested on Ngarrgu-Tindebeek. An environment configuration
script, QUOKKA input files, and test configurations to illustrate the tests
are provided in `quokka-setup.tar.xz`. To use these files put them together
in an empty folder on Ngarrgu-Tindebeek and run the script. Alternative
environment module scripts are provided in the `hpc_performance_testing` repository at 

```
https://github.com/ADACS-Australia/MKrumholz_2025a.git
```

This repository contains a `pyproject.toml` file suitable
for use with `poetry` versions 2.x.

### Setup Virtual Environment

The following lines from `quokka-setup.sh` creates a virtual
environment, clones the repository, and installs dependencies.

```bash
VENV=verse
HPC_PERF_TEST=https://github.com/ADACS-Australia/MKrumholz_2025a.git
HPC_PERF_TEST_BRANCH=batch_test

module load load gcc/12.3.0 python/3.11.3
python -m venv ${VENV}
source ${VENV}/bin/activate
pip install --upgrade pip
pip install poetry

git clone -b ${HPC_PERF_TEST_BRANCH} ${HPC_PERF_TEST} hpc_performance_testing
cd hpc_performance_testing || exit 1

poetry lock
POETRY_VIRTUALENVS_CREATE=false poetry install
source "${VENV_ABSOLUTE_PATH}/bin/activate"
```

### Unpack environment script and inputs

The following code unpacks the `quokka-setup.tar.xz` repository and
configures the environment module script to use the virtual
environment configured above.

```bash
cd ../
tar Jxvf quokka-setup.tar.xz
VENV_ABSOLUTE_PATH=$(realpath -e ${VENV}/)
echo source "${VENV_ABSOLUTE_PATH}/bin/activate" >> setup/env.sh
```

### Install the regression testing code

Now install the modified regression testing code that will be 
remotely activated.

```bash
REG_TEST=https://github.com/ADACS-Australia/regression_testing.git
REG_TEST_BRANCH=mk2025a

git clone -b "${REG_TEST_BRANCH}" "${REG_TEST}" regression_testing
```

### Test configuration

Place test configuration INI files in the folder where the above setup
was performed. Example files are provided in `quokka-setup.tar.xz`. These
files are identical except for their working folders. Multiple configurations
are included to show thow these are handled in the web report.


### Setup authorized_keys for Remote Execution

The regression testing system can be triggered remotely using SSH with restricted keys. This allows CI systems or remote users to run tests securely.

#### Example authorized_keys entry:

A complete example is provided in `authorized_keys_example`:

```
command="bash -l -c 'set -e; cd ${HOME}/src/cas/quokka/remote; [ -f setup/env.sh ] && source setup/env.sh; exec python regression_testing/regtest.py'",restrict ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFG21CqFMHf3gAt6dui9XkGbXDjenzvUJkgiRCYNQJK9 quokka
```
Some notes on security:

- The `restrict` option is the modern way to apply all security restrictions at once
- The command restriction ensures the SSH key can ONLY run regtest.py
- Using `exec` replaces the shell process, preventing shell escape attempts
- The `set -e` ensures the command chain stops on any error
- Environment setup is optional but allows module loading if needed

The script `quokka-setup.sh` sets up this restricted key in your
`~/.ssh/authorized_keys` using the key configured by a line like:

```bash
KEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFG21CqFMHf3gAt6dui9XkGbXDjenzvUJkgiRCYNQJK9 quokka'
```

#### Key components explained:

Note that `quokka-setup.sh` configures the path used here.

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

#### Setting up the restricted key:

1. **Add to ~/.ssh/authorized_keys**:

```bash
cat authorized_keys_example >> ~/.ssh/authorized_keys
```

2. **Adjust the path in the command**:

Replace `${HOME}/src/cas/quokka/remote` with your actual work directory.
The example uses `remote/` subdirectory for isolation. This folder is
set if you use `quokka-setup.sh`.

3. **Use a configure file to simplify remote commands**

The following lines in `~/.ssh/config` allow the use of `quokka` as a destination
in `ssh` commands without explicitly giving a URL or key. 

```
Host quokka
    User            agray
    HostName        tooarrana2.hpc.swin.edu.au
    Port            22
    IdentityFile    ~/.ssh/cas/id_ed25519-quokka
```

#### Valid remote commands

When the SSH key is properly configured, remote commands are automatically
passed to regtest.py via SSH_ORIGINAL_COMMAND:

```bash
# From remote system (the SSH command is parsed from SSH_ORIGINAL_COMMAND)
ssh quokka "regtest.py setup config_nt.ini"
ssh quokka "regtest.py submit config_nt.ini"
ssh quokka "regtest.py check config_nt.ini" 
ssh quokka "regtest.py extract config_nt.ini"
ssh quokka "regtest.py www"  # INI file optional for www
```

The `regtest.py` script automatically detects it's running via SSH and parses
the command from the `SSH_ORIGINAL_COMMAND` environment variable.


## Running regtest Commands

This section provides a short description of each command available through
the `regression_testing/` repository.
Note that as noted above you omit the `regression_tesing/` part of the command
when using the remote execution setup described above. 

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


## Simple CI Setup

A version of `quokka` with a GitHub action is configured
at `https://github.com/gusgw/quokka-ci-demo/`. This has
the following file at `.github/workflows/regression-submit.yml`.

```
name: Submit Regression Tests
on:
  push:
    branches:
      - development
jobs:
  submit-regression-tests:
    name: Submit tests to HPC
    runs-on: ubuntu-latest

    steps:
      - name: Setup SSH
        run: |
          # Create SSH directory
          mkdir -p ~/.ssh

          # Add the private key
          echo "${{ secrets.QUOKKA_SSH_KEY }}" > ~/.ssh/id_ed25519-quokka
          chmod 600 ~/.ssh/id_ed25519-quokka

          # Add known hosts
          echo "${{ secrets.QUOKKA_KNOWN_HOSTS }}" > ~/.ssh/known_hosts

          # Create SSH config
          cat > ~/.ssh/config << 'EOF'
          Host quokka
              User            agray
              HostName        tooarrana2.hpc.swin.edu.au
              Port            22
              IdentityFile    ~/.ssh/id_ed25519-quokka
              StrictHostKeyChecking yes
          EOF
          chmod 600 ~/.ssh/config

      - name: Submit regression tests
        run: |
          echo "Submitting regression tests to HPC..."
          ssh quokka "regtest.py submit config_nt_0.ini"
          echo "✓ Regression tests submitted successfully"
```

### Setting up GitHub Secrets for SSH Access

To securely connect to your HPC cluster from GitHub Actions, you need to configure two secrets: `QUOKKA_SSH_KEY` and `QUOKKA_KNOWN_HOSTS`. These secrets store sensitive SSH credentials securely.

#### Step-by-step setup:

1. **Generate an SSH key pair** (if you haven't already):
   ```bash
   ssh-keygen -t ed25519 -C "quokka-ci" -f ~/.ssh/id_ed25519-quokka -N ""
   ```
   This creates two files: `id_ed25519-quokka` (private) and `id_ed25519-quokka.pub` (public)

2. **Add the public key to HPC authorized_keys**:
   ```bash
   # On your HPC system, add the restricted command entry:
   cat ~/.ssh/id_ed25519-quokka.pub | ssh tooarrana2.hpc.swin.edu.au \
     "cat >> ~/.ssh/authorized_keys"
   ```
   Then modify the entry on the HPC to add command restrictions as shown in the authorized_keys section above.

3. **Get the HPC host's SSH fingerprint**:
   ```bash
   ssh-keyscan -H tooarrana2.hpc.swin.edu.au > known_hosts_temp
   # Verify the fingerprint matches your HPC system's actual fingerprint
   ```

4. **Create the GitHub secrets**:
   - Go to your GitHub repository (e.g., https://github.com/gusgw/quokka-ci-demo)
   - Navigate to **Settings** → **Secrets and variables** → **Actions**
   - Click **New repository secret**

5. **Add QUOKKA_SSH_KEY secret**:
   - Name: `QUOKKA_SSH_KEY`
   - Secret: Copy the entire contents of your private key:
   ```bash
   cat ~/.ssh/id_ed25519-quokka
   # Copy everything including -----BEGIN and -----END lines
   ```
   - Click "Add secret"

6. **Add QUOKKA_KNOWN_HOSTS secret**:
   - Name: `QUOKKA_KNOWN_HOSTS`
   - Secret: Copy the contents of the known_hosts file:
   ```bash
   cat known_hosts_temp
   # Copy the entire output
   ```
   - Click "Add secret"

7. **Test the workflow**:
   - Push a commit to the development branch
   - Check Actions tab in GitHub to see if the workflow runs successfully
   - Verify on HPC that jobs were submitted

#### Security notes:
- Never commit private keys to your repository
- Use repository secrets for all sensitive data
- Consider using environment-specific secrets for different HPC systems
- Rotate SSH keys periodically
- Limit the SSH key permissions using command restrictions in authorized_keys

For more details, see the [GitHub documentation on encrypted secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets).

## Folder Structure

The complete regression testing environment in `/home/agray/src/cas/quokka-test/`:

```
quokka-test/
├── config0/, config1/, config2/   # Test configuration directories
│   ├── performance_test/          # Test run outputs
│   │   └── 20250929171957/       # Timestamp directory
│   │       ├── quokka/           # Quokka source clone
│   │       ├── results/          # Performance data (parquet files)
│   │       └── test_*/           # Individual test outputs
│   ├── tests_input/              # Test input files
│   │   ├── blast_32.in
│   │   ├── blast_unigrid_128_regression.in
│   │   └── radhydro_shell_128.in
│   ├── config.yaml               # Converted YAML for hpc_performance_testing
│   ├── env.sh                    # Environment setup script
│   └── test_instance.yaml        # Job submission metadata
│
├── hpc_performance_testing/       # MKrumholz_2025a package (batch_test branch)
│   ├── cli/                      # Command-line interface
│   │   └── pipeline.py           # Main CLI entry point
│   ├── config_yaml/              # Example configurations
│   │   ├── config_nt.yaml        # Ngarrgu-Tindebeek config
│   │   ├── config_gadi.yaml      # Gadi config
│   │   ├── config_setonix.yaml   # Setonix config
│   │   └── config_frontier.yaml  # Frontier config
│   ├── hpc_env/                  # Environment setup scripts
│   ├── python/                   # Python package source
│   │   └── hpc_performance_testing/
│   ├── pyproject.toml            # Poetry configuration with dependencies
│   └── poetry.lock               # Locked dependency versions
│
├── regression_testing/            # Regression testing scripts (mk2025a branch)
│   ├── regtest.py               # Main test orchestration script
│   ├── web_generator.py         # HTML report generation
│   ├── plotting.py              # Performance plotting (matplotlib)
│   ├── plotting_plotly.py       # Interactive plots (plotly)
│   ├── web_utils.py             # Web generation utilities
│   ├── comparison.py            # Performance comparison logic
│   ├── trend_analysis.py        # Trend analysis over time
│   ├── web_styling.py           # CSS and HTML templates
│   ├── web_logging.py           # Logging utilities
│   ├── BATCH.md                 # This documentation
│   ├── authorized_keys_example  # SSH key setup example
│   └── requirements.txt         # Python dependencies
│
├── setup/                        # Shared environment configuration
│   ├── env.sh                   # Module loading script
│   └── tests_input/             # Shared test input files
│
├── verse/                        # Python virtual environment
│   ├── bin/                     # Python executables and scripts
│   ├── lib/python3.11/          # Installed packages
│   └── pyvenv.cfg               # Virtual environment config
│
├── venv -> verse                 # Symlink for compatibility
│
├── www/                          # Generated web reports
│   ├── index.html               # Main dashboard
│   ├── assets/                  # Static assets (CSS, JS)
│   └── config0/, config1/, config2/  # Per-config reports
│       ├── index.html           # Config summary
│       ├── trends.html          # Performance trends
│       └── 20250929171957/      # Timestamp-specific reports
│           └── index.html       # Detailed test results
│
├── config_nt_0.ini              # Test configuration 0
├── config_nt_1.ini              # Test configuration 1
├── config_nt_2.ini              # Test configuration 2
├── quokka-setup.sh              # Automated setup script
├── quokka-setup.tar.xz          # Setup archive with env scripts
└── runtime_err.log              # Error log from test runs
```

### Key components:

- **config*/** - Working directories for different test configurations, each containing:
  - Performance test outputs with timestamps
  - Test input files
  - Generated YAML configurations
  - Job submission metadata

- **hpc_performance_testing/** - The batch job submission framework:
  - Handles SLURM/PBS job submission
  - Manages performance data extraction
  - Creates parquet files for analysis

- **regression_testing/** - Test orchestration and reporting:
  - Coordinates setup, submit, check, extract, www workflow
  - Generates HTML reports with plots and tables
  - Handles remote execution via SSH

- **verse/** - Consolidated Python environment with all dependencies:
  - hpc_performance_testing package
  - matplotlib, numpy, pandas for analysis
  - plotly for interactive visualization
  - PyYAML for configuration handling

- **www/** - Web-accessible test results:
  - Performance plots and comparison tables
  - Trend analysis across multiple runs
  - Organized by configuration and timestamp