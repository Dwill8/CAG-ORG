
import json
import os
import requests
import time
import re
from datetime import datetime

CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'config')

# 日志目录
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

def load_config():
    config_path = os.path.join(CONFIG_DIR, 'llm_config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def log_llm_call(prompt, response, model, duration_ms, success):
    """记录LLM调用日志"""
    try:
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'model': model,
            'duration_ms': duration_ms,
            'success': success,
            'prompt': prompt[:500] + '...' if len(prompt) > 500 else prompt,
            'response': response[:1000] + '...' if response and len(response) > 1000 else (response or '')
        }
        
        # 按日期创建日志文件
        date_str = datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(LOG_DIR, f'llm_calls_{date_str}.json')
        
        # 读取现有日志
        logs = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8-sig') as f:
                    logs = json.load(f)
            except Exception as e:
                print(f"读取日志文件失败: {e}")
                logs = []
        
        # 添加新日志
        logs.append(log_entry)
        
        # 写入日志文件
        with open(log_file, 'w', encoding='utf-8-sig') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
        
        print(f"LLM日志已记录到: {log_file}")
    except Exception as e:
        # 日志写入失败不影响主流程
        print(f"日志记录失败: {e}")

def call_llm(prompt, model=None, temperature=None, max_retries=3):
    config = load_config()
    
    api_key = config['api_key']
    api_url = config['api_url']
    model_name = model or config['model']
    temp = temperature if temperature is not None else config['temperature']
    
    # 记录开始时间
    start_time = time.time()
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    payload = {
        'model': model_name,
        'temperature': temp,
        'messages': [
            {'role': 'system', 'content': '你是一个专业的国际事务分析专家，擅长分析地缘政治和经贸安全事件。'},
            {'role': 'user', 'content': prompt}
        ]
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            print(f"LLM请求状态码: {response.status_code}")
            print(f"LLM请求URL: {api_url}")
            print(f"LLM请求模型: {model_name}")
            response.raise_for_status()
            result = response.json()
            print(f"LLM响应: {result}")
            
            # 计算耗时并记录日志
            duration_ms = int((time.time() - start_time) * 1000)
            response_content = result['choices'][0]['message']['content']
            log_llm_call(prompt, response_content, model_name, duration_ms, True)
            
            return response_content
        except requests.exceptions.RequestException as e:
            print(f"LLM调用失败(尝试 {attempt+1}/{max_retries}) - 请求异常: {str(e)}")
            # 检查response是否存在
            if 'response' in locals():
                print(f"响应内容: {response.text}")
                # 如果是429错误，等待后重试
                if response.status_code == 429:
                    wait_time = 2 ** attempt  # 指数退避
                    print(f"请求被限流，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                elif response.status_code == 401:
                    print(f"API密钥无效，请检查配置")
                    duration_ms = int((time.time() - start_time) * 1000)
                    log_llm_call(prompt, str(e), model_name, duration_ms, False)
                    return None
                else:
                    duration_ms = int((time.time() - start_time) * 1000)
                    log_llm_call(prompt, str(e), model_name, duration_ms, False)
                    return None
            else:
                # response未定义，说明请求根本没有发送成功
                print("请求未成功发送")
                duration_ms = int((time.time() - start_time) * 1000)
                log_llm_call(prompt, str(e), model_name, duration_ms, False)
                return None
        except Exception as e:
            print(f"LLM调用失败(尝试 {attempt+1}/{max_retries}) - 其他异常: {str(e)}")
            duration_ms = int((time.time() - start_time) * 1000)
            log_llm_call(prompt, str(e), model_name, duration_ms, False)
            return None
    
    print(f"LLM调用失败，已达到最大重试次数 {max_retries}")
    duration_ms = int((time.time() - start_time) * 1000)
    log_llm_call(prompt, f"已达到最大重试次数 {max_retries}", model_name, duration_ms, False)
    return None

def rule_based_parse_event(event_text):
    """基于规则的事件解析降级方案"""
    
    result = {
        'event_type': '其他',
        'region': '未知',
        'subject': 'USA',
        'opponent': '未知',
        'allies': ['美国'],
        'trigger_factors': [],
        'strategic_goal': '维护国家利益',
        'constraint_tags': [],
        'risk_tags': [],
        'possible_rules': []
    }
    
    # 分析事件类型
    if re.search(r'关税|贸易|进口|出口|商品', event_text):
        result['event_type'] = '贸易争端'
        result['constraint_tags'].append('BL-US-003')
        result['possible_rules'].append('RL-US-003')
    elif re.search(r'制裁|禁运|冻结资产', event_text):
        result['event_type'] = '经济制裁'
        result['constraint_tags'].append('BL-US-001')
        result['possible_rules'].append('RL-US-001')
    elif re.search(r'军队|部署|边境|战争|冲突', event_text):
        result['event_type'] = '地缘冲突'
        result['constraint_tags'].append('BL-US-002')
        result['possible_rules'].append('RL-US-002')
    elif re.search(r'导弹|核|武器|军事演习', event_text):
        result['event_type'] = '军事威胁'
        result['constraint_tags'].append('BL-US-002')
        result['risk_tags'].append('安全风险')
        result['possible_rules'].append('RL-US-002')
    elif re.search(r'技术|芯片|科技|专利|知识产权', event_text):
        result['event_type'] = '技术竞争'
        result['constraint_tags'].append('BL-US-004')
        result['possible_rules'].append('RL-US-004')
    elif re.search(r'反垄断|调查|罚款', event_text):
        result['event_type'] = '监管调查'
        result['constraint_tags'].append('BL-US-005')
        result['possible_rules'].append('RL-US-005')
    
    # 分析地区
    if re.search(r'中国|亚太|印太|亚洲', event_text):
        result['region'] = '印太'
    elif re.search(r'欧洲|欧盟', event_text):
        result['region'] = '欧洲'
    elif re.search(r'中东|伊朗|沙特', event_text):
        result['region'] = '中东'
    elif re.search(r'俄罗斯|乌克兰', event_text):
        result['region'] = '东欧'
    elif re.search(r'朝鲜|韩国|日本', event_text):
        result['region'] = '东北亚'
    elif re.search(r'南美|拉美', event_text):
        result['region'] = '拉美'
    else:
        result['region'] = '全球'
    
    # 分析对手
    if re.search(r'中国|北京', event_text):
        result['opponent'] = '中国'
    elif re.search(r'俄罗斯|莫斯科', event_text):
        result['opponent'] = '俄罗斯'
    elif re.search(r'朝鲜|平壤', event_text):
        result['opponent'] = '朝鲜'
    elif re.search(r'欧盟|布鲁塞尔', event_text):
        result['opponent'] = '欧盟'
    
    # 分析触发因素
    if re.search(r'宣布|决定|实施', event_text):
        result['trigger_factors'].append('政策变化')
    if re.search(r'紧张|冲突|争端', event_text):
        result['trigger_factors'].append('地区紧张局势')
    if re.search(r'安全|威胁', event_text):
        result['trigger_factors'].append('安全威胁')
    if re.search(r'利益|经济', event_text):
        result['trigger_factors'].append('经济利益驱动')
    
    # 设置风险标签
    if result['event_type'] in ['地缘冲突', '军事威胁']:
        result['risk_tags'].append('升级风险')
    if result['event_type'] in ['贸易争端', '经济制裁']:
        result['risk_tags'].append('经济风险')
    if result['opponent'] != '未知':
        result['risk_tags'].append('双边关系恶化')
    
    # 确保列表不为空
    if not result['trigger_factors']:
        result['trigger_factors'] = ['地区紧张局势']
    if not result['constraint_tags']:
        result['constraint_tags'] = ['BL-US-001', 'BL-US-002']
    if not result['risk_tags']:
        result['risk_tags'] = ['不确定性风险']
    if not result['possible_rules']:
        result['possible_rules'] = ['RL-US-001']
    
    return result

def parse_event(event_text):
    prompt = f"""请将以下事件解析为结构化特征：
    
事件描述：{event_text}

请输出JSON格式，包含以下字段：
- event_type: 事件类型（如：地缘冲突、贸易争端、技术竞争等）
- region: 涉及地区（如：亚太、欧洲、中东等）
- subject: 主体（通常是美国）
- opponent: 对手/目标国家
- allies: 盟友列表
- trigger_factors: 触发因素列表
- strategic_goal: 战略目标
- constraint_tags: 约束标签列表（如：BL-US-001, BL-US-002）
- risk_tags: 风险标签列表
- possible_rules: 可能涉及的规则ID列表（如：RL-US-001）
"""
    
    result = call_llm(prompt)
    
    if result:
        try:
            parsed_result = json.loads(result)
            print(f"LLM解析成功")
            return parsed_result
        except Exception as e:
            print(f"LLM响应解析失败: {str(e)}")
    
    # LLM调用失败或返回结果无效，使用基于规则的降级解析
    print("使用基于规则的降级解析")
    return rule_based_parse_event(event_text)

def calculate_similarity(event_features, case):
    # 获取事件特征
    event_type = event_features.get('event_type', '')
    event_region = event_features.get('region', '')
    event_opponent = event_features.get('opponent', '')
    event_subject = event_features.get('subject', '')
    event_triggers = ' '.join(event_features.get('trigger_factors', []))
    event_goal = event_features.get('strategic_goal', '')
    event_tags = set(event_features.get('constraint_tags', []) + 
                    event_features.get('risk_tags', []) + 
                    event_features.get('possible_rules', []))
    
    # 获取案例特征
    case_type = case.get('case_type', '')
    case_stakeholders = case.get('stakeholders', [])
    case_trigger = case.get('trigger_event', '')
    case_goal = case.get('strategic_goal', '')
    case_tags = set(case.get('similar_tag', []))
    case_constraints = set(case.get('constraints', []))
    
    # 1. 事件类型匹配 (权重0.25)
    type_score = 0.0
    if event_type and case_type:
        # 检查事件类型是否是案例类型的子类型
        if event_type in case_type:
            type_score = 1.0
        # 检查关键词匹配
        type_keywords = {
            '贸易争端': ['贸易', '关税', '进口', '出口', '商品'],
            '经济制裁': ['制裁', '禁运', '冻结', '资产'],
            '地缘冲突': ['冲突', '军队', '部署', '边境'],
            '军事威胁': ['导弹', '核', '武器', '军事演习'],
            '技术竞争': ['技术', '芯片', '科技', '专利'],
            '监管调查': ['反垄断', '调查', '罚款']
        }
        if event_type in type_keywords:
            for keyword in type_keywords[event_type]:
                if keyword in case_type or keyword in case_trigger:
                    type_score = max(type_score, 0.7)
                    break
    type_score *= 0.25
    
    # 2. 地区匹配 (权重0.20)
    region_score = 0.0
    region_keywords = {
        '印太': ['中国', '日本', '韩国', '菲律宾', '澳大利亚', '台湾', '南海', '台海', '印太'],
        '欧洲': ['欧盟', '德国', '法国', '英国', '俄罗斯', '乌克兰', '芬兰', '瑞典', '欧洲'],
        '中东': ['以色列', '伊朗', '沙特', '埃及', '卡塔尔', '加沙', '红海', '胡塞', '中东'],
        '东北亚': ['朝鲜', '韩国', '日本', '东北亚'],
        '东欧': ['俄罗斯', '乌克兰', '东欧'],
        '拉美': ['巴西', '墨西哥', '拉美'],
        '全球': ['G7', '北约', '联合国', '全球']
    }
    
    # 检查地区关键词
    if event_region in region_keywords:
        case_text = str(case_stakeholders) + ' ' + case_trigger
        for keyword in region_keywords[event_region]:
            if keyword in case_text:
                region_score = 1.0
                break
    region_score *= 0.20
    
    # 3. 行为者匹配 (权重0.25)
    actor_score = 0.0
    stakeholders_text = str(case_stakeholders)
    
    # 对手匹配
    if event_opponent and event_opponent in stakeholders_text:
        actor_score += 0.5
    # 主体匹配
    if event_subject and event_subject in stakeholders_text:
        actor_score += 0.3
    # 盟友匹配
    event_allies = event_features.get('allies', [])
    for ally in event_allies:
        if ally in stakeholders_text:
            actor_score += 0.1
            break
    actor_score = min(actor_score, 1.0) * 0.25
    
    # 4. 标签匹配 (权重0.15)
    tag_score = 0.0
    # 代码标签匹配
    code_intersection = event_tags & case_constraints
    if code_intersection:
        tag_score += 0.5
    # 文本标签匹配
    event_tag_text = ' '.join(list(event_tags))
    case_tag_text = ' '.join(list(case_tags))
    if event_tag_text and case_tag_text:
        for tag in event_tag_text.split():
            if tag in case_tag_text:
                tag_score += 0.3
                break
    tag_score = min(tag_score, 1.0) * 0.15
    
    # 5. 语义内容匹配 (权重0.15)
    content_score = 0.0
    # 战略目标匹配
    if event_goal and case_goal:
        if event_goal in case_goal or case_goal in event_goal:
            content_score += 0.5
    # 触发因素匹配
    if event_triggers and case_trigger:
        for trigger in event_triggers.split():
            if trigger in case_trigger:
                content_score += 0.3
                break
    content_score = min(content_score, 1.0) * 0.15
    
    # 计算总分
    similarity_score = type_score + region_score + actor_score + tag_score + content_score
    
    return min(max(similarity_score, 0), 1)

def generate_initial_measures(similar_cases, event_features):
    if not similar_cases:
        return None
    
    event_type = event_features.get('event_type', '')
    event_region = event_features.get('region', '')
    event_opponent = event_features.get('opponent', '')
    
    # 根据事件类型生成针对性措施
    type_based_measures = {
        '贸易争端': [
            {'action': '关税反制', 'description': '对目标国家进口商品加征报复性关税', 'risk': '贸易战升级风险', 'rules': ['RL-US-003', 'BL-US-003']},
            {'action': 'WTO诉讼', 'description': '通过世界贸易组织提起诉讼', 'risk': '诉讼周期长', 'rules': ['RL-US-003']},
            {'action': '双边谈判', 'description': '通过双边渠道进行贸易谈判', 'risk': '谈判破裂风险', 'rules': ['BL-US-001']},
            {'action': '产业补贴', 'description': '对受影响产业提供补贴支持', 'risk': '财政负担', 'rules': ['BL-US-003']},
            {'action': '市场多元化', 'description': '开拓新的贸易市场', 'risk': '短期成本增加', 'rules': ['BL-US-003']}
        ],
        '经济制裁': [
            {'action': '金融制裁', 'description': '冻结目标国家资产，限制金融交易', 'risk': '金融系统风险', 'rules': ['RL-US-001', 'BL-US-001']},
            {'action': '贸易禁运', 'description': '禁止与目标国家的特定贸易', 'risk': '自身经济影响', 'rules': ['RL-US-001', 'BL-US-002']},
            {'action': '投资限制', 'description': '限制对目标国家的投资', 'risk': '投资回报损失', 'rules': ['BL-US-004']},
            {'action': '资产冻结', 'description': '冻结相关个人和实体资产', 'risk': '法律诉讼风险', 'rules': ['RL-US-001']},
            {'action': 'SWIFT制裁', 'description': '将目标国家排除出SWIFT系统', 'risk': '全球金融影响', 'rules': ['RL-US-001', 'BL-US-004']}
        ],
        '地缘冲突': [
            {'action': '军事威慑', 'description': '展示军事力量，形成威慑态势', 'risk': '误判升级风险', 'rules': ['RL-US-002', 'BL-US-002']},
            {'action': '盟友协调', 'description': '与盟友进行多边安全协调', 'risk': '盟友分歧', 'rules': ['BL-US-001']},
            {'action': '情报共享', 'description': '加强情报收集和共享', 'risk': '情报泄露', 'rules': ['BL-US-004']},
            {'action': '边境部署', 'description': '在边境地区部署军事力量', 'risk': '冲突升级', 'rules': ['RL-US-002']},
            {'action': '外交谴责', 'description': '通过外交渠道强烈谴责', 'risk': '效果有限', 'rules': ['BL-US-001']}
        ],
        '军事威胁': [
            {'action': '防空部署', 'description': '加强防空系统部署', 'risk': '成本高昂', 'rules': ['RL-US-002']},
            {'action': '联合军演', 'description': '与盟友进行联合军事演习', 'risk': '刺激对手', 'rules': ['BL-US-002']},
            {'action': '武器援助', 'description': '向盟友提供武器援助', 'risk': '卷入冲突', 'rules': ['RL-US-002', 'BL-US-002']},
            {'action': '导弹防御', 'description': '加强导弹防御系统', 'risk': '技术难度', 'rules': ['RL-US-002']},
            {'action': '外交斡旋', 'description': '通过第三方进行外交斡旋', 'risk': '斡旋失败', 'rules': ['BL-US-001']}
        ],
        '技术竞争': [
            {'action': '出口管制', 'description': '限制高端技术出口', 'risk': '产业影响', 'rules': ['RL-US-004', 'BL-US-004']},
            {'action': '研发投入', 'description': '加大本土研发投入', 'risk': '投入大周期长', 'rules': ['BL-US-004']},
            {'action': '人才吸引', 'description': '吸引全球顶尖科技人才', 'risk': '竞争激烈', 'rules': ['BL-US-004']},
            {'action': '标准制定', 'description': '主导国际技术标准制定', 'risk': '协调难度', 'rules': ['BL-US-004']},
            {'action': '投资审查', 'description': '加强外资技术并购审查', 'risk': '投资环境影响', 'rules': ['RL-US-004']}
        ],
        '监管调查': [
            {'action': '反垄断调查', 'description': '启动反垄断调查程序', 'risk': '法律挑战', 'rules': ['RL-US-005']},
            {'action': '罚款处罚', 'description': '对违规企业处以罚款', 'risk': '法律诉讼', 'rules': ['RL-US-005']},
            {'action': '强制拆分', 'description': '强制拆分垄断企业', 'risk': '市场影响', 'rules': ['RL-US-005']},
            {'action': '合规要求', 'description': '提出整改合规要求', 'risk': '执行难度', 'rules': ['BL-US-005']},
            {'action': '行业监管', 'description': '加强行业监管力度', 'risk': '监管成本', 'rules': ['BL-US-005']}
        ]
    }
    
    # 获取当前事件类型对应的措施模板
    if event_type in type_based_measures:
        measure_templates = type_based_measures[event_type]
    else:
        measure_templates = [
            {'action': '外交斡旋', 'description': '通过外交渠道进行沟通和谈判', 'risk': '谈判破裂风险', 'rules': ['BL-US-001']},
            {'action': '经济制裁', 'description': '实施针对性的经济制裁措施', 'risk': '反制风险', 'rules': ['RL-US-001']},
            {'action': '军事威慑', 'description': '展示军事力量', 'risk': '升级风险', 'rules': ['RL-US-002']},
            {'action': '多边协调', 'description': '与盟友进行协调', 'risk': '分歧风险', 'rules': ['BL-US-001']},
            {'action': '技术限制', 'description': '实施技术出口限制', 'risk': '产业影响', 'rules': ['BL-US-004']}
        ]
    
    measures = []
    
    # 从排名第一的相似案例中提取决策措施作为参考
    top_case = similar_cases[0]
    case_measures = top_case.get('decision_measures', [])
    
    # 生成措施
    for i, template in enumerate(measure_templates):
        # 始终参考排名第一的案例
        ref_case = top_case
        
        # 生成适用条件描述
        conditions = f"事件类型: {event_type}"
        if event_region:
            conditions += f"，地区: {event_region}"
        if event_opponent:
            conditions += f"，对手: {event_opponent}"
        
        # 生成迁移逻辑
        transfer_logic = f"参考{ref_case.get('case_label', '历史案例')}的经验"
        if case_measures:
            transfer_logic += f"，借鉴措施: {', '.join(case_measures[:2])}"
        
        measures.append({
            'measure_id': f'M{i+1}',
            'measure_text': f'{template["action"]}: {template["description"]}',
            'reference_case': ref_case.get('case_id', 'UNKNOWN'),
            'transfer_logic': transfer_logic,
            'applicable_conditions': conditions,
            'risk_hint': template.get('risk', '需评估可能的风险'),
            'possible_rules': template.get('rules', ['BL-US-001', 'BL-US-002']),
            'confidence': min(0.95, 0.75 + i * 0.03)
        })
    
    # 如果措施不足10条，补充通用措施
    generic_measures = [
        {'action': '情报收集', 'description': '加强情报收集和分析工作', 'risk': '情报准确性', 'rules': ['BL-US-004']},
        {'action': '舆论宣传', 'description': '开展国际舆论宣传工作', 'risk': '舆论反弹', 'rules': ['BL-US-001']},
        {'action': '法律准备', 'description': '做好法律诉讼准备', 'risk': '法律成本', 'rules': ['RL-US-005']},
        {'action': '能源安全', 'description': '确保能源供应安全', 'risk': '能源价格波动', 'rules': ['BL-US-003']},
        {'action': '供应链调整', 'description': '调整关键供应链布局', 'risk': '短期成本', 'rules': ['BL-US-003']},
        {'action': '多边协调', 'description': '与多边组织进行协调', 'risk': '协调难度', 'rules': ['BL-US-001']},
        {'action': '国内动员', 'description': '动员国内相关资源', 'risk': '资源紧张', 'rules': ['BL-US-002']},
        {'action': '预案制定', 'description': '制定应急预案', 'risk': '预案适用性', 'rules': ['BL-US-002']},
        {'action': '媒体沟通', 'description': '加强媒体沟通', 'risk': '舆论风险', 'rules': ['BL-US-001']},
        {'action': '态势监控', 'description': '持续监控态势发展', 'risk': '监控盲区', 'rules': ['BL-US-004']}
    ]
    
    # 获取已有的措施动作，避免重复
    existing_actions = {m['measure_text'].split(':')[0] for m in measures}
    
    i = len(measures)
    for template in generic_measures:
        if i >= 10:
            break
        action_name = template['action']
        if action_name not in existing_actions:
            # 始终参考排名第一的案例
            measures.append({
                'measure_id': f'M{i+1}',
                'measure_text': f'{template["action"]}: {template["description"]}',
                'reference_case': top_case.get('case_id', 'UNKNOWN'),
                'transfer_logic': f'参考{top_case.get("case_label", "历史案例")}的经验',
                'applicable_conditions': conditions if 'conditions' in locals() else '当前局势',
                'risk_hint': template.get('risk', '需评估可能的风险'),
                'possible_rules': template.get('rules', ['BL-US-001', 'BL-US-002']),
                'confidence': min(0.95, 0.70 + i * 0.02)
            })
            existing_actions.add(action_name)
            i += 1
    
    return measures

def check_org_violation(measure, legal_rules):
    matched_rules = []
    measure_text = measure.get('measure_text', '')
    
    if not measure_text or not legal_rules:
        return {'matched_rules': matched_rules}
    
    # 阶段一：先通过action_type筛选候选规则
    candidate_rules = []
    for rule in legal_rules:
        action_type = rule.get('action_type', '')
        print("检查规则:", rule.get('rule_id', ''), ", action_type: '", action_type, "'", sep='')
        if is_action_type_matched(measure_text, action_type):
            print("匹配成功! action_type: '", action_type, "'", sep='')
            candidate_rules.append(rule)
        else:
            print("匹配失败")
    
    if not candidate_rules:
        print("阶段一：无匹配的action_type，措施内容:", measure_text)
        return {'matched_rules': matched_rules, 'reasoning': '未匹配到任何行动类型，无需进行LLM分析', 'candidate_rules': []}
    
    print("阶段一：匹配到", len(candidate_rules), "个候选规则")
    
    # 阶段二：将候选规则的violation_action与措施文本进行比对分析
    # 构建详细的规则信息，包含violation_action
    rules_detail_text = "\n".join([
        f"规则ID: {rule['rule_id']}\n规则名称: {rule['rule_name']}\n行动类型: {rule['action_type']}\n禁止行为: {rule.get('violation_action', '')}" 
        for rule in candidate_rules
    ])
    
    prompt = f"""
你是法律合规专家，请分析以下措施内容，并判断它是否触发了候选法律规则中描述的禁止行为。

措施内容：{measure_text}

候选法律规则详情：
{rules_detail_text}

分析要求：
1. 仔细阅读每个候选规则的"禁止行为"描述
2. 判断措施内容是否属于该禁止行为的行为、适用对象、条件等的范畴
3. 只有当措施内容明确违反了禁止行为、适用对象、条件描述时，才判定为触发
4. 如果措施是合法行为或与禁止行为无关，则不触发

请输出JSON格式结果，包含以下字段：
- triggered_rule_ids: 被措施触发的规则ID列表（未触发任何规则则为空数组）
- reasoning: 判断理由，用一句话简要概述即可

注意：
1. 禁止行为描述中的条件（如"未经授权"、"未申报"等）是判断的关键
2. 如果措施内容与禁止行为描述语义差异较大，不应强行匹配
3. 输出必须是有效的JSON格式
4. reasoning字段请务必用一句话简要概述，不要冗长
"""
    
    result = call_llm(prompt)
    
    if result:
        try:
            # 移除可能的代码块标记
            cleaned_result = result.strip()
            if cleaned_result.startswith('```json'):
                cleaned_result = cleaned_result[7:]
            if cleaned_result.endswith('```'):
                cleaned_result = cleaned_result[:-3]
            cleaned_result = cleaned_result.strip()
            
            parsed_result = json.loads(cleaned_result)
            matched_rules = parsed_result.get('triggered_rule_ids', [])
            reasoning = parsed_result.get('reasoning', '')
            
            # 如果reasoning是字典，转换为字符串
            if isinstance(reasoning, dict):
                reasoning_str = ""
                for rule_id, reason in reasoning.items():
                    reasoning_str += f"{rule_id}: {reason}\n"
                reasoning = reasoning_str.strip()
            
            print(f"阶段二：LLM判断结果 - 触发规则: {matched_rules}")
            print(f"阶段二：判断理由: {reasoning[:100] if isinstance(reasoning, str) else str(reasoning)[:100]}...")
            return {'matched_rules': matched_rules, 'reasoning': reasoning, 'candidate_rules': candidate_rules}
        except Exception as e:
            print(f"LLM响应解析失败: {str(e)}")
            print(f"原始响应: {result[:200]}...")
            return {'matched_rules': [], 'reasoning': f'【LLM解析失败】响应格式错误: {str(e)}', 'candidate_rules': candidate_rules}
    
    # LLM调用失败（result为None）
    print("LLM调用失败")
    return {'matched_rules': [], 'reasoning': '【LLM调用失败】无法连接到LLM服务，请检查配置或稍后重试', 'candidate_rules': candidate_rules}


# 行动类型关键词映射配置
ACTION_TYPE_KEYWORDS = {
    '军事行动': ['军事', '军队', '部署', '威慑', '军演', '武器', '导弹', '使用武力', '战机', '空袭', '攻击', '入侵', '作战', '阵地', '武装', '防卫', '防御', '军事力量'],
    '金融封锁': ['封锁', '制裁', '禁运', '冻结', '资产', '金融', '霍尔木兹', '资金冻结', '金融制裁'],
    '出口管制': ['出口', '管制', '技术', '芯片', '产品', '物品', '出口限制', '技术出口', '敏感技术'],
    '武器出口': ['武器', '军售', '军事援助', '武器援助', '国防物品', '军火', '武器转让'],
    '秘密行动': ['秘密', '情报', '网络', '攻击', '间谍', '情报收集', '网络战', '黑客'],
    '经济制裁': ['制裁', '禁运', '冻结资产', '金融制裁', 'SWIFT', '经济制裁', '贸易制裁'],
    '关税措施': ['关税', '贸易', '进口', '出口', '商品', '贸易限制', '关税壁垒', '进口税'],
    '外资审查': ['投资', '审查', '并购', '外资', 'CFIUS', '外国投资', '国家安全审查'],
    '技术限制': ['技术', '芯片', '出口管制', '技术限制', '关键技术', '技术封锁', '技术制裁'],
    '对外援助': ['援助', '援助资金', '经济援助', '人道主义援助', '发展援助'],
    '产业控制': ['产业控制', '关键产业', '控制权转移', '企业收购', '股权收购'],
    '军备控制': ['导弹', '核武器', '中导', '军备控制', '核不扩散', '裁军'],
    '外交抗议': ['抗议', '谴责', '声明', '外交照会', '强烈不满', '严正抗议'],
    '情报活动': ['情报', '侦察', '监视', '情报收集', '情报共享'],
    '贸易壁垒': ['贸易壁垒', '贸易保护', '进口限制', '配额', '贸易战'],
    '能源制裁': ['能源', '石油', '天然气', '能源禁运', '能源制裁'],
    '资产冻结': ['资产冻结', '冻结账户', '财产冻结', '资金冻结'],
    '旅行限制': ['旅行禁令', '签证限制', '入境限制', '旅行限制'],
    '外交制裁': ['外交制裁', '驱逐大使', '断交', '召回大使'],
    '金融制裁': ['金融制裁', '银行制裁', '金融限制', 'SWIFT制裁']
}

def is_action_type_matched(measure_text, action_type):
    """判断措施内容是否与行动类型匹配（基于关键词映射）"""
    if action_type in ACTION_TYPE_KEYWORDS:
        keywords = ACTION_TYPE_KEYWORDS[action_type]
        for keyword in keywords:
            if keyword in measure_text:
                return True
    return False

def fallback_check_org_violation(measure, legal_rules):
    """降级的关键词匹配方案"""
    matched_rules = []
    matched_details = []
    measure_text = measure.get('measure_text', '')
    
    # 定义行动类型与关键词的映射
    action_type_keywords = {
        '经济制裁': ['制裁', '禁运', '冻结资产', '金融制裁', 'SWIFT'],
        '军事行动': ['军事', '军队', '部署', '威慑', '军演', '武器', '导弹'],
        '武器出口': ['武器', '军售', '军事援助', '武器援助'],
        '关税措施': ['关税', '贸易', '进口', '出口', '商品'],
        '外资审查': ['投资', '审查', '并购', '外资'],
        '技术限制': ['技术', '芯片', '出口管制', '技术限制'],
        '对外援助': ['援助', '援助资金', '经济援助']
    }
    
    for rule in legal_rules:
        action_type = rule.get('action_type', '')
        if action_type in action_type_keywords:
            keywords = action_type_keywords[action_type]
            for keyword in keywords:
                if keyword in measure_text:
                    matched_rules.append(rule['rule_id'])
                    matched_details.append(f"规则 {rule['rule_id']} ({rule['rule_name']})：措施包含关键词'{keyword}'，匹配行动类型'{action_type}'")
                    break
    
    if matched_details:
        reasoning = '【降级方案-关键词匹配】\n' + '\n'.join(matched_details)
    else:
        reasoning = '【降级方案-关键词匹配】未找到匹配的法律规则'
    
    return {'matched_rules': matched_rules, 'reasoning': reasoning}

def resolve_conflict(rules):
    if not rules:
        return None
    
    class_priority = {'宪法': 3, '联邦法律': 2, '国际条约': 2}
    
    rules_with_priority = []
    for rule in rules:
        priority = class_priority.get(rule.get('rule_class'), 1)
        rules_with_priority.append({
            'rule': rule,
            'priority': priority,
            'year': rule.get('enacted_year', 0)
        })
    
    rules_with_priority.sort(key=lambda x: (-x['priority'], -x['year']))
    
    top_rule = rules_with_priority[0]['rule']
    
    reasoning = f"规则优先级分析：\n"
    reasoning += f"- 法律类型优先级：宪法 > 联邦法律 = 国际条约\n"
    reasoning += f"- 同类型法律：后法 > 前法\n"
    reasoning += f"最终选择规则: {top_rule['rule_id']} ({top_rule['rule_name']})"
    
    return {
        'priority_rule_id': top_rule['rule_id'],
        'final_rule_type': top_rule['rule_type'],
        'reasoning': reasoning
    }

def generate_remedy_measure(original_measure, reference_case, event_features):
    """
    根据原始措施和参考案例生成修正措施
    :param original_measure: 原始待修正措施
    :param reference_case: 参考案例（排名第二或第三的案例）
    :param event_features: 事件特征
    :return: 修正后的措施
    """
    original_text = original_measure.get('measure_text', '')
    
    # 从原始措施中提取领域
    domain_keywords = {
        '贸易': ['贸易', '关税', '进口', '出口', '商品', 'WTO'],
        '金融': ['金融', '制裁', '禁运', '冻结', '资产', 'SWIFT'],
        '军事': ['军事', '军队', '部署', '威慑', '军演', '武器', '导弹'],
        '外交': ['外交', '谈判', '斡旋', '协调', '谴责', '多边'],
        '技术': ['技术', '芯片', '出口管制', '研发', '人才'],
        '情报': ['情报', '监控', '收集', '共享']
    }
    
    domain = '外交'
    for d, keywords in domain_keywords.items():
        for keyword in keywords:
            if keyword in original_text:
                domain = d
                break
        if domain != '外交':
            break
    
    # 根据领域生成替代措施模板
    remedy_templates = {
        '贸易': [
            {'action': '贸易协商', 'description': '通过双边贸易谈判解决分歧', 'risk': '谈判周期长', 'rules': ['BL-US-001', 'BL-US-003']},
            {'action': '关税调整', 'description': '适度调整关税政策', 'risk': '贸易影响', 'rules': ['RL-US-003', 'BL-US-003']},
            {'action': '贸易救济', 'description': '申请贸易救济措施', 'risk': '法律程序复杂', 'rules': ['RL-US-003']},
            {'action': '市场准入', 'description': '协商市场准入条件', 'risk': '对方不配合', 'rules': ['BL-US-003']},
            {'action': '标准协调', 'description': '协调产品标准和认证', 'risk': '协调难度大', 'rules': ['BL-US-003']}
        ],
        '金融': [
            {'action': '金融监管', 'description': '加强金融监管合作', 'risk': '执行难度', 'rules': ['BL-US-001']},
            {'action': '资产监控', 'description': '监控相关资产流动', 'risk': '信息获取难度', 'rules': ['BL-US-004']},
            {'action': '金融对话', 'description': '开展金融政策对话', 'risk': '效果不确定', 'rules': ['BL-US-001']},
            {'action': '风险预警', 'description': '建立金融风险预警机制', 'risk': '预警准确性', 'rules': ['BL-US-004']},
            {'action': '流动性支持', 'description': '提供流动性支持', 'risk': '资金压力', 'rules': ['BL-US-003']}
        ],
        '军事': [
            {'action': '军事交流', 'description': '开展军事交流活动', 'risk': '时机敏感', 'rules': ['BL-US-001']},
            {'action': '情报共享', 'description': '加强情报共享合作', 'risk': '情报安全', 'rules': ['BL-US-004']},
            {'action': '联合演习', 'description': '举行联合军事演习', 'risk': '刺激对手', 'rules': ['BL-US-002']},
            {'action': '装备展示', 'description': '展示军事装备实力', 'risk': '误判风险', 'rules': ['BL-US-002']},
            {'action': '边境巡逻', 'description': '加强边境巡逻力度', 'risk': '冲突风险', 'rules': ['BL-US-002']}
        ],
        '外交': [
            {'action': '外交谈判', 'description': '通过外交渠道谈判解决', 'risk': '谈判破裂', 'rules': ['BL-US-001']},
            {'action': '多边协调', 'description': '通过多边组织协调', 'risk': '协调难度', 'rules': ['BL-US-001']},
            {'action': '高层对话', 'description': '举行高层对话', 'risk': '时机不成熟', 'rules': ['BL-US-001']},
            {'action': '外交照会', 'description': '发送外交照会表达立场', 'risk': '效果有限', 'rules': ['BL-US-001']},
            {'action': '领事沟通', 'description': '通过领事渠道沟通', 'risk': '级别有限', 'rules': ['BL-US-001']}
        ],
        '技术': [
            {'action': '技术合作', 'description': '开展技术合作项目', 'risk': '技术泄露', 'rules': ['BL-US-004']},
            {'action': '研发投入', 'description': '加大本土研发投入', 'risk': '周期长', 'rules': ['BL-US-004']},
            {'action': '技术引进', 'description': '引进关键技术', 'risk': '成本高', 'rules': ['BL-US-004']},
            {'action': '标准制定', 'description': '主导国际技术标准', 'risk': '协调难度', 'rules': ['BL-US-004']},
            {'action': '人才培养', 'description': '加强人才培养', 'risk': '周期长', 'rules': ['BL-US-004']}
        ],
        '情报': [
            {'action': '情报收集', 'description': '加强情报收集工作', 'risk': '准确性', 'rules': ['BL-US-004']},
            {'action': '态势监控', 'description': '持续监控态势发展', 'risk': '盲区', 'rules': ['BL-US-004']},
            {'action': '分析研判', 'description': '深入分析研判', 'risk': '误判', 'rules': ['BL-US-004']},
            {'action': '预警发布', 'description': '发布风险预警', 'risk': '误报', 'rules': ['BL-US-004']},
            {'action': '信息共享', 'description': '与盟友共享信息', 'risk': '泄露', 'rules': ['BL-US-004']}
        ]
    }
    
    templates = remedy_templates.get(domain, remedy_templates['外交'])
    
    # 随机选择一个模板（避免与原始措施重复）
    import random
    available_templates = [t for t in templates if t['action'] not in original_text]
    if not available_templates:
        available_templates = templates
    
    template = random.choice(available_templates)
    
    # 获取事件信息
    event_type = event_features.get('event_type', '')
    event_region = event_features.get('region', '')
    event_opponent = event_features.get('opponent', '')
    
    conditions = f"事件类型: {event_type}"
    if event_region:
        conditions += f"，地区: {event_region}"
    if event_opponent:
        conditions += f"，对手: {event_opponent}"
    
    # 生成修正措施
    remedy_measure = {
        'measure_id': original_measure.get('measure_id', 'REMEDY') + '-R',
        'measure_text': f'{template["action"]}: {template["description"]}',
        'reference_case': reference_case.get('case_id', 'UNKNOWN'),
        'transfer_logic': f"参考{reference_case.get('case_label', '参考案例')}的经验，针对{domain}领域生成替代措施",
        'applicable_conditions': conditions,
        'risk_hint': template.get('risk', '需评估可能的风险'),
        'possible_rules': template.get('rules', ['BL-US-001', 'BL-US-002']),
        'confidence': 0.85,
        'remedy_count': original_measure.get('remedy_count', 0) + 1
    }
    
    return remedy_measure
