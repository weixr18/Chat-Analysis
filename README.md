# README

## 数据无价，尊重他人

使用此代码时，应始终尊重和保护他人的数据隐私。所有分析和处理过程中涉及的任何个人或群体信息，均需严格遵循相关的法律法规以及数据隐私保护政策。代码使用时，应最大程度减少数据泄露或滥用的风险。所有数据的获取、存储、传输与处理，均应符合数据所有者的授权与同意。任何因用户违反隐私法规或未经授权使用数据而引发的法律责任，均由代码使用者自行承担，开发者不对使用本项目分析任何未经授权或未经合法途径获取的个人数据承担责任。

## Data is Priceless, Respect Others

When using this code, you should always respect and protect the privacy of others' data. Any personal or group information involved in the analysis and processing should strictly follow the relevant laws, regulations, and data privacy protection policies. When using the code, the risk of data leakage or misuse should be minimized as much as possible. All data acquisition, storage, transmission, and processing should be in compliance with the authorization and consent of the data owner. Any legal responsibility arising from the user's violation of privacy regulations or unauthorized use of data shall be borne by the user. The developer is not responsible for the analysis of any personal data obtained without authorization or through illegal means using this project.

## 代码功能

### 基本统计

+ preprocess.py
  + 原始数据预处理
+ stats.py
  + 水群天梯(总榜/半年榜)
  + 群热度曲线(按日/按月)
  + 个人水群曲线(按日/按周/按月)
+ word_cloud.py
  + 生成总词云/月度词云
  + f_stop_words.py: 停止词列表

### LLM话题总结

+ llm_preprocess.py
  + 准备数据
+ llm_topic_batch.py/llm_topic_file.py
  + 调用LLM API总结topic
+ llm_postprocess.py
  + 处理LLM生成的结果


## 代码使用

### f_params.py

中文：

1. 你需要给你的群聊起一个**群聊代号**，中英文均可，例如"宿舍群"。如果你有多个群聊，每个群聊取一个不一样的
2. 新建文件`scripts/f_params.py`，在里面仿照下方的示例，配置`months, txt_paths, csv_paths, periods, user_lists`这些字典变量。你需要给你的每个群聊配置一个表项，key就是群聊代号，value是对应的配置项。
3. 具体的配置项含义和格式见下方示例。
4. 注意txt文件和csv文件要放在示例中的对应位置，否则代码可能找不到

English:

1. You need to assign a **ChatCode** to your group chat, which can be in Chinese or English, such as "宿舍群". If you have multiple group chats, each one should have a unique name.
2. Create a new file scripts/f_params.py. Inside this file, configure the dictionary variables months, txt_paths, csv_paths, periods, user_lists by following the example provided below. You need to set up an entry for each of your group chats, where the key is the **ChatCode**s and the value is the corresponding configuration item.
3. Refer to the example below for the specific meanings and formats of the configuration items.
4. Put your csv and txt files in the directory as below shows.

```py
months = {
    "宿舍群": [
        '2023-9', '2023-10', '2023-11', '2023-12', 
        '2024-1', '2024-2', '2024-3', '2024-4', '2024-5', '2024-6', '2024-7', '2024-8', '2024-9', '2024-10', '2024-11', '2024-12', 
        '2025-1',
    ], # 群聊的时间范围，以月为单位
}
txt_paths = {
    "宿舍群": [
        '../data/宿舍群/origin/宿舍群.txt',
    ], # 导出的txt文件路径(包含链接消息)，一个群可以添加多个文件
}
csv_paths = {
    "宿舍群": [
        '../data/宿舍群/origin/宿舍群.csv',
    ], # 导出的csv文件路径(包含文本消息)，一个群可以添加多个文件
}
periods = {
    "宿舍群": [
        ('2024-01-01', '2024-06-30'),
        ('2024-07-01', '2024-12-31'),
        ('2025-01-01', '2025-06-30'),
    ], # 分时段水群用户统计的时段划分，以起止日期年月日标记每个范围
}
user_lists = {
    "宿舍群": [
        'AAA坦克租赁', '𝓚𝓲𝓻𝓪☆彡星空の猫', '量子波动养生大师', 
    ], # 需要统计个人水群曲线图的用户id
}
```

### 脚本运行

注意，每个脚本运行时，都需要指定**群聊代号**，该代号需要和上面`f_params.py`设置的一致

```sh
cd ./scripts/
python ./preprocess.py --chat {ChatCode}
python ./stats.py --chat {ChatCode}
python ./word_cloud.py --chat {ChatCode}
python ./llm_preprocess.py --chat {ChatCode}
python ./llm_topic_batch.py --chat {ChatCode}
python ./llm_postprocess.py --chat {ChatCode}
```
