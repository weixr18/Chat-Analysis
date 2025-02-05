import csv, os, argparse
import pandas as pd
from f_params import txt_paths, csv_paths, months
from utils import chat

#################################### Links ####################################

TMP_LINK_FILE = f'../data/{chat}/cleaned/links.csv'
TMP_CHAT_FILE = f'../data/{chat}/cleaned/chat.csv'
MESSAGES_FILE = f'../data/{chat}/cleaned/messages.csv'
TEXT_FILE = f'../data/{chat}/cleaned/text.csv'
MERGED_DIR = f'../data/{chat}/merged'


def create_dirs():
    def test_and_mkdir(path):
        if not os.path.exists(path):
            os.mkdir(path)
    test_and_mkdir("../data/")
    test_and_mkdir("../res/")
    dirs = [
        f"../data/{chat}/",
        f"../data/{chat}/cleaned/",
        f"../data/{chat}/llm/",
        f"../data/{chat}/llm/input/",
        f"../data/{chat}/llm/output/",
        f"../data/{chat}/merged/",
        f"../data/{chat}/origin/",
        f"../res/{chat}/",
        f"../res/{chat}/wordcloud/",
        f"../res/{chat}/user/",
    ]
    for dir_ in dirs:
        test_and_mkdir(dir_)
    pass


def _get_link_entries(input_file):
    with open(input_file, "r", encoding="utf-8") as file:
        lines = file.readlines()
    entries = []
    current_entry = {}
    is_entry = False
    # generate dict
    for line in lines:
        line = line.strip()
        if not line:  # 跳过空行
            if is_entry:  # 如果当前条目非空，保存条目
                entries.append(current_entry)
                current_entry = {}
                is_entry = False
            continue
        # 非空行，第一行 or 无关行
        if not is_entry:
            if line[:4].isdigit() and "&" not in line:  # 首行判定
                current_entry["StrTime"] = line[:19]
                current_entry["Remark"] = line[20:]
                is_entry = True
            continue
        # 非空行，非第一行
        if is_entry:   
            if "title:" in line: 
                current_entry["title"] = line.split("title:")[1].strip()
            elif "description:" in line: 
                if "https://" in line:
                    current_entry["description"] = ""
                else:
                    current_entry["description"] = line.split("description:")[1].strip()
            elif "name:" in line:  
                current_entry["name"] = line.split("name:")[1].strip()
            elif "url:" in line:
                pass
            else:
                is_entry = False
            continue
        pass
    if current_entry:
        entries.append(current_entry)
    print(f"Got entries from {input_file}: {len(entries)}")
    return entries


def process_links_to_csv(output_file):
    entries = []
    for txt_file in txt_paths[chat]:
        entries = entries + _get_link_entries(txt_file)
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Remark", "StrTime", "StrContent"])
        for entry in entries:
            remark = entry.get("Remark", "")
            str_time = entry.get("StrTime", "")
            str_content = f"{entry.get('name', '')} | {entry.get('title', '')} | {entry.get('description', '')}"
            str_content = str_content.replace("\n", "").replace("\r", "")
            writer.writerow([remark, str_time, str_content])
        pass
    print(f"CSV 文件已生成：{output_file}")



#################################### Merge files ####################################



def merge_csvs():
    data_frames = [pd.read_csv(file_path) for file_path in csv_paths[chat]]
    for i, df in enumerate(data_frames):
        print(f'File {i + 1} has {len(df)} rows.')
    combined_data = pd.concat(data_frames, ignore_index=True)
    combined_data.to_csv(TMP_CHAT_FILE, index=False, encoding='utf8')
    pass


def merge_links():
    link_df = pd.read_csv(TMP_LINK_FILE)
    chat_df = pd.read_csv(TMP_CHAT_FILE)
    merged_df = chat_df.merge(
        link_df[['Remark', 'StrTime', 'StrContent']], 
        on=['Remark', 'StrTime'], 
        how='left', 
        suffixes=('', '_link')
    )
    merged_df['StrContent'] = merged_df['StrContent_link'].combine_first(merged_df['StrContent'])
    merged_df = merged_df.drop(columns=['StrContent_link'])
    merged_df = merged_df.dropna(subset=['StrContent']) # 防止'StrContent'列为float类型
    merged_df.to_csv(MESSAGES_FILE, index=False, encoding='utf8')
    print("Total messages:", len(merged_df))
    text_df = merged_df[merged_df['Type'].isin([1, 49])] # only links and chats
    text_df.to_csv(TEXT_FILE, index=False, encoding='utf8')
    print("Merged links and dialogues.")
    os.remove(TMP_LINK_FILE)
    os.remove(TMP_CHAT_FILE)
    pass



#################################### monthly TXTs ####################################


def generate_monthly_txt():
    df = pd.read_csv(TEXT_FILE)
    df['CreateTimeNew'] = pd.to_datetime(df['CreateTime'], unit='s')
    df['Year'] = df['CreateTimeNew'].dt.year
    df['Month'] = df['CreateTimeNew'].dt.month
    df['StrContent'] = df['StrContent'].astype(str)
    for month_str in months[chat]:
        year, month = month_str.split("-")
        year, month = int(year), int(month)
        file_name = f'{MERGED_DIR}/{year}-{month}.txt'
        month_df = df[(df['Year'] == year) & (df['Month'] == month)]
        if len(month_df) < 2:
            print(f"No data in {year}-{month}.")
            continue
        with open(file_name, 'w', encoding='utf8') as file:
            for text in month_df['StrContent']:
                file.write(text + '\n')
        print(f'File {file_name} has {len(month_df)} rows.')
        pass
    file_name = f'{MERGED_DIR}/merged.txt'
    with open(file_name, 'w', encoding='utf8') as file:
        for text in df['StrContent']:
            file.write(text + '\n')
    print(f'File {file_name} has {len(df)} rows.')
    pass



#################################### Calls ####################################

if __name__ == "__main__":
    create_dirs()
    merge_csvs()
    process_links_to_csv(TMP_LINK_FILE)
    merge_links()
    generate_monthly_txt()
