import json, argparse
import pandas as pd
from f_params import months

chat = None

def get_chat_name():
    global chat
    parser = argparse.ArgumentParser(description="Process the chat parameter.")
    parser.add_argument("--chat", required=True, help="Chat codename. See params.py.")
    args = parser.parse_args()
    chat = args.chat
    assert chat in months 
    print(f"Chat name: {chat}")
    return chat

get_chat_name()

WITH_TEXT_DEBUG = False
MESSAGES_FILE = f'../data/{chat}/cleaned/messages.csv'
TEXT_FILE = f'../data/{chat}/cleaned/text.csv'
TEXT_DEBUG_FILE = f'../data/{chat}/cleaned/text-debug.csv'
LLM_INPUT_PATH = f'../data/{chat}/llm/input'
TMP_START_FILE = f'../data/{chat}/llm/start.json'


def gen_user_id_list():
    adf = pd.read_csv(MESSAGES_FILE)
    all_nicknames = adf['NickName'].unique()
    # 建立一个昵称到用户ID的映射
    user_id_list = {name: i for i, name in enumerate(all_nicknames)}
    return user_id_list


def llm_preprocess(user_id_list):
    # 取df的StrContent, CreateTime, NickName, localId四列数据合并到一个txt文件中
    # 文件名为'../data/merged/{year}-{month}.txt'
    # e.g. `u:312 t:44139 c:"XXXXXXXXXXXXX" id:7951``
    df = pd.read_csv(TEXT_FILE)
    df['CreateTimeNew'] = pd.to_datetime(df['CreateTime'], unit='s')
    df['Year'] = df['CreateTimeNew'].dt.year
    df['Month'] = df['CreateTimeNew'].dt.month
    df['StrContent'] = df['StrContent'].astype(str)
    df['NickName'] = df['NickName'].apply(lambda x: user_id_list[x]) # NickName转换为用户ID
    # get names & dfs
    dfs = {}
    for month_str in months[chat]:
        year, month = month_str.split("-")
        year, month = int(year), int(month)
        month_df = df[(df['Year'] == year) & (df['Month'] == month)]
        if len(month_df) < 2:
            print(f"No data in {month_str}.")
            continue
        dfs[month_str] = month_df
    if WITH_TEXT_DEBUG:
        months[chat].append("text-debug")
        dfs["text-debug"] = pd.read_csv(TEXT_DEBUG_FILE)
    
    # write files
    starts = {}
    for month_str in months[chat]:
        month_df = dfs[month_str]
        file_name = f'{LLM_INPUT_PATH}/{month_str}.txt'
        START_TIME = month_df.iloc[0]['CreateTime']
        START_MESSAGE = month_df.iloc[0]['localId']
        starts[month_str] = {
            'CreateTime': int(START_TIME),
            'localId': int(START_MESSAGE),
        }
        with open(file_name, 'w', encoding='utf8') as file: 
            for _, row in month_df.iterrows():
                row["StrContent"] = row["StrContent"].replace("\n", "").replace("\r", "")
                line = f'u:{row["NickName"]} ' + \
                    f'c:"{row["StrContent"]}" ' + \
                    f't:{int(row["CreateTime"])-START_TIME} ' + \
                    f'id:{int(row["localId"])-START_MESSAGE}\n'
                file.write(line)
        print(f'File {file_name} has {len(month_df)} rows.')
    with open(TMP_START_FILE, "w", encoding="utf-8") as json_file:
        json.dump(starts, json_file, ensure_ascii=False, indent=4)
    pass


########################################################################


user_id_list = gen_user_id_list()
llm_preprocess(user_id_list)
