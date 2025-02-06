import json, os
from utils import _get_model, _decode_reply, _create_input_list, _create_batch_file
from utils import *

PROVIDER = 'zhipu'


#################################### LLM Inputs ####################################


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
    _create_batch_file(model, total_input_lists, PROVIDER)
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
            json_str = _decode_reply(reply, START_TIME, msgs_out, False)
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
model = _get_model(PROVIDER)
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
