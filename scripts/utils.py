import argparse
from f_params import txt_paths, csv_paths, months, user_lists, periods

chat = None
def _get_chat_name():
    global chat
    parser = argparse.ArgumentParser(description="Process the chat parameter.")
    parser.add_argument("--chat", required=True, help="Chat codename. See params.py.")
    args = parser.parse_args()
    chat = args.chat
    print(f"Chat name: {chat}")
    assert chat in user_lists
    assert chat in periods
    assert chat in txt_paths
    assert chat in csv_paths
    assert chat in months
    return chat
_get_chat_name() # must be called
