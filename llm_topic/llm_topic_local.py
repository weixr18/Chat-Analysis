import json, time, os, math
from tqdm import tqdm
from openai import OpenAI


#################################### LLM preparation ####################################

PROVIDER = 'local'
settings = {
    "local": {
        "MODEL" : "deepseek-v3",
        "API_KEY" : "EMPTY",
        "BASE_URL" : "http://127.0.0.1:30000/v1",
        "COUNT_URL" : "http://127.0.0.1:30000/v1/tokenizers/estimate-token-count",
    },
}


sys_prompt = """
你将接收一组群聊消息，需要分析并提取每个话题的主题。话题由相关消息组成，一个话题的起止点要通过消息内容和时间判断。
每条消息格式如下：u:118 c:"..." t:1179 id:AAA
u代表发布者，c代表消息内容，t代表发布的时间戳(精确到秒)，id代表消息的唯一标识符。
处理要求：判断话题的起始和结束时间，输出每个话题的信息。一条消息只属于一个话题，一个话题通常有3条以上消息。
注意同一时间可能同时在讨论2个话题，例如消息[1,2,3,4,6,8]是话题A，消息[5,7,9,10,11]是话题B。
对每个Topic，输出一行，格式如下：
{"Topic": "XXX"(简要总结话题内容), "StartTime": xxxx(话题开始时间),"EndTime": xxxx(话题结束时间),"Messages": [522, 523, ...](属于话题的消息id)}
输出时，只输出我要求的内容，不要输出其他任何内容
"""

# init model
def _get_model():
    def get_properties(provider):
        p = settings[provider]
        return p["MODEL"], p["API_KEY"], p["BASE_URL"], p["COUNT_URL"]
    MODEL, API_KEY, BASE_URL, COUNT_URL = get_properties(PROVIDER)
    model = OpenAI(api_key = API_KEY, base_url = BASE_URL)
    setattr(model, "provider", PROVIDER)
    setattr(model, "MODEL", MODEL)
    setattr(model, "COUNT_URL", COUNT_URL)
    print("Got LLM model.")
    return model

#################################### LLM batch job ####################################



def _get_llm_batch_response(model:OpenAI, total_input_lists:dict):
    """see: https://docs.sglang.ai/backend/openai_api_completions.html#Batches"""
    # prepare requests
    tmp_file_path = "../data/tmp_batch_requests.jsonl"
    if os.path.exists(tmp_file_path):
        os.remove(tmp_file_path)
    requests = []
    for name in total_input_lists:
        input_list = total_input_lists[name]
        for i, messages in enumerate(input_list):
            requests.append({
                "custom_id": f"{name}_{i}",
                "method": "POST",
                "url": "/chat/completions",
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
    with open(tmp_file_path, "w") as f:
        for req in requests:
            f.write(json.dumps(req) + "\n")
    with open(tmp_file_path, "rb") as f:
        uploaded_file = model.files.create(file=f, purpose="batch")
    # create batch job
    batch_response = model.batches.create(
        input_file_id=uploaded_file.id,
        endpoint="/v1/chat/completions",
        timeout=5*60*60,
        completion_window="24h",
    )
    print(f"Created batch job with ID: {batch_response.id}")
    print(f"Initial status: {batch_response.status}")
    # wait for job done
    start_time = time.time()
    while batch_response.status not in ["completed", "failed", "cancelled"]:
        time.sleep(30)
        print(f"Batch job status: {batch_response.status}...trying again in 30 seconds...")
        batch_response = model.batches.retrieve(batch_response.id)
    print(f"Processing time: {time.time() - start_time:.4f}s")
    # get replies
    if batch_response.status == "completed":
        print("Batch job completed successfully!")
        print(f"Request counts: {batch_response.request_counts}")
        result_file_id = batch_response.output_file_id
        file_response = model.files.content(result_file_id)
        result_content = file_response.read().decode("utf-8")
        results = [
            json.loads(line) for line in result_content.split("\n") if line.strip() != ""
        ]
        all_replies = {}
        for result in results:
            name, i = result['custom_id'].split('_')
            if name not in all_replies:
                all_replies[name] = []
            all_replies[name].append(result['response']['body']['choices']['message']['content'])
        del batch_response
        return all_replies
    else:
        print(f"Batch job failed with status: {batch_response.status}")
        if hasattr(batch_response, "errors"):
            print(f"Errors: {batch_response.errors}")
        del batch_response
        return {}



#################################### Process ####################################

LLM_INPUT_PATH = '../data/input'
LLM_OUTPUT_PATH = '../data/output'
VERBOSE = False
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


# prepare input
def _prepare_input(name):
    # get inputs
    input_file = f'{LLM_INPUT_PATH}/{name}.txt'
    print(f"Processing file {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    input_list = _create_input_list(lines)
    # prepare output messages
    msgs_out = {}
    for line in lines:
        id_ = int(line.split("id:")[-1])
        msgs_out[id_] = " t:".join(line.split(" t:")[:-1])
    # remove existing output file
    output_file = f'{LLM_OUTPUT_PATH}/{name}.txt'
    if os.path.exists(output_file):
        os.remove(output_file)
    return input_list, msgs_out


# decode function
def _decode_reply(reply:str, START_TIME:int, msgs:dict):
    rpls = reply.split("\n")
    if VERBOSE:
        print(f"---------------- LLM reply (len={len(rpls)}) ----------------")
        print(reply)
        print("-------------------------------------------\n\n")
    topics = []
    for rpl in rpls:
        try:
            tpc = json.loads(rpl)
        except Exception as e:
            continue
        tpc["StartTime"] = _time(tpc["StartTime"]+START_TIME)
        tpc["EndTime"] = _time(tpc["EndTime"]+START_TIME)
        tpc["Count"] = len(tpc["Messages"])
        tpc["msgs"] = []
        for id_ in tpc["Messages"]:
            if id_ not in msgs:
                print("not in msgs:", id_)
                continue
            tpc["msgs"].append(msgs[id_].replace('"', ""))
        del tpc["Messages"]
        topics.append(tpc)
    json_str = json.dumps(topics, ensure_ascii=False, indent=4)
    return json_str


# save to file
def _save_to_file(name, json_str):
    output_file = f'{LLM_OUTPUT_PATH}/{name}.txt'
    with open(output_file, "a", encoding="utf-8") as f:
        f.writelines(json_str)
    pass



#################################### Call ####################################


def get_file_topics(model, starts, names):
    total_input_lists = {}
    total_msgs_outs = {}
    for name in names:
        input_list, msgs_out = _prepare_input(name)
        n_input = len(input_list)
        print(f"input num: {n_input}, message num: {len(msgs_out)}, avg msg/input: {len(msgs_out)/n_input}")
        total_input_lists[name] = input_list
        total_msgs_outs[name] = msgs_out
    all_replies = _get_llm_batch_response(model, total_input_lists)
    for name in names:
        replies = all_replies[name]
        for reply in replies:
            START_TIME = starts[name]['CreateTime']
            json_str = _decode_reply(reply, START_TIME, total_msgs_outs[name])
            _save_to_file(name, json_str)
    return


skip_data = [
    'text-debug'
]


DEBUG_MODE = False
model = _get_model()
TMP_START_FILE = '../data/start.json'
with open(TMP_START_FILE, "r", encoding="utf-8") as json_file:
    starts = json.load(json_file)
if DEBUG_MODE:
    get_file_topics(model, starts, ['text-debug'])
else:
    names = []
    for name in starts:
        if name not in skip_data:
            names.append(name)
    get_file_topics(model, starts, names)
print("All files process are done.")
