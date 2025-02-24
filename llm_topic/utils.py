import time, json, os
from openai import OpenAI
from f_params import months, api_settings


#################################### basics ####################################

chat = None
def _get_chat_name():
    import argparse
    global chat
    parser = argparse.ArgumentParser(description="Process the chat parameter.")
    parser.add_argument("--chat", required=True, help="Chat codename. See params.py.")
    args = parser.parse_args()
    chat = args.chat
    assert chat in months 
    print(f"Chat name: {chat}")
_get_chat_name()

MESSAGES_FILE = f'../data/{chat}/cleaned/messages.csv'
TEXT_FILE = f'../data/{chat}/cleaned/text.csv'
TEXT_DEBUG_FILE = f'../data/{chat}/cleaned/text-debug.csv'
LLM_INPUT_PATH = f'../data/{chat}/llm/input'
LLM_OUTPUT_PATH = f'../data/{chat}/llm/output'
TMP_START_FILE = f'../data/{chat}/llm/start.json'
TMP_JSONL_FILE = f"../data/{chat}/llm/tmp_batch_requests_{chat}.jsonl"
TOPIC_CSV_PATH = f'../data/{chat}/llm/topics.csv'
PURE_TOPIC_PATH = f'../data/{chat}/llm/pure_topics.txt'

# init model
def _get_model(PROVIDER):
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



#################################### LLM input preparation ####################################


MAX_INPUT_LEN = 3000

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



def _create_batch_file(model:OpenAI, total_input_lists:dict, PROVIDER:str):
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



#################################### LLM output decoding ####################################


def _time(tsp):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(tsp))


# decode function
def _decode_reply(reply:str, START_TIME:int, msgs:dict, VERBOSE:bool):
    def _trim_string(s:str):
        start = s.find('{')
        end = s.rfind('}')
        return s[start:end+1]
    rpls = reply.split("\n")
    if VERBOSE:
        print(f"---------------- LLM reply (len={len(rpls)}) ----------------")
        print(reply)
        print("-------------------------------------------\n\n")
    topics = []
    for rpl in rpls:
        rpl = _trim_string(rpl)
        try:
            tpc = json.loads(rpl)
            tpc["StartTime"] = _time(tpc["StartTime"]+START_TIME)
            tpc["EndTime"] = _time(tpc["EndTime"]+START_TIME)
            tpc["Count"] = len(tpc["Messages"])
            tpc["msgs"] = []
        except Exception as e:
            print(e)
            continue
        for id_ in tpc["Messages"]:
            if id_ not in msgs:
                print("not in msgs:", id_)
                continue
            tpc["msgs"].append(msgs[id_].replace('"', ""))
        del tpc["Messages"]
        topics.append(tpc)
    json_str = json.dumps(topics, ensure_ascii=False, indent=4)
    return json_str
