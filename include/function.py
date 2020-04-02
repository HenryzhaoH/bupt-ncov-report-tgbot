import re
from typing import Dict, Optional
import logging
import requests
import logging
import json
from .config import *

_logger = logging.getLogger(__name__)

class UsernameNotSet(Exception):
    pass

def match_re_group1(re_str: str, text: str) -> str:
    """
    在 text 中匹配正则表达式 re_str，返回第 1 个捕获组（即首个用括号包住的捕获组）
    :param re_str: 正则表达式（字符串）
    :param text: 要被匹配的文本
    :return: 第 1 个捕获组
    """
    match = re.search(re_str, text)
    if match is None:
        raise ValueError(f'在文本中匹配 {re_str} 失败，没找到任何东西。\n请阅读脚本文档中的“使用前提”部分。')

    return match.group(1)

def extract_post_data(html: str, old_data=None) -> Dict[str, str]:
    """
    从上报页面的 HTML 中，提取出上报 API 所需要填写的参数。
    :return: 最终 POST 的参数（使用 dict 表示）
    """
    new_data = match_re_group1(r'var def = (\{.+\});', html)
    if old_data == None:
        old_data = match_re_group1(r'oldInfo: (\{.+\}),', html)

    # 检查数据是否足够长
    if len(old_data) < REASONABLE_LENGTH or len(new_data) < REASONABLE_LENGTH:
        _logger.debug(f'\nold_data: {old_data}\nnew_data: {new_data}')
        raise ValueError('获取到的数据过短。请阅读脚本文档的“使用前提”部分')

    old_data, new_data = json.loads(old_data), json.loads(new_data)

    # 需要从 new dict 中提取如下数据
    PICK_PROPS = (
        'id', 'uid', 'date', 'created',
    )

    for prop in PICK_PROPS:
        val = new_data.get(prop, ...)
        if val is ...:
            raise RuntimeError(f'从网页上提取的 new data 中缺少属性 {prop}，可能网页已经改版。')
        old_data[prop] = val

    SANITIZE_PROPS = {
        'ismoved': 0,
        'jhfjrq': '',
        'jhfjjtgj': '',
        'jhfjhbcc': '',
        'sfxk': 0,
        'xkqq': '',
        'szgj': '',
        'szcs': '',
        # Moved info sanitize
        'sfsfbh': 0, 
        'ismoved': 0,
        'xjzd': '',
        'bztcyy': '',
    }
    old_data.update(SANITIZE_PROPS)
    
    try:
        if len(old_data['address']) == 0 \
        or (
            len(old_data['city']) == 0 \
            and old_data['province'] in ['北京市','上海市','重庆市','天津市'] 
        ):
            geo_info = json.loads(old_data['geo_api_info'])
            old_data['address'] = geo_info['formattedAddress']
            old_data['province'] = geo_info['addressComponent']['province']
            if old_data['province'] in ['北京市','上海市','重庆市','天津市']:
                old_data['city'] = geo_info['addressComponent']['province']
            else:
                old_data['city'] = geo_info['addressComponent']['city']
            old_data['area'] = ' '.join([old_data['province'], old_data['city'], geo_info['addressComponent']['district']])
    except json.decoder.JSONDecodeError as e:
        raise RuntimeError(f'定位信息为空，自动修复地址信息失败。手动上报一次后方可正常使用。')

    return old_data