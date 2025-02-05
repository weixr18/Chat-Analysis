import json, time, os
from openai import OpenAI
from utils import _get_model, _decode_reply, _create_input_list, _create_batch_file
from utils import *

PROVIDER = 'NVIDIA'

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


#################################### LLM batch job ####################################

def _get_llm_batch_response(model:OpenAI):
    # prepare requests
    with open(TMP_JSONL_FILE, "rb") as f:
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
    _create_batch_file(model, total_input_lists, PROVIDER)
    all_replies = _get_llm_batch_response(model)
    def _save_to_file(name, json_str):
        output_file = f'{LLM_OUTPUT_PATH}/{name}.txt'
        with open(output_file, "a", encoding="utf-8") as f:
            f.writelines(json_str)
        pass
    for name in names:
        replies = all_replies[name]
        for reply in replies:
            START_TIME = starts[name]['CreateTime']
            json_str = _decode_reply(reply, START_TIME, total_msgs_outs[name], VERBOSE)
            _save_to_file(name, json_str)
    return


skip_data = [
    'text-debug'
]


DEBUG_MODE = False
VERBOSE = False
model = _get_model()
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
