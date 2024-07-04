import argparse
import csv
import os
import re
import signal
import subprocess
import threading
import time

import psutil

# Define the command line templates for the tools, their input folder names, and the regex patterns to extract segment times
ALL_TOOLS = {
    "Plume_TCC": {
        "command": "java -jar /plume/Plume/target/Plume-1.0-SNAPSHOT-shaded.jar -i TCC -t PLUME --count-dfs {input_path}",
        "input_folder": "text",
        "segments": {
            "construction": r"Construction: (\d+)ms",
            "traversal": r"Traversal: (\d+)ms",
        },
        "dfs_count": r"DFS count: (\d+)"
    },
    "PolySI": {
        "command": "java -jar /plume/Tools/PolySI/build/libs/PolySI-1.0.0-SNAPSHOT.jar audit -t TEXT {input_path}",
        "input_folder": "text",
        "segments": {
            "construction": r"ONESHOT_CONS: (\d+)ms",
            "encoding": r"ONESHOT_ENCODING: (\d+)ms",
            "solving": r"ONESHOT_SOLVE: (\d+)ms",
        }
    },
    "Viper": {
        "command": "python3 /plume/Tools/Viper/src/main_allcases.py --config_file /plume/Reproduce/viper_config.yaml --sub_dir {input_path} --strong-session --perf_file /tmp/test_perf.txt --exp_name test_run",
        "input_folder": "viper",
        "segments": {
            "encoding": r"encoding: (\d+) ms",
            "solving": r"solving: (\d+) ms",
        }
    },
    "dbcop_TCC": {
        "command": "/plume/Tools/dbcop/target/release/dbcop verify -c cc --ver_dir {input_path} --out_dir /tmp",
        "input_folder": "dbcop",
        "segments": {
            "construction": r"construction: (\d+) ms",
            "traversal": r"traversal: (\d+) ms",
        }
    },
    "TCC-Mono": {
        "command": "python3 /plume/Tools/mono/run_mono_txn.py {input_path}",
        "input_folder": "text",
        "segments": {
            "construction": r"construction: (\d+) ms",
            "encoding": r"encoding: (\d+) ms",
            "solving": r"solving: (\d+) ms",
        }
    },
    "CausalC+": {
        "command": "python3 /plume/Tools/datalog/clingo_txn.py {input_path}",
        "input_folder": "text",
        "segments": {
            "construction": r"construction: (\d+) ms",
            "encoding": r"encoding: (\d+) ms",
            "solving": r"solving: (\d+) ms",
        }
    },
    "Plume_TCC_List": {
        "command": "java -jar /plume/Plume/target/Plume-1.0-SNAPSHOT-shaded.jar -i TCC -t PLUME_LIST {input_path}",
        "input_folder": "elle",
        "segments": {
            "construction": r"Construction: (\d+)ms",
            "traversal": r"Traversal: (\d+)ms",
        }
    },
    "Elle_TCC": {
        "command": "java -jar /plume/Tools/elle-cli/elle-cli-0.1.7-standalone.jar -s 100000000 -m list-append -c causal-cerone {input_path}",
        "input_folder": "elle",
        "segments": {
            "construction": r"Stage construction Time: (\d+) ms",
            "traversal": r"Stage cycle-search Time: (\d+) ms",
        }
    },
    "Plume_TCC_Without_TC": {
        "command": "java -jar /plume/Plume/target/Plume-1.0-SNAPSHOT-shaded.jar -i TCC -t PLUME_WITHOUT_TC {input_path}",
        "input_folder": "text",
    },
    "Plume_TCC_Without_VC": {
        "command": "java -jar /plume/Plume/target/Plume-1.0-SNAPSHOT-shaded.jar -i TCC -t PLUME_WITHOUT_VEC --count-dfs {input_path}",
        "input_folder": "text",
        "dfs_count": r"DFS count: (\d+)"
    },
    "Plume_TCC_Large_Memory": {
        "command": "java -Xms50G -Xmx50G -jar /plume/Plume/target/Plume-1.0-SNAPSHOT-shaded.jar -i TCC -t PLUME {input_path}",
        "input_folder": "text",
    },
    "Plume_RC_Large_Memory": {
        "command": "java -Xms50G -Xmx50G -jar /plume/Plume/target/Plume-1.0-SNAPSHOT-shaded.jar -i RC -t PLUME {input_path}",
        "input_folder": "text",
    },
    "Plume_RA_Large_Memory": {
        "command": "java -Xms50G -Xmx50G -jar /plume/Plume/target/Plume-1.0-SNAPSHOT-shaded.jar -i RA -t PLUME {input_path}",
        "input_folder": "text",
    },
}

# Timeout duration (seconds)
TIMEOUT = 600
CHECK_INTERVAL = 0.5  # Memory usage check interval (seconds)


def monitor_memory(process, memory_usage):
    try:
        while process.is_running():
            mem_info = process.memory_info().rss
            for child in process.children(recursive=True):
                mem_info += child.memory_info().rss
            if mem_info > memory_usage[0]:
                memory_usage[0] = mem_info
    except psutil.NoSuchProcess:
        pass


def kill_process_tree(pid, including_parent=True):
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            os.kill(child.pid, signal.SIGTERM)
        if including_parent:
            os.kill(pid, signal.SIGTERM)
    except psutil.NoSuchProcess:
        pass


def run_tool(tool, command, input_path, record_time, record_memory, record_segments, record_dfs):
    try:
        formatted_command = command.format(input_path=input_path)
        print(f"Running {tool} with command: {formatted_command}")

        start_time = time.time()
        process = subprocess.Popen(formatted_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        proc = psutil.Process(process.pid)
        memory_usage = [0]

        if record_memory:
            monitor_thread = threading.Thread(target=monitor_memory, args=(proc, memory_usage))
            monitor_thread.start()

        try:
            stdout, stderr = process.communicate(timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            print(f"{tool} on {input_path} timed out. Killing the process...")
            kill_process_tree(process.pid, True)
            stdout, stderr = process.communicate()

        end_time = time.time()
        elapsed_time = end_time - start_time if record_time else None

        if record_memory:
            monitor_thread.join()
            max_memory_usage = memory_usage[0]
        else:
            max_memory_usage = None

        combined_output = stdout.decode() + "\n" + stderr.decode()
        segment_times = extract_segment_times(tool, combined_output) if record_segments else {}
        dfs_count = extract_dfs_count(tool, combined_output) if record_dfs else None

        return max_memory_usage, elapsed_time, segment_times, dfs_count
    except Exception as e:
        print(f"Error running {tool} on {input_path}: {e}")
        return None, None, {}, None


def extract_segment_times(tool, output):
    segment_times = {}
    if tool in ALL_TOOLS and "segments" in ALL_TOOLS[tool]:
        for segment, pattern in ALL_TOOLS[tool]["segments"].items():
            match = re.search(pattern, output)
            if match:
                segment_times[segment] = float(match.group(1)) / 1000
    return segment_times


def extract_dfs_count(tool, output):
    if tool in ALL_TOOLS and "dfs_count" in ALL_TOOLS[tool]:
        pattern = ALL_TOOLS[tool]["dfs_count"]
        match = re.search(pattern, output)
        if match:
            return int(match.group(1))
    return None


def run_experiments(experiment_group):
    base_dir = "/plume/History/figure"
    configurations = {
        "fig8": {
            "fig8a": {
                "dirs": ["fig_8_9/2_200_0.5_10000_uniform_20", "fig_8_9/5_200_0.5_10000_uniform_20",
                         "fig_8_9/10_200_0.5_10000_uniform_20", "fig_8_9/15_200_0.5_10000_uniform_20",
                         "fig_8_9/20_200_0.5_10000_uniform_20", "fig_8_9/25_100_0.5_10000_uniform_20",
                         "fig_8_9/30_200_0.5_10000_uniform_20",
                         "fig_8_9/40_200_0.5_10000_uniform_20", "fig_8_9/50_200_0.5_10000_uniform_20"],
                "tools": ["Plume_TCC", "PolySI", "Viper", "dbcop_TCC", "TCC-Mono", "CausalC+"],
                "record_time": True
            },
            "fig8b": {
                "dirs": ["fig_8_9/25_100_0.5_10000_uniform_20", "fig_8_9/25_200_0.5_10000_uniform_20",
                         "fig_8_9/25_300_0.5_10000_uniform_20", "fig_8_9/25_400_0.5_10000_uniform_20",
                         "fig_8_9/25_500_0.5_10000_uniform_20"],
                "tools": ["Plume_TCC", "PolySI", "Viper", "dbcop_TCC", "TCC-Mono", "CausalC+"],
                "record_time": True
            },
            "fig8c": {
                "dirs": ["fig_8_9/25_200_0.5_10000_uniform_10",
                         "fig_8_9/25_200_0.5_10000_uniform_20",
                         "fig_8_9/25_200_0.5_10000_uniform_30",
                         "fig_8_9/25_200_0.5_10000_uniform_40",
                         "fig_8_9/25_200_0.5_10000_uniform_50"],
                "tools": ["Plume_TCC", "PolySI", "Viper", "dbcop_TCC", "TCC-Mono", "CausalC+"],
                "record_time": True
            },
            "fig8d": {
                "dirs": ["fig_8_9/25_200_0.5_10000_zipf_20",
                         "fig_8_9/25_200_0.5_10000_hotspot_20",
                         "fig_8_9/25_200_0.5_10000_uniform_20"],
                "tools": ["Plume_TCC", "PolySI", "Viper", "dbcop_TCC", "TCC-Mono", "CausalC+"],
                "record_time": True
            },
            "fig8e": {
                "dirs": ["fig_12/rubis-10000",
                         "fig_12/tpcc-10000",
                         "fig_12/twitter-10000"],
                "tools": ["Plume_TCC", "PolySI", "Viper", "dbcop_TCC", "TCC-Mono", "CausalC+"],
                "record_time": True
            },
        },
        "fig9": {
            "fig9a": {
                "dirs": ["fig_8_9/2_200_0.5_10000_uniform_20", "fig_8_9/5_200_0.5_10000_uniform_20",
                         "fig_8_9/10_200_0.5_10000_uniform_20", "fig_8_9/15_200_0.5_10000_uniform_20",
                         "fig_8_9/20_200_0.5_10000_uniform_20", "fig_8_9/25_100_0.5_10000_uniform_20",
                         "fig_8_9/30_200_0.5_10000_uniform_20",
                         "fig_8_9/40_200_0.5_10000_uniform_20", "fig_8_9/50_200_0.5_10000_uniform_20"],
                "tools": ["Plume_TCC", "PolySI", "Viper", "dbcop_TCC", "TCC-Mono", "CausalC+"],
                "record_memory": True
            },
            "fig9b": {
                "dirs": ["fig_8_9/25_100_0.5_10000_uniform_20", "fig_8_9/25_200_0.5_10000_uniform_20",
                         "fig_8_9/25_300_0.5_10000_uniform_20", "fig_8_9/25_400_0.5_10000_uniform_20",
                         "fig_8_9/25_500_0.5_10000_uniform_20"],
                "tools": ["Plume_TCC", "PolySI", "Viper", "dbcop_TCC", "TCC-Mono", "CausalC+"],
                "record_memory": True
            },
            "fig9c": {
                "dirs": ["fig_8_9/25_200_0.5_10000_uniform_10",
                         "fig_8_9/25_200_0.5_10000_uniform_20",
                         "fig_8_9/25_200_0.5_10000_uniform_30",
                         "fig_8_9/25_200_0.5_10000_uniform_40",
                         "fig_8_9/25_200_0.5_10000_uniform_50"],
                "tools": ["Plume_TCC", "PolySI", "Viper", "dbcop_TCC", "TCC-Mono", "CausalC+"],
                "record_memory": True
            }
        },
        "fig10": {
            "fig10a": {
                "dirs": ["fig_10/sess2", "fig_10/sess5", "fig_10/sess10",
                         "fig_10/sess15", "fig_10/sess20", "fig_10/sess25",
                         "fig_10/sess30", "fig_10/sess40", "fig_10/sess50",
                         "fig_10/sess60", "fig_10/sess70", "fig_10/sess80",
                         "fig_10/sess90", "fig_10/sess100"],
                "tools": ["Plume_TCC_List", "Elle_TCC"],
                "record_time": True
            },
            "fig10b": {
                "dirs": ["fig_10/txns-per-session100", "fig_10/txns-per-session200",
                         "fig_10/txns-per-session300", "fig_10/txns-per-session400",
                         "fig_10/txns-per-session500"],
                "tools": ["Plume_TCC_List", "Elle_TCC"],
                "record_time": True,
            },
        },
        "fig11": {
            "fig11a": {
                "dirs": ["fig_11"],
                "tools": ["Plume_TCC", "PolySI", "Viper", "TCC-Mono", "CausalC+"],
                "record_segments": True
            },
            "fig11b": {
                "dirs": ["fig_11"],
                "tools": ["Plume_TCC", "dbcop_TCC"],
                "record_segments": True
            },
            "fig11c": {
                "dirs": ["fig_11"],
                "tools": ["Plume_TCC_List", "Elle_TCC"],
                "record_segments": True
            },
        },
        "fig12": {
            "fig12a": {
                "dirs": ["fig_12/GeneralRH", "fig_12/GeneralRW", "fig_12/GeneralWH",
                         "fig_12/rubis-10000", "fig_12/tpcc-10000", "fig_12/twitter-10000"],
                "tools": ["Plume_TCC", "Plume_TCC_Without_TC", "Plume_TCC_Without_VC"],
                "record_time": True
            },
            "fig12b": {
                "dirs": ["fig_8_9/2_200_0.5_10000_uniform_20", "fig_8_9/5_200_0.5_10000_uniform_20",
                         "fig_8_9/10_200_0.5_10000_uniform_20", "fig_8_9/15_200_0.5_10000_uniform_20",
                         "fig_8_9/20_200_0.5_10000_uniform_20", "fig_8_9/25_100_0.5_10000_uniform_20",
                         "fig_8_9/30_200_0.5_10000_uniform_20",
                         "fig_8_9/40_200_0.5_10000_uniform_20", "fig_8_9/50_200_0.5_10000_uniform_20"],
                "tools": ["Plume_TCC", "Plume_TCC_Without_VC"],
                "record_dfs": True
            },
        },
        "fig13": {
            "fig13a": {
                "dirs": ["fig_13/100_10000_0.2_1000000000_uniform_100",
                         "fig_13/100_10000_0.4_1000000000_uniform_100",
                         "fig_13/100_10000_0.5_1000000000_uniform_100",
                         "fig_13/100_10000_0.6_1000000000_uniform_100",
                         "fig_13/100_10000_0.8_1000000000_uniform_100"],
                "tools": ["Plume_TCC_Large_Memory", "Plume_RC_Large_Memory", "Plume_RA_Large_Memory"],
                "record_time": True
            },
            "fig13b": {
                "dirs": ["fig_13/100_10000_0.5_1000000000_uniform_100",
                         "fig_13/100_10000_0.5_1000000000_uniform_200",
                         "fig_13/100_10000_0.5_1000000000_uniform_300",
                         "fig_13/100_10000_0.5_1000000000_uniform_400"],
                "tools": ["Plume_TCC_Large_Memory", "Plume_RC_Large_Memory", "Plume_RA_Large_Memory"],
                "record_time": True
            },
        }
    }

    if experiment_group not in configurations:
        print(f"Invalid experiment group: {experiment_group}")
        return

    for sub_experiment, config in configurations[experiment_group].items():
        selected_configurations = config["dirs"]
        selected_tools = config["tools"]
        record_time = config.get("record_time", False)
        record_memory = config.get("record_memory", False)
        record_segments = config.get("record_segments", False)
        record_dfs = config.get("record_dfs", False)
        output_file = f"{sub_experiment}_results.csv"

        results = []

        for config_dir in selected_configurations:
            base_input_path = os.path.join(base_dir, config_dir)
            if os.path.isdir(base_input_path):
                for tool in selected_tools:
                    tool_config = ALL_TOOLS[tool]
                    command = tool_config["command"]
                    tool_base_input_path = os.path.join(base_input_path, tool_config["input_folder"])
                    if os.path.isdir(tool_base_input_path):
                        for sub_input_path in os.listdir(tool_base_input_path):
                            full_input_path = os.path.join(tool_base_input_path, sub_input_path)
                            if os.path.isdir(full_input_path) or os.path.isfile(full_input_path):
                                max_memory_usage, elapsed_time, segment_times, dfs_count = run_tool(tool, command,
                                                                                                    full_input_path,
                                                                                                    record_time,
                                                                                                    record_memory,
                                                                                                    record_segments,
                                                                                                    record_dfs)
                                result = {
                                    "tool": tool,
                                    "input_path": full_input_path,
                                }
                                if record_memory:
                                    result["max_memory_usage_mb"] = max_memory_usage / (1024 * 1024)
                                if record_time:
                                    result["elapsed_time_s"] = elapsed_time
                                if record_segments:
                                    result.update(segment_times)
                                if record_dfs:
                                    result["dfs_count"] = dfs_count
                                results.append(result)
                            else:
                                print(f"Input {full_input_path} is neither a directory nor a file")
                    else:
                        print(f"Directory {tool_base_input_path} does not exist")

        # Write to CSV file
        with open(output_file, mode='w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ["tool", "input_path"]
            if record_memory:
                fieldnames.append("max_memory_usage_mb")
            if record_time:
                fieldnames.append("elapsed_time_s")
            if record_segments and results:
                segments = set()
                for result in results:
                    for field in result.keys() - {"tool", "input_path", "max_memory_usage_mb", "elapsed_time_s"}:
                        segments.add(field)
                fieldnames.extend(segments)
            if record_dfs:
                fieldnames.append("dfs_count")
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                writer.writerow(result)

        print(f"Results for {sub_experiment} have been written to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run experiments to reproduce figures from the paper')
    parser.add_argument(
        'experiment_group',
        type=str,
        choices=['fig8', 'fig9', 'fig10', 'fig11', 'fig12', 'fig13'],
        help='The experiment group to run for reproducing figures. Choices are: fig8, fig9, fig10, fig11, fig12, fig13.'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=600,
        help='Timeout for the experiment in seconds. Default is 600 seconds.'
    )
    args = parser.parse_args()
    print(f'Running experiment group: {args.experiment_group}')
    print(f'Timeout: {args.timeout} seconds')

    TIMEOUT = args.timeout
    run_experiments(args.experiment_group)
