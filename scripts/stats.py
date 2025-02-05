import argparse
import pandas as pd
import numpy as np
from itertools import cycle
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用黑体显示中文
plt.rcParams['axes.unicode_minus'] = False   # 正常显示负号

from f_params import user_lists, periods

############################# Basic #############################

chat = None

def get_chat_name():
    global chat
    parser = argparse.ArgumentParser(description="Process the chat parameter.")
    parser.add_argument("--chat", required=True, help="Chat codename. See params.py.")
    args = parser.parse_args()
    chat = args.chat
    print(f"Chat name: {chat}")
    assert chat in user_lists
    assert chat in periods
    return chat

get_chat_name() # must be called
MESSAGES_FILE = f'../data/{chat}/cleaned/text.csv'
RES_DIR = f'../res/{chat}'

df = pd.read_csv(MESSAGES_FILE)
print(f'Column names: {df.columns.tolist()}')
print(f'Total number of rows: {len(df)}')

def get_nicknames():
    df['LatestNickName'] = df.groupby('Sender')['NickName'].transform('last')
    # 输出 NickName 列的所有去重值
    nick_name = df['LatestNickName'].unique()
    print(f'Total number of unique NickName: {len(nick_name)}')
    print(f'Unique NickName: {nick_name}')
    def print_mapping():
        tmp_df = df.groupby('LatestNickName')['NickName']
        latest_nickname_dict = tmp_df.apply(lambda x: list(set(x))).to_dict()
        from pprint import pprint
        print("Nickname mapping:")
        for last_nn in latest_nickname_dict:
            if len(latest_nickname_dict[last_nn]) > 1:
                pprint(f'"{last_nn}": {latest_nickname_dict[last_nn]}')
        pass
    print_mapping()

get_nicknames() # must be called

def get_user_counts(name):
    # 统计一下NickName列为'name'的用户的发言量
    counts = len(df[df['LatestNickName'] == name])
    print(f'Number of messages from {name}: {counts}')


############################# Top Users (All time) #############################

def list_top_users_by_message():
    # 统计每个人发言的数量，从高到低排序，输出前30个
    nick_name_counts = df['LatestNickName'].value_counts().sort_values(ascending=False)
    print('Number of messages per NickName (sorted from high to low):')
    print(nick_name_counts.head(30))
    # # 输出前30人发言数量之和，以及占总数量的比例
    # top_30_counts = nick_name_counts.head(30).sum()
    # total_counts = len(df)
    # print(f'Top 30 counts / Total counts: {top_30_counts / total_counts}')
    # # 输出未发言群友
    # no_msg_nicknames = nick_name_counts[nick_name_counts < 21]
    # print(f'NickNames less than 21 messages: {len(no_msg_nicknames)}')
    # no_msg_nicknames = nick_name_counts[nick_name_counts < 6]
    # print(f'NickNames less than 6 messages: {len(no_msg_nicknames)}')
    # no_msg_nicknames = nick_name_counts[nick_name_counts < 2]
    # print(f'NickNames less than 2 messages: {len(no_msg_nicknames)}')
    # 输出列表对应情况
    

def list_top_users_by_word():
    # 统计每个人发言的字数之和，从高到低排序。字数定义为'StrContent'列的长度，不包括空白符
    def count_words(text):
        return len(text.strip())
    df['WordCount'] = df['StrContent'].apply(count_words)
    nick_name_word_counts = df.groupby('LatestNickName')['WordCount'].sum().sort_values(ascending=False)
    # 输出前30个发言字数最多的用户
    print('Total number of words per NickName (sorted from high to low):')
    print(nick_name_word_counts.head(30))
    # 输出总字数，以及前30个用户的字数之和占总字数的比例
    top_30_word_counts = nick_name_word_counts.head(30).sum()
    total_word_counts = df['WordCount'].sum()
    print(f'Total word counts: {total_word_counts}')
    print(f'Top 30 word counts / Total word counts: {top_30_word_counts / total_word_counts}')


############################# Top Users (Half Year) #############################

def list_halfyear_top_users(N: int = 10):
    df['CreateTimeNew'] = pd.to_datetime(df['CreateTime'], unit='s')
    top_users_df = pd.DataFrame()
    for start, end in periods[chat]:
        half_year_df = df[(df['CreateTimeNew'] >= start) & (df['CreateTimeNew'] <= end)]
        nick_name_counts = half_year_df['LatestNickName'].value_counts().sort_values(ascending=False)
        top_users_df[f'{start} to {end}'] = nick_name_counts.head(N).index
    return top_users_df
    

def plot_halfyear_top_users(top_users_df):
    user_rankings = {}
    for period in top_users_df.columns:
        for rank, user in enumerate(top_users_df[period]):
            if user not in user_rankings:
                user_rankings[user] = []
            user_rankings[user].append((period, rank + 1))
    # Add ">N名" for users not in the top N in a period
    for user in user_rankings:
        periods_with_rank = [period for period, _ in user_rankings[user]]
        for period in top_users_df.columns:
            if period not in periods_with_rank:
                user_rankings[user].append((period, len(top_users_df) + 1))
    # Sort the rankings by period
    for user in user_rankings:
        user_rankings[user].sort()
    # Plot the rankings
    plt.figure(figsize=(15, 10))
    colors = cycle(plt.cm.tab20.colors)
    for user, rankings in user_rankings.items():
        periods_ = [period for period, _ in rankings]
        ranks = [rank for _, rank in rankings]
        plt.plot(periods_, ranks, marker='o', label=user, color=next(colors))
    # Annotate the NickName next to the lines only once at the first occurrence of rank <= N
    for user, rankings in user_rankings.items():
        for period, rank in rankings:
            if rank <= len(top_users_df):
                plt.text(period, rank, user, fontsize=8, ha='right')
                break
    # show plot
    plt.gca().invert_yaxis()  # Invert y-axis to have rank 1 at the top
    plt.xlabel('Period')
    plt.xticks(rotation=45)
    plt.ylabel('Rank')
    plt.yticks(range(1, len(top_users_df) + 2))
    plt.title('Top Users by Message Count Over Time')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(f'{RES_DIR}/Halfyear-Top-Users.png')
    pass


############################# Top User-day #############################

def list_top_user_day():
    df['CreateTimeNew'] = pd.to_datetime(df['CreateTime'], unit='s')
    df['Date'] = df['CreateTimeNew'].dt.date
    user_day_counts = df.groupby(['LatestNickName', 'Date']).size().reset_index(name='MessageCount')
    top_user_days = user_day_counts.sort_values(by='MessageCount', ascending=False).head(10)
    print('Top user-days with the most messages:')
    print(top_user_days)



############################# Time Series (All users) #############################


def plot_daily_message_counts():
    df['CreateTimeNew'] = pd.to_datetime(df['CreateTime'], unit='s')
    daily_counts = df['CreateTimeNew'].dt.date.value_counts().sort_index()
    plt.figure(figsize=(15, 5))
    daily_counts.plot()
    plt.xlabel('Date')
    plt.ylabel('Number of Messages')
    plt.title('Daily Message Counts')
    plt.savefig(f'{RES_DIR}/Daily-Message-Counts.png')
    print('Top 10 days with the most messages:')
    print(daily_counts.sort_values(ascending=False).head(10))
    

def plot_monthly_message_counts():
    df['CreateTimeNew'] = pd.to_datetime(df['CreateTime'], unit='s')
    monthly_counts = df['CreateTimeNew'].dt.to_period('M').value_counts().sort_index()
    plt.figure(figsize=(15, 5))
    monthly_counts.plot()
    plt.xlabel('Month')
    plt.ylabel('Number of Messages')
    plt.title('Monthly Message Counts')
    plt.savefig(f'{RES_DIR}/Monthly-Message-Counts.png')

############################# Time Series (Specific users) #############################

user_list = user_lists[chat]

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def plot_daily_message_counts_of_user(NickName: str):
    df['CreateTimeNew'] = pd.to_datetime(df['CreateTime'], unit='s')
    # 绘制每日消息数量的图
    daily_counts = df[df['LatestNickName'] == NickName]['CreateTimeNew'].dt.date.value_counts().sort_index()
    plt.figure(figsize=(15, 5))
    plt.plot(daily_counts.index, daily_counts.values, label='Daily Message Counts', marker='o')
    plt.xlabel('Date')
    plt.ylabel('Number of Messages')
    plt.title(f'Daily Message Counts of {NickName}')
    plt.legend()
    plt.savefig(f'{RES_DIR}/user/{NickName}-Daily-Counts.png')
    plt.close()
    # 绘制累积消息数量的图
    cumulative_counts = np.cumsum(daily_counts)
    plt.figure(figsize=(15, 5))
    plt.plot(daily_counts.index, cumulative_counts.values, label='Cumulative Message Counts', marker='o', linestyle='--', color='orange')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Number of Messages')
    plt.title(f'Cumulative Message Counts of {NickName}')
    plt.legend()
    plt.savefig(f'{RES_DIR}/user/{NickName}-Cumulative-Counts.png')
    plt.close()



def plot_weekly_message_counts_of_user(NickName:str):
    # 统计用户每周的发言数量，绘制折线图
    df['CreateTimeNew'] = pd.to_datetime(df['CreateTime'], unit='s')
    weekly_counts = df[df['LatestNickName'] == NickName]['CreateTimeNew'].dt.to_period('W').value_counts().sort_index()
    plt.figure(figsize=(15, 5))
    weekly_counts.plot()
    plt.xlabel('Week')
    plt.ylabel('Number of Messages')
    plt.title(f'Weekly Message Counts of {NickName}')
    plt.savefig(f'{RES_DIR}/user/{NickName}-Weekly-Counts.png')


def plot_monthly_message_counts_of_user(NickName:str):
    # 统计用户每月的发言数量，绘制折线图
    df['CreateTimeNew'] = pd.to_datetime(df['CreateTime'], unit='s')
    monthly_counts = df[df['LatestNickName'] == NickName]['CreateTimeNew'].dt.to_period('M').value_counts().sort_index()
    plt.figure(figsize=(15, 5))
    monthly_counts.plot()
    plt.xlabel('Month')
    plt.ylabel('Number of Messages')
    plt.title(f'Monthly Message Counts of {NickName}')
    plt.savefig(f'{RES_DIR}/user/{NickName}-Monthly-Counts.png')


def plot_figs_for_users():
    for user in user_list:
        plot_daily_message_counts_of_user(user)
        plot_weekly_message_counts_of_user(user)
        plot_monthly_message_counts_of_user(user)
        print("Finish plotting for user: ", user)

##########################################################


# get_user_counts('Hybird')
# list_top_users_by_message()
# list_top_users_by_word()
# list_top_user_day()
# plot_daily_message_counts()
# plot_monthly_message_counts()
# top_users_df = list_halfyear_top_users()
# plot_halfyear_top_users(top_users_df)
plot_figs_for_users()
