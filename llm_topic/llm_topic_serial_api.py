import json, os
from openai import OpenAI
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils import _get_model, _decode_reply, _create_input_list
from utils import *

PROVIDER = 'aliyun'

#################################### preparation ####################################


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




#################################### LLM ####################################

MAX_WORKERS = 10
SLEEP_SECONDS = 1

def get_file_topics(model:OpenAI, starts:dict, names:list):
    def _save_to_file(name, json_str):
        output_file = f'{LLM_OUTPUT_PATH}/{name}.txt'
        with open(output_file, "a", encoding="utf-8") as f:
            f.writelines(json_str)
        pass
    def process_message(messages, name, msgs_outs):
        try:
            response = model.chat.completions.create(
                model=model.MODEL,  
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": messages}
                ],
                max_tokens=2048,
                temperature=1.0,
                stream=False,
            )
        except Exception as e:
            print(e)
            return
        reply = response.model_dump()['choices'][0]['message']['content'] 
        START_TIME = starts[name]['CreateTime']
        json_str = _decode_reply(reply, START_TIME, msgs_outs, False)
        _save_to_file(name, json_str)
        time.sleep(SLEEP_SECONDS)

    for name in names:
        output_file = f'{LLM_OUTPUT_PATH}/{name}.txt'
        if os.path.exists(output_file):
            os.remove(output_file)
        input_list, msgs_outs = _prepare_input(name)
        n_input = len(input_list)
        print(f"input num: {n_input}, message num: {len(msgs_outs)}, avg msg/input: {len(msgs_outs)/n_input}")
        if DEBUG_MODE:
            for messages in input_list:
                process_message(messages, name, msgs_outs)
            pass
        else:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor: 
                futures = [executor.submit(process_message, messages, name, msgs_outs) for messages in input_list]
                for future in tqdm(as_completed(futures), total=len(futures)):
                    future.result()
            pass
    return




#################################### Call ####################################



skip_data = [
    'text-debug', '2022-3', '2022-4'
]


DEBUG_MODE = False
VERBOSE = False
model = _get_model(PROVIDER)
with open(TMP_START_FILE, "r", encoding="utf-8") as json_file:
    starts = json.load(json_file)
if DEBUG_MODE:
    get_file_topics(model, starts, ['text-debug'])
else:
    names = []
    for name in starts:
        if name in skip_data:
            continue
        names.append(name)
    print("names:", names)
    get_file_topics(model, starts, names)
print("All files process are done.")
