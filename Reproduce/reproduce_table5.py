import os
import signal
import subprocess
import json

import psutil

# Define the command line templates for the tools, their input folder names
ALL_TOOLS = {
    "PolySI": {
        "command": "java -jar /plume/Tools/PolySI/build/libs/PolySI-1.0.0-SNAPSHOT.jar audit -t TEXT {input_path}",
        "input_folder": "text",
    },
    "Viper_Old": {
        "command": "python3 /plume/Tools/Viper_old/src/main_allcases.py --config_file /plume/Reproduce/viper_config.yaml --sub_dir {input_path} --strong-session --perf_file /tmp/test_perf.txt --exp_name test_run",
        "input_folder": "viper",
    },
    "Viper_Latest": {
        "command": "python3 /plume/Tools/Viper/src/main_allcases.py --config_file /plume/Reproduce/viper_config.yaml --sub_dir {input_path} --strong-session --perf_file /tmp/test_perf.txt --exp_name test_run",
        "input_folder": "viper",
    },
    "Cobra": {
        "command": "/plume/Tools/CobraVerifier/run.sh mono audit /plume/Tools/CobraVerifier/cobra.conf.default {input_path}",
        "input_folder": "cobra",
    },
    "dbcop_TCC": {
        "command": "/plume/Tools/dbcop/target/release/dbcop verify -c cc --ver_dir {input_path} --out_dir /tmp",
        "input_folder": "dbcop",
    },
    "dbcop_RA": {
        "command": "/plume/Tools/dbcop/target/release/dbcop verify -c ra --ver_dir {input_path} --out_dir /tmp",
        "input_folder": "dbcop",
    },
    "dbcop_RC": {
        "command": "/plume/Tools/dbcop/target/release/dbcop verify -c rc --ver_dir {input_path} --out_dir /tmp",
        "input_folder": "dbcop",
    },
    "Elle_0.1.6_TCC": {
        "command": "java -jar /plume/Tools/elle-0.1.6/target/elle-cli-0.1.6-standalone.jar -m list-append -c causal-cerone {input_path}",
        "input_folder": "elle",
    },
    "Elle_0.1.9_TCC": {
        "command": "java -jar /plume/Tools/elle-0.1.9/target/elle-cli-0.1.7-standalone.jar -m list-append -c causal-cerone {input_path}",
        "input_folder": "elle",
    },
    "Elle_0.1.6_RA": {
        "command": "java -jar /plume/Tools/elle-0.1.6/target/elle-cli-0.1.6-standalone.jar -m list-append -c read-atomic {input_path}",
        "input_folder": "elle",
    },
    "Elle_0.1.9_RA": {
        "command": "java -jar /plume/Tools/elle-0.1.9/target/elle-cli-0.1.7-standalone.jar -m list-append -c read-atomic {input_path}",
        "input_folder": "elle",
    },
    "Elle_0.1.6_RC": {
        "command": "java -jar /plume/Tools/elle-0.1.6/target/elle-cli-0.1.6-standalone.jar -m list-append -c read-committed {input_path}",
        "input_folder": "elle",
    },
    "Elle_0.1.9_RC": {
        "command": "java -jar /plume/Tools/elle-0.1.9/target/elle-cli-0.1.7-standalone.jar -m list-append -c read-committed {input_path}",
        "input_folder": "elle",
    },
    "Plume_TCC": {
        "command": "java -jar /plume/Plume/target/Plume-1.0-SNAPSHOT-shaded.jar -i TCC -t PLUME --count-dfs {input_path}",
        "input_folder": "text",
    },
}

TIMEOUT = 10  # seconds

def should_skip_directory(tool, directory_name):
    if "RA" in tool and ("tap-m" in directory_name or "tap-n" in directory_name):
        return True
    if "Elle_RC" in tool and any(f"tap-{chr(c)}" in directory_name for c in range(ord('h'), ord('n')+1)):
        return True
    if "dbcop_RC" in tool and any(f"tap-{chr(c)}" in directory_name for c in range(ord('j'), ord('n')+1)):
        return True
    return False


def kill_process_tree(pid, including_parent=True):
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            os.kill(child.pid, signal.SIGTERM)
        if including_parent:
            os.kill(pid, signal.SIGTERM)
    except psutil.NoSuchProcess:
        pass


def run_tool(tool, command, input_path):
    try:
        formatted_command = command.format(input_path=input_path)
        print(f"Running {tool} with command: {formatted_command}")

        process = subprocess.Popen(formatted_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        try:
            stdout, stderr = process.communicate(timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            kill_process_tree(process.pid, True)
            stdout, stderr = process.communicate()
            print(f"{tool} on {input_path} timed out.")

        combined_output = stdout.decode() + "\n" + stderr.decode()
        return combined_output
    except Exception as e:
        print(f"Error running {tool} on {input_path}: {e}")
        return None

def run_experiments(input_directory):
    results = []

    if os.path.isdir(input_directory):
        for tool in ALL_TOOLS:
            tool_config = ALL_TOOLS[tool]
            command = tool_config["command"]
            tool_base_input_path = os.path.join(input_directory, tool_config["input_folder"])
            if os.path.isdir(tool_base_input_path):
                sub_input_paths = sorted(os.listdir(tool_base_input_path))
                for sub_input_path in sub_input_paths:
                    if should_skip_directory(tool, sub_input_path):
                        print(f"Skipping {sub_input_path} for {tool}")
                        continue
                    full_input_path = os.path.join(tool_base_input_path, sub_input_path)
                    if os.path.isdir(full_input_path) or os.path.isfile(full_input_path):
                        combined_output = run_tool(tool, command, full_input_path)
                        result = {
                            "tool": tool,
                            "input_path": full_input_path,
                            "output": combined_output,
                        }
                        results.append(result)
                    else:
                        print(f"Input {full_input_path} is neither a directory nor a file")
            else:
                print(f"Directory {tool_base_input_path} does not exist")
    else:
        print(f"Input directory {input_directory} does not exist")

    # Write to JSON file
    output_file = "table5.json"
    with open(output_file, 'w', encoding='utf-8') as jsonfile:
        json.dump(results, jsonfile, indent=4)

    print(f"Results have been written to {output_file}")

if __name__ == "__main__":
    input_directory = "/plume/History/testcase"
    run_experiments(input_directory)
