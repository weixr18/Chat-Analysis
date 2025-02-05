import json, time, os, argparse
from pprint import pprint
from openai import OpenAI
from f_params import api_settings

#################################### LLM preparation ####################################

PROVIDER = 'zhipu'

sys_prompt = """
你将接收一组群聊消息，需要分析并提取每个话题的主题。话题由相关消息组成，一个话题的起止点要通过消息内容和时间判断。
你将看到按时间顺序排列的一系列消息。，每条消息格式如下：u:118 c:"..." t:1179 id:AAA。
u代表发布者，c代表消息内容，t代表发布的时间戳(精确到秒)，id代表消息的唯一标识符。
处理要求：判断话题的起始和结束时间，输出每个话题的信息。一条消息只属于一个话题，一个话题通常有3条以上消息。
注意，同一时间可能同时在讨论2个话题，例如消息[1,2,3,4,6,8]是话题A，消息[5,7,9,10,11]是话题B。
对每个Topic，输出一行，格式如下：
{"Topic": "XXX"(简要总结话题内容), "StartTime": xxxx(话题开始时间),"EndTime": xxxx(话题结束时间),"Messages": [522, 523, ...](属于话题的消息id)}
输出时，只输出我要求的内容，不要输出其他任何内容.尽量缩短思维链，这个任务不需要思考太多，但关键是要精准。
"""

# init model
def _get_model():
    print("Using provider:", PROVIDER)
    def get_properties(provider):
        p = api_settings[provider]
        return p["MODEL"], p["API_KEY"], p["BASE_URL"]
    MODEL, API_KEY, BASE_URL = get_properties(PROVIDER)
    model = OpenAI(api_key = API_KEY, base_url = BASE_URL)
    setattr(model, "provider", PROVIDER)
    setattr(model, "MODEL", MODEL)
    print("Got LLM model.")
    return model

#################################### chat preparation ####################################

chat = None

def get_chat_name():
    global chat
    parser = argparse.ArgumentParser(description="Process the chat parameter.")
    parser.add_argument("--chat", required=True, help="Chat codename. See params.py.")
    args = parser.parse_args()
    chat = args.chat
    print(f"Chat name: {chat}")
    return chat

get_chat_name()
LLM_INPUT_PATH = f'../data/{chat}/llm/input'
LLM_OUTPUT_PATH = f'../data/{chat}/llm/output'
TMP_START_FILE = f'../data/{chat}/llm/start.json'
TMP_JSONL_FILE = f"../data/{chat}/llm/tmp_batch_requests_{chat}.jsonl"


#################################### LLM Inputs ####################################


MAX_INPUT_LEN = 5000

def _time(tsp):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(tsp))

# get input list
def _create_input_list(lines):
    input_list = []
    current_str = ""
    for line in lines:
        if len(current_str) + len(line) > MAX_INPUT_LEN:
            input_list.append(current_str)
            current_str = line
        else:
            current_str += line
    if current_str:
        input_list.append(current_str)
    return input_list


def _create_batch_file(model:OpenAI, total_input_lists:dict):
    """see: https://docs.sglang.ai/backend/openai_api_completions.html#Batches"""
    if os.path.exists(TMP_JSONL_FILE):
        os.remove(TMP_JSONL_FILE)
    requests = []
    for name in total_input_lists:
        input_list = total_input_lists[name]
        for i, messages in enumerate(input_list):
            requests.append({
                "custom_id": f"{name}_{i}",
                "method": "POST",
                "url": api_settings[PROVIDER]["BATCH_API"],
                "body": {
                    "model": model.MODEL,
                    "messages": [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": messages}
                    ],
                    "max_tokens": 2048,
                },
            })
    print(f"Total requests: {len(requests)}")
    with open(TMP_JSONL_FILE, "w", encoding="utf-8") as f:
        for req in requests:
            f.write(json.dumps(req, ensure_ascii=False) + "\n")
    print(f"Created batch file: {TMP_JSONL_FILE}")
    pass


def prepare_batch_request(model, names):
    total_input_lists = {}
    for name in names:
        input_file = f'{LLM_INPUT_PATH}/{name}.txt'
        print(f"Processing file {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        input_list = _create_input_list(lines)
        total_input_lists[name] = input_list
        n_input, n_msgs = len(input_list), len(lines)
        print(f"input num: {n_input}, message num: {n_msgs}, avg msg/input: {n_msgs/n_input:.4f}")
        # remove existing output txt file
        output_file = f'{LLM_OUTPUT_PATH}/{name}.txt'
        if os.path.exists(output_file):
            os.remove(output_file)
    _create_batch_file(model, total_input_lists)
    pass


#################################### LLM Outputs ####################################

# prepare output
def _prepare_msgs_out(name):
    # get inputs
    input_file = f'{LLM_INPUT_PATH}/{name}.txt'
    print(f"Processing file {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    # prepare output messages
    msgs_out = {}
    for line in lines:
        id_ = int(line.split("id:")[-1])
        msgs_out[id_] = " t:".join(line.split(" t:")[:-1])
    return msgs_out



# decode function
def _decode_reply(reply:str, START_TIME:int, msgs:dict):
    def _trim_string(s:str):
        start = s.find('{')
        end = s.rfind('}')
        return s[start:end+1]
    rpls = reply.split("\n")
    topics = []
    for rpl in rpls:
        rpl = _trim_string(rpl)
        try:
            tpc = json.loads(rpl)
            if "StartTime" not in tpc:
                continue
        except Exception as e:
            continue
        tpc["StartTime"] = _time(tpc["StartTime"]+START_TIME)
        tpc["EndTime"] = _time(tpc["EndTime"]+START_TIME)
        tpc["Count"] = len(tpc["Messages"])
        tpc["msgs"] = []
        for id_ in tpc["Messages"]:
            if id_ not in msgs:
                # print("not in msgs:", id_)
                continue
            tpc["msgs"].append(msgs[id_].replace('"', ""))
        del tpc["Messages"]
        topics.append(tpc)
    json_str = json.dumps(topics, ensure_ascii=False, indent=4)
    return json_str




def get_batch_results(starts, names):
    for file in os.listdir(LLM_OUTPUT_PATH):
        if file.endswith('.jsonl'):
            output_jsonl_file = f"{LLM_OUTPUT_PATH}/{file}"
    with open(output_jsonl_file, 'r', encoding='utf-8') as f:
        result_content = f.readlines()
    all_replies = {}
    for line in result_content:
        if line.strip() == "":
            continue
        result = json.loads(line) 
        name, i = result['custom_id'].split('_')
        if name not in all_replies:
            all_replies[name] = []
        all_replies[name].append(result['response']['body']['choices'][0]['message']['content'])
    for name in names:
        msgs_out = _prepare_msgs_out(name)
        replies = all_replies[name]
        for reply in replies:
            START_TIME = starts[name]['CreateTime']
            json_str = _decode_reply(reply, START_TIME, msgs_out)
            if len(json_str) < 10:
                continue
            output_file = f'{LLM_OUTPUT_PATH}/{name}.txt'
            with open(output_file, "a", encoding="utf-8") as f:
                f.writelines(json_str)
        pass
    pass



#################################### Call ####################################

skip_data = [
    'text-debug'
]

DEBUG_MODE = False
model = _get_model()
with open(TMP_START_FILE, "r", encoding="utf-8") as json_file:
    starts = json.load(json_file)
if DEBUG_MODE:
    prepare_batch_request(model, ['text-debug'])
    #---------------WAIT FOR API PROCESSING---------------#
    get_batch_results(starts, ['text-debug'])
else:
    names = []
    for name in starts:
        if name not in skip_data:
            names.append(name)
    prepare_batch_request(model, names)
    #---------------WAIT FOR API PROCESSING---------------#
    # get_batch_results(starts, names)
print("All files process are done.")
