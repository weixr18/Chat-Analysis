import re, argparse
from collections import Counter
import jieba
import matplotlib.pyplot as plt
from wordcloud import WordCloud

from f_stop_words import stop_words

#############################################################

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
MERGED_DIR = f'../data/{chat}/merged'
WORDCLOUD_DIR = f'../res/{chat}/wordcloud'
TOPICS_PURE_FILE = f'../data/{chat}/llm/topics_pure.csv'


def read_text(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def preprocess_text(text):
    # text = re.sub(r'[^\u4e00-\u9fa5]', '', text)  # 仅保留中文字符
    text = re.sub(r'[^\w\s]', '', text)  # 仅保留中文和英文字符
    text = re.sub(r'\n', ' ', text)  # 将换行符替换为空格
    return text

#############################################################

# 分词并统计词频
def generate_word_frequency(text):
    words = jieba.lcut(text)  
    word_counts = Counter(words)
    filtered_word_counts = {
        word: count for word, count in word_counts.items() if word not in stop_words # and len(word) > 1
    }
    return filtered_word_counts


# 显示词频最高的前50个词
def show_freq_words(word_counts):
    words = []
    print("Top 50 frequent words:")
    for word, count in Counter(word_counts).most_common(50):
        print(f"{word}: {count}")
        words.append(word)
    print(words)


# 生成词云
def create_wordcloud(word_counts, output_path):
    wordcloud = WordCloud(
        font_path='msyh.ttc', 
        width=800,
        height=600,
        background_color='white'
    ).generate_from_frequencies(word_counts)
    # 显示词云
    plt.figure(figsize=(10, 8))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title(f"Word Cloud of {output_path.split('/')[-1][:-4]}")
    plt.savefig(output_path,bbox_inches='tight', pad_inches=0)
    plt.close()
    # wordcloud.to_file(output_path)
    print(f"Word cloud image saved to {output_path}")

#############################################################

def wordcloud(file_path):
    file_name = file_path.split("/")[-1]
    output_image = f'{WORDCLOUD_DIR}/{file_name[:-4]}.png'  # 输出的词云图片路径
    text = read_text(file_path)
    text = preprocess_text(text)
    word_counts = generate_word_frequency(text)
    # show_freq_words(word_counts) 
    create_wordcloud(word_counts, output_image)


if __name__ == '__main__':
    import os
    for file in os.listdir(MERGED_DIR):
        if file[:4] != "2021":
            continue
        wordcloud(f'{MERGED_DIR}/{file}')
    # wordcloud(TOPICS_PURE_FILE)
    pass
