# -*- coding: utf-8 -*-
import os
import re
import time

from videotrans.configure import config
from videotrans.configure.config import logger
from videotrans.util import tools
import google.generativeai as genai

'''
输入
[{'line': 1, 'time': 'aaa', 'text': '\n我是中国人,你是哪里人\n'}, {'line': 2, 'time': 'bbb', 'text': '我身一头猪'}]

输出
[{'line': 1, 'time': 'aaa', 'text': 'I am Chinese, where are you from?'}, {'line': 2, 'time': 'bbb', 'text': 'I am a pig'}]

'''


def geminitrans(text_list, target_language_chatgpt="English", *, set_p=True):
    serv = tools.set_proxy()
    if serv:
        os.environ['http_proxy'] = serv
        os.environ['https_proxy'] = serv
    try:
        genai.configure(api_key=config.gemini_key)
    except Exception as e:
        err=str(e)
        if isinstance(text_list,str):
            return err
        else:
            tools.set_process(f'[error]Gemini翻译出错了:{err}','error')
            return [{"text":err}]
    lang = target_language_chatgpt
    print(f'{config.gemini_template=}')
    if isinstance(text_list, str):
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(
                config.gemini_template.replace('{lang}', lang) + f"\n{text_list}"
            )
            return response.text.strip()
        except Exception as e:
            error = str(e)
            return f"Gemini翻译失败 :{error}"

    total_result = []
    split_size = 10
    # 按照 split_size 将字幕每组8个分成多组,是个二维列表，一维是包含8个字幕dict的list，二维是每个字幕dict的list
    srt_lists = [text_list[i:i + split_size] for i in range(0, len(text_list), split_size)]
    srts = ''
    # 分别按组翻译，每组翻译 srt_list是个list列表，内部有10个字幕dict
    for srt_list in srt_lists:
        # 存放时间和行数
        origin = []
        # 存放待翻译文本
        trans = []
        # 处理每个字幕信息，it是字幕dict
        for it in srt_list:
            # 纯粹文本信息， 第一行是 行号，第二行是 时间，第三行和以后都是文字
            trans.append(it['text'].strip())
            # 行数和时间信息
            origin.append({"line": it["line"], "time": it["time"], "text": ""})

        len_sub = len(origin)
        logger.info(f"\n[Gemini start]待翻译文本:" + "\n".join(trans))
        error = ""
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(
                config.gemini_template.replace('{lang}', lang) + "\n" + "\n".join(trans)
            )
            trans_text = response.text.split("\n")
            logger.info(f"\n[Gemini OK]翻译成功")
            if set_p:
                tools.set_process(f"Gemini 翻译成功")
        except Exception as e:
            error = str(e)
            logger.error(f"【Gemini Error-2】翻译失败 :{error}")
            trans_text = [f"[error]Gemini 请求失败:{error}"] * len_sub
        if error and re.search(r'limit', error, re.I) is not None:
            if set_p:
                tools.set_process(f'Gemini请求速度被限制，暂停30s后自动重试')
            time.sleep(30)
            return geminitrans(text_list)
        # 处理

        for index, it in enumerate(origin):
            if index < len(trans_text):
                it["text"] = trans_text[index]
                origin[index] = it
                # 更新字幕
                st = f"{it['line']}\n{it['time']}\n{it['text']}\n\n"
                if set_p:
                    tools.set_process(st, 'subtitle')
                srts += st
        total_result.extend(origin)
    if set_p:
        tools.set_process(srts, 'replace_subtitle')
    return total_result
