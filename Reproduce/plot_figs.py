import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import argparse


def generate_chart(csv_filename, chart_type='line'):
    output_filename = os.path.splitext(csv_filename)[0] + '.png'

    # Read the CSV file
    df = pd.read_csv(csv_filename)

    # Determine the y-axis column to use
    if 'elapsed_time_s' in df.columns:
        y_column = 'elapsed_time_s'
        y_label = 'Elapsed Time (s)'
    elif 'max_memory_usage_mb' in df.columns:
        y_column = 'max_memory_usage_mb'
        y_label = 'Memory Usage (MB)'
    elif 'dfs_count' in df.columns:
        y_column = 'dfs_count'
        y_label = 'DFS count'
    else:
        y_column = None

    # If no specified y-axis column, assume new stage format
    if y_column is None:
        stages = [col for col in df.columns if col not in ['tool', 'input_path']]
        df[stages] = df[stages].fillna(0)
        df['total_time'] = df[stages].sum(axis=1)

        # Generate stacked bar chart
        plt.figure(figsize=(12, 6))
        tools = df['tool'].unique()
        index = np.arange(len(tools))
        bar_width = 0.35

        bottom_values = pd.DataFrame(0, index=tools, columns=stages)

        for stage in stages:
            stage_sum = df.groupby('tool')[stage].sum()
            plt.bar(index, stage_sum[tools].values, bar_width, label=stage,
                    bottom=bottom_values.loc[tools, stage].values)
            bottom_values[stage] += stage_sum

        plt.xticks(index, tools)
        plt.xlabel('Tool')
        plt.ylabel('Time (s)')
        plt.title('Time by Tool and Stage')
        plt.legend()
        plt.grid(True)
    else:
        # Try to extract parameters from input_path naming conventions
        extracted_8_9_13 = df['input_path'].str.extract(r'/fig_(8_9|13)/(\d+)_(\d+)_(\d\.\d+)_(\d+)_([a-zA-Z]+)_(\d+)/')
        extracted_10_sess = df['input_path'].str.extract(r'/fig_10/sess(\d+)/')
        extracted_10_txns = df['input_path'].str.extract(r'/fig_10/txns-per-session(\d+)/')

        if extracted_8_9_13.isnull().values.all():
            if not extracted_10_sess.isnull().values.all():
                df['session_count'] = extracted_10_sess[0].astype(int)
                use_folder_names = False
                x_column = 'session_count'
            elif not extracted_10_txns.isnull().values.all():
                df['transactions_per_session'] = extracted_10_txns[0].astype(int)
                use_folder_names = False
                x_column = 'transactions_per_session'
            else:
                df['workload'] = df['input_path'].str.extract(r'/fig_12/([^/]+)/')[0]
                use_folder_names = True
        else:
            df[['fig_type', 'session_count', 'transactions_per_session', 'read_ratio', 'total_keys', 'key_distribution',
                'operations_per_transaction']] = extracted_8_9_13
            df['session_count'] = df['session_count'].astype(int)
            df['transactions_per_session'] = df['transactions_per_session'].astype(int)
            df['read_ratio'] = df['read_ratio'].astype(float)
            df['total_keys'] = df['total_keys'].astype(int)
            df['operations_per_transaction'] = df['operations_per_transaction'].astype(int)
            use_folder_names = False

            varying_columns = [col for col in ['session_count', 'transactions_per_session', 'read_ratio', 'total_keys',
                                               'key_distribution', 'operations_per_transaction'] if
                               df[col].nunique() > 1]
            if varying_columns:
                x_column = varying_columns[0]
            else:
                x_column = 'session_count'

        if use_folder_names:
            average_values = df.groupby(['tool', 'workload'])[y_column].mean().reset_index()
            x_column = 'workload'
        else:
            average_values = df.groupby(['tool', x_column])[y_column].mean().reset_index()

        plt.figure(figsize=(12, 6))
        tools = average_values['tool'].unique()
        x_values = average_values[x_column].unique()
        x_values.sort()
        index = np.arange(len(x_values))

        # Dynamically adjust bar width
        total_bar_width = 0.8
        bar_width = total_bar_width / len(tools)
        bar_offsets = np.linspace(-total_bar_width / 2, total_bar_width / 2, len(tools), endpoint=False)

        for i, tool in enumerate(tools):
            tool_data = average_values[average_values['tool'] == tool]
            if chart_type == 'line':
                plt.plot(tool_data[x_column], tool_data[y_column], marker='o', linestyle='-', label=tool)
            elif chart_type == 'bar':
                plt.bar(index + bar_offsets[i], tool_data[y_column], bar_width, label=tool)

        if chart_type == 'bar':
            plt.xticks(index, x_values)

        plt.xlabel(x_column.replace('_', ' ').title())
        plt.ylabel(y_label)
        plt.legend()
        plt.grid(True if chart_type == 'line' else False)

    plt.savefig(output_filename)
    plt.close()
    print(f'Chart saved as {output_filename}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate charts from CSV files.')
    parser.add_argument('csv_filename', type=str, help='The CSV file to process.')
    parser.add_argument('chart_type', type=str, choices=['line', 'bar'],
                        help='The type of chart to generate (line or bar).')

    args = parser.parse_args()
    generate_chart(args.csv_filename, args.chart_type)
