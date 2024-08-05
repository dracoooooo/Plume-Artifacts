# Artifact for "Plume: Efficient and Complete Black-box Checking of Weak Isolation Levels"

## Introduction

This artifact provides a Docker image that includes all the necessary tools and experimental data used in the paper titled "Plume: Efficient and Complete Black-box Checking of Weak Isolation Levels." 
The Docker image ensures a fully configured environment to facilitate the reproducibility of the results presented in the paper.

### Contents

The Docker image includes:

- Comparison Tools: A suite of tools required for the experiments.
- Experimental Data: Complete datasets used in the experiments.
- Reproduction Scripts: Scripts for reproducing the experimental results.

### Directory Organization

```
/plume
|-- Data                    # experimental data presented in the paper
|-- History                 # histories and benchmarks used in our experiments
|   |-- bugs                # histories for the bugs we found
|   |-- figure              # histories corresponding to the figures in the paper
|   |-- reproduce           # histories for the bugs previously found by other tools
|   `-- testcase            # 14 simple test cases corresponding to our 14 transactional anomalous patterns
|-- Dockerfile
|-- Plume                   # our prototype of Plume
|-- README.md
|-- Reproduce
|   |-- memusg
|   |-- plot_all.sh         # use this script to plot all figs after reproducing all expirments
|   |-- plot_figs.py        # use this script to plot figs
|   |-- reproduce_figs.py   # use this script to reproduce expirments of figs
|   |-- reproduce_table3.sh # use this script to reproduce expirments of table3
|   |-- reproduce_table4.sh # use this script to reproduce expirments of table4
|   |-- reproduce_table5.py # use this script to reproduce expirments of table5
|   |-- requirements.txt
|   `-- viper_config.yaml
`-- Tools                   # our implementations of the competing checkers CausalC+ and TCC-Mono and other tools
    ├── CobraVerifier       # the Cobra checker
    ├── PolySI              # the PolySI checker
    ├── Viper               # the Viper checker(latest version)
    ├── Viper_old           # the Viper checker(old version, revison number: df2343)
    ├── datalog             # our implementation of the CausalC+ checker 
    ├── dbcop               # the dbcop checker
    ├── elle-cli            # a command-line tool for Elle
    ├── elle-0.1.6          # elle-cli with elle 0.1.6
    ├── elle-0.1.9          # elle-cli with elle 0.1.9
    └── mono                # our implemention of the TCC-Mono checker
```

### Claims Supported by the Artifact

1. Plume is efficient and can handle large-scale histories. This claim is supported by experiments presented in Figures 8-13.
2. The number of TAPs (Transactional Anomalous Patterns) identified is significantly higher than the number of histories; the number of simple, yet crucial bugs are non-negligible. Both claims are supported by the results in Table 4.
3. Plume is complete while other tools rarely exhibit completeness. This claim is supported by the results in Table 5.

## Hardware Dependencies

To evaluate the artifact, the following hardware is required:

- **Memory**: At least 50GB RAM for reproducing Figure 13 experiments. The maximum memory used by other experiments is approximately 10GB.
- **Storage**: At least 13GB of disk space for the Docker image.
- **CPU architecture**: The Docker image is based on the amd64 architecture. Running this Docker image on ARM or other CPU architectures may result in errors or performance issues.

## Getting Started Guide

### Prerequisites

- Docker installed on your system.

### Setup Instructions

1. **Load the Docker image:**

    ```bash
    docker load -i plume-artifacts.tar
    ```

    Or pull the Docker image from GitHub Container Registry:

    ```bash
    docker pull ghcr.io/dracoooooo/plume-artifacts:main
    ```

2. **Run the Docker container:**

    ```bash
    docker run -it ghcr.io/dracoooooo/plume-artifacts:main
    ```

3. **Basic Testing:**

    After running the Docker container, you will have access to a pre-configured environment containing all the tools and datasets.
    Navigate to the `/plume/Reproduce` directory inside the Docker container:

    ```bash
    cd /plume/Reproduce
    ```

    Try running the reproduction script to ensure everything is set up correctly:

    ```bash
    python3 reproduce_figs.py
    ```
   
   The following output is expected:

    ```bash
   usage: reproduce_figs.py [-h] [--timeout TIMEOUT] {fig8,fig9,fig10,fig11,fig12,fig13}
   reproduce_figs.py: error: the following arguments are required: experiment_group
    ```

## Step-by-Step Instructions

### Reproducing the Experiments of Figures

1. **Navigate to the reproduce directory:**

    ```bash
    cd /plume/Reproduce
    ```

2. **Run the reproduction script:**

    Use the provided Python script to reproduce the results for specific figures from the paper:

    ```bash
    python3 reproduce_figs.py <figure>
    ```

    Replace `<figure>` with the desired figure identifier (e.g., `fig8`, `fig9`, `fig10`, `fig11`, `fig12`, `fig13`). For example, to reproduce the results for Figure 8:

    ```bash
    python3 reproduce_figs.py fig8
    ```

   When the execution is complete, the results (e.g. `fig8a_results.csv`) will be generated in the `Reproduce` folder.

    **Notes:**

    - Reproducing Figure 13 results requires at least 50GB memory.
    - Reproducing the results for Figure 8, Figure 9, Figure 10, Figure 12, and Figure 13 with the default configuration takes several hours, and Figure 11 takes about 20 minutes. This is due to some comparison tools timing out at large test inputs.
    - The default timeout for each tool is 10 minutes. Modify the timeout by passing the `--timeout` parameter.
    - You can use `vim` (already installed in this image) to modify the configuration in the `run_experiments` function of `reproduce_figs.py` to selectively run a few sets of experiments. 
For example, to only use Plume to reproduce the experiments. If you only use Plume, the time to reproduce the results for each figure will be reduced to a few minutes.


3. **Plot the figures:**
After reproducing all the experiments, run the following script to plot all the figures:
```bash
./plot_all.sh
```
This script takes all the `figX_results.csv` output from the previous step as input and produces `figX_result.png` as output.

If you need to plot a single figure separately, you can directly use `plot_figs.py`:
```bash
python3 plot_figs.py <csv_filename> <chart_type>
```
Replace `<csv_filename>` with one of the CSV output files from the second step, and replace `<chart_type>` with either `line` or `bar` to indicate a line chart or a bar chart respectively. For example:
```bash
python3 plot_figs.py fig8a_results.csv line
```
The output should be "Chart saved as fig8a_results.png", and you can find `fig8a_results.png` in the `Reproduce` folder.

### Reproducing the Experiments of Tables

**Navigate to the reproduce directory:**

```bash
cd /plume/Reproduce
```

**Reproduce Table 3:**

Run the following command to reproduce the results of Table 3:

```bash
./reproduce_table3.sh
```

Running the script takes a few seconds. The result (`table3.csv`) will be generated in the `Reproduce` folder.

**Reproduce Table 4:**

Run the following command to reproduce the results of Table 4:

```bash
./reproduce_table4.sh
```

Running the script takes about 30 seconds. The result (`table4.csv`) will be generated in the `Reproduce` folder.

Note that as we continued to improve the quality of our codebase after the paper notification, we fixed a bug in counting the number of TAPs. As a result, the numbers of some TAPs shown in 
Table 4 have been adjusted. The correct data is: 

| TAP    | TAP-a | TAP-b | TAP-c | TAP-d | TAP-e | TAP-f | TAP-g | TAP-h | TAP-i | TAP-j | TAP-k | TAP-l | TAP-m | TAP-n | #TAPs | #Hist |
|--------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|
| Count  | 0     | 3     | 1     | 71    | 0     | 1     | 2     | 103   | 2929  | 14    | 1655  | 2920  | 3079  | 2973  | 13751 | 3100  |


However, this does not invalidate our two claims from this table:
1. "The number of identified TAPs is far more than the number of histories." Previously, we had 12270 (#TAPs) vs 3100 (#hists) in the submission; now, it is 13751 vs 3100.
2. "the number of simple, yet crucial bugs are non-negligible." Previously, we had 95 in the submission; now it is 92.

Note also that this bug does not affect other experimental results.

**Reproduce Table 5:**

Run the following command to let the tools execute the test cases:

```bash
python3 reproduce_table5.py
```

Running the script takes a few minutes. The outputs of the tools will be recorded in `/Reproduce/table5.json`.

Manual analysis of the tool's output is required. The expected result for each test case is either false or reject. 
If a tool returns true or accepts a test case, it indicates that the tool has failed that test case.

However, there may be instances where a hist does not have a corresponding format for a tool, or the tool encounters an error during execution. 
In these cases, we will analyze the tool's code and the paper to determine whether the tool has passed the test case.

## Reusability Guide

**Core Components:**

- **Plume**: Our implementation of the Plume algorithm is in the source code located at `/plume/Plume`.

**Adapting to New Inputs:**

If you only need to build Plume, use the following command to install the required packages on Ubuntu 22.04:

1. **Install Required Packages:**

    ```bash
    apt install openjdk-11-jdk maven
    ```

2. **Build Plume:**

    Navigate to the Plume source code directory:

    ```bash
    cd /plume/Plume
    ```

    Use maven to build the Plume jar:

    ```bash
    mvn package -DskipTests
    ```

3. **Run Plume:**

    ```bash
    java -jar /plume/Plume/target/Plume-1.0-SNAPSHOT-shaded.jar
    ```

    If you see the following output, Plume has been successfully built:

    ```bash
    Missing required parameter: '<file>'
    Usage: Plume [-hV] [--count-dfs] [--enable-graphviz] [-i=<isolationLevel>]
                 [-t=<algType>] <file>
    Check if the history satisfies transactional causal consistency.

          <file>              Input file
          --count-dfs         Record DFS count
          --enable-graphviz   Use graphviz to visualize violation
      -h, --help              Show this help message and exit.
      -i=<isolationLevel>     Candidates: RC, RA, TCC
      -t=<algType>            Candidates: PLUME, PLUME_WITHOUT_TC,
                                PLUME_WITHOUT_VEC, PLUME_LIST
      -V, --version           Print version information and exit.
    ```

## Additional Information

### History Folder Naming Convention

The folders under `History/figure/fig_8_9` and `History/figure/fig_13` are named following a specific convention that encodes key parameters of the dataset or experiment configuration. 
The naming pattern is as follows:

```
<session_count>_<transactions_per_session>_<read_ratio>_<total_keys>_<key_distribution>_<operations_per_transaction>
```

Here's a breakdown of each component:

1. session_count: The number of sessions included in the history.
2. transactions_per_session: The number of transactions in each session.
3. read_ratio: The ratio of read operations to the total operations.
4. total_keys: The total number of unique keys in the history.
5. key_distribution: The distribution pattern of the keys accessed during the transactions.
6. operations_per_transaction: The number of operations in each transaction.

**Example**

A folder named `25_200_0.5_6000_uniform_20` would be interpreted as:

- `25` sessions
- `200` transactions per session
- `0.5` read ratio (50% read operations)
- `6000` total unique keys
- `uniform` key distribution
- `20` operations per transaction

### History Subfolders
Within each history folder, there are several subfolders that represent different input formats for the history data. These subfolders include:

- dbcop
- text
- viper

Although the format of the history data differs in each of these subfolders, the content they represent is identical. 

For more details on the experiments, tools, and datasets, please refer to the [github repository](https://github.com/dracoooooo/Plume-Artifacts).
