import os, json, csv
from datetime import timedelta, datetime
import pandas as pd
from utils import *


def replace_in_files(directory):
    for filename in os.listdir(directory):
        if filename.endswith('.txt'):
            file_path = os.path.join(directory, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                updated_content = content.replace('][', '').replace('}\n\n    {', "},\n    {")
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(updated_content)
                print(f"Processed file: {file_path}")
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
            pass
    pass


def extract_data_from_txt_files(input_dir, output_csv):
    all_entries = []
    pure_topics = []
    for filename in os.listdir(input_dir):
        if not filename.endswith(".txt"):
            continue
        file_path = os.path.join(input_dir, filename)
        with open(file_path, 'r', encoding='utf-8') as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError as e:
                print(file_path, "Error:", e)
                print(f"文件 {filename} 不是有效的JSON格式，跳过该文件。")
                continue
            for entry in data:
                topic = entry.get("Topic", "")
                start_time = entry.get("StartTime", "")
                end_time = entry.get("EndTime", "")
                num = len(entry["msgs"])
                start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
                if start_dt == end_dt:
                    duration = timedelta(seconds=1)
                else:
                    duration = end_dt - start_dt
                duration_str = str(duration)
                all_entries.append([topic, start_time, duration_str, num])
                pure_topics.append([topic])
            pass
        print(f"Processed file: {file_path}")
        pass
    # 将结果写入CSV文件
    with open(output_csv, 'w', encoding='utf-8', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(["Topic", "StartTime", "Duration", "Number"])
        csv_writer.writerows(all_entries)
    with open(PURE_TOPIC_PATH, 'w', encoding='utf-8', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerows(pure_topics)
    pass


def pretty_csv(output_csv_path):
    df = pd.read_csv(output_csv_path)
    df_sorted = df.sort_values(by="StartTime")
    df_sorted.to_csv(output_csv_path, index=False)
    pass


if __name__ == "__main__":
    replace_in_files(LLM_OUTPUT_PATH)
    extract_data_from_txt_files(LLM_OUTPUT_PATH, TOPIC_CSV_PATH)
    pretty_csv(TOPIC_CSV_PATH)
    print(f"CSV文件已成功输出到: {TOPIC_CSV_PATH}")
    print(f"话题列表: {PURE_TOPIC_PATH}")
