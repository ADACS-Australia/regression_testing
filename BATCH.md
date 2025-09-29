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

## Folder Structure

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