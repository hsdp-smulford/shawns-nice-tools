### AWS

This repository contains various Python and other scripts. The repository is configured to streamline development and ensure consistent environments using `.python-version` and `pyproject.toml`.

---

#### Prerequisites

1. **Install pyenv**

   Install and set up pyenv by following [pyenv's installation guide](https://github.com/pyenv/pyenv#installation).

   ```bash
   curl https://pyenv.run | bash
   ```

2. **Install Poetry**

    Dependency management is handled by Poetry. Install Poetry globally:

    ```bash
    curl -sSL https://install.python-poetry.org | python3 -
    ```

#### Setup

1. **Set up Python**
    Ensure the required Python version (specified in [.python-version](../.python-version)) is installed using pyenv from this directory:

    ```bash
    pyenv install
    pyenv local
    ```

2. **Install dependencies**
Use Poetry to install the dependencies specified in [pyproject.toml](../pyproject.toml):

    ```bash
    poetry install
    ```

#### Linting and Code Quality

To maintain high code quality, consider integrating Ruff (a fast Python linter).

``` bash
poetry run ruff check .
```

feeling lucky? let ruff fix it.

```bash
poetry run ruff check . --fix
```

#### Script Summaries

* [`find-lambdas.py`](./find-lambdas.py): This script scans multiple AWS accounts and regions to find Lambda functions with a specific suffix. It outputs a summary table of the results.

#### Scripts

##### [`find-lambdas.py`](./find-lambdas.py) 🐍

This script scans multiple AWS accounts and regions to find Lambda functions with a specific suffix. It outputs a summary table of the results.

**Usage**

```bash
./find-lambdas.py
```

**Configuration**
The script relies on [config.toml](./config.toml) file for its configuration. Below are the key configuration options:

``` plaintext
[aws]
payer_profile_name = ""  # AWS profile name for the payer account
lambda_suffix = ""  # Suffix to match against Lambda function names
regions = ["us-east-1""]  # List of AWS regions to scan
management_account_ids = [""]  # List of management account IDs
management_role_name = ""  # Role name to assume in the management account
execution_role_name = ""  # Role name to assume in the target accounts
account_ids = []  # List of specific account IDs to scan (optional)
ignored_account_ids = []  # List of account IDs to ignore (optional)
```

**Example Output**
The script outputs a summary table of the results, showing the number of matching Lambda functions in each region for each account.

``` plaintext
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━┳━━━━━━┳━━━━━━┳━━━━━━┳━━━━━━┳━━━━━━━┳━━━━━━┳━━━━━━━┳━━━━━━┳━━━━━━┓
┃ Account ID   ┃ Account Name ┃ aps1 ┃ cac1 ┃ usw1 ┃ usw2 ┃ euw2 ┃ euw1 ┃ apne1 ┃ sae1 ┃ apse2 ┃ use1 ┃ use2 ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━╇━━━━━━╇━━━━━━╇━━━━━━╇━━━━━━╇━━━━━━━╇━━━━━━╇━━━━━━━╇━━━━━━╇━━━━━━┩
│ 123456789012 │ Example Acc  │  -   │  1   │  -   │  2   │  -   │  -   │   -   │  -   │   -   │  1   │  -   │
│ 234567890123 │ Another Acc  │  -   │  -   │  -   │  -   │  -   │  -   │   -   │  -   │   -   │  -   │  -   │
└──────────────┴──────────────┴──────┴──────┴──────┴──────┴──────┴──────┴───────┴──────┴───────┴──────┴──────┘
```

**Logging**
The script uses [logging.conf](./logging.conf) file to configure logging. Customize the log levels or output formats as needed.

#### Configuration Files

* [`.python-version`](../.python-version): Specifies the Python version for the project.
* [`pyproject.toml`](../pyproject.toml): Dependency and configuration management for the project.
* **`config.toml`**: General configuration for the project. Update parameters as needed.
* **`logging.conf`**: Logging configuration for the scripts. Customize log levels or output formats.
