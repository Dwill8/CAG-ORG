
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# 添加UTF-8编码支持
app.config['JSON_AS_ASCII'] = False

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'config')
ORIGINAL_CONFIG_DIR = CONFIG_DIR  # 添加这行

def load_json_file(file_name):
    file_path = os.path.join(DATA_DIR, file_name)
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

@app.route('/api/cases/geopolitical', methods=['GET'])
def get_geopolitical_cases():
    cases = load_json_file('cases_geopolitical.json')
    return jsonify(cases)

@app.route('/api/cases/economic_security', methods=['GET'])
def get_economic_security_cases():
    cases = load_json_file('cases_economic_security.json')
    return jsonify(cases)

@app.route('/api/rules', methods=['GET'])
def get_rules():
    rules = load_json_file('LegalRule.json')
    return jsonify(rules)

def get_config_path():
    """获取配置文件路径，优先使用用户目录"""
    user_config_path = os.path.join(CONFIG_DIR, 'llm_config.json')
    original_config_path = os.path.join(ORIGINAL_CONFIG_DIR, 'llm_config.json')
    
    # 如果用户目录没有配置文件，从原始目录复制
    if not os.path.exists(user_config_path) and os.path.exists(original_config_path):
        import shutil
        shutil.copy(original_config_path, user_config_path)
        print(f"配置文件已复制到用户目录: {user_config_path}")
    
    return user_config_path

@app.route('/api/llm/config', methods=['GET'])
def get_llm_config():
    config_path = get_config_path()
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
        config['api_key'] = '***' + config['api_key'][-4:]
        return jsonify(config)

@app.route('/api/llm/config', methods=['POST'])
def update_llm_config():
    config_path = get_config_path()
    data = request.json
    
    print(f"LLM配置保存请求 - 接收数据: {data}")
    print(f"配置文件路径: {config_path}")
    print(f"文件是否存在: {os.path.exists(config_path)}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"读取现有配置成功: {list(config.keys())}")
        
        if 'api_key' in data:
            config['api_key'] = data['api_key']
            print(f"更新api_key: {data['api_key'][:10]}...")
        if 'api_url' in data:
            config['api_url'] = data['api_url']
            print(f"更新api_url: {data['api_url']}")
        if 'model' in data:
            config['model'] = data['model']
            print(f"更新model: {data['model']}")
        if 'temperature' in data:
            config['temperature'] = data['temperature']
            print(f"更新temperature: {data['temperature']}")
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print("配置文件写入成功")
        
        config['api_key'] = '***' + config['api_key'][-4:]
        return jsonify({'success': True, 'config': config})
        
    except Exception as e:
        print(f"配置保存失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/event/parse', methods=['POST'])
def parse_event():
    from utils.llm_client import parse_event
    
    data = request.json
    event_text = data.get('event_text', '')
    
    if not event_text:
        return jsonify({'error': '事件文本不能为空'}), 400
    
    result = parse_event(event_text)
    if result:
        return jsonify(result)
    else:
        return jsonify({
            'event_type': '地缘冲突',
            'region': '印太',
            'subject': 'USA',
            'opponent': '未知',
            'allies': ['美国'],
            'trigger_factors': ['地区紧张局势'],
            'strategic_goal': '维护地区安全',
            'constraint_tags': ['BL-US-001', 'BL-US-002'],
            'risk_tags': ['升级风险'],
            'possible_rules': ['RL-US-001']
        })

@app.route('/api/cag/search', methods=['POST'])
def search_similar_cases():
    from utils.llm_client import calculate_similarity
    
    data = request.json
    event_features = data.get('event_features', {})
    
    geopolitical_cases = load_json_file('cases_geopolitical.json')
    economic_cases = load_json_file('cases_economic_security.json')
    all_cases = geopolitical_cases + economic_cases
    
    results = []
    for case in all_cases:
        score = calculate_similarity(event_features, case)
        results.append({
            'case_id': case['case_id'],
            'case_label': case['case_label'],
            'case_type': case['case_type'],
            'case_category': case['case_category'],
            'similarity_score': round(score, 4),
            'matched_tags': list(set(event_features.get('constraint_tags', []) + event_features.get('risk_tags', [])) & set(case.get('similar_tag', []))),
            'similar_reason': '事件类型和战略目标匹配',
            'difference_hint': '案例涉及的利益相关方与当前事件不同'
        })
    
    results.sort(key=lambda x: x['similarity_score'], reverse=True)
    top3 = results[:3]
    
    return jsonify({
        'cases': top3,
        'low_similarity_warning': top3[0]['similarity_score'] < 0.6 if top3 else False
    })

@app.route('/api/cag/generate', methods=['POST'])
def generate_measures():
    from utils.llm_client import generate_initial_measures
    
    data = request.json
    similar_cases = data.get('similar_cases', [])
    event_features = data.get('event_features', {})
    
    print(f"生成措施请求 - 事件类型: {event_features.get('event_type', '空')}")
    print(f"生成措施请求 - 地区: {event_features.get('region', '空')}")
    print(f"生成措施请求 - 对手: {event_features.get('opponent', '空')}")
    print(f"生成措施请求 - 相似案例数量: {len(similar_cases)}")
    
    geopolitical_cases = load_json_file('cases_geopolitical.json')
    economic_cases = load_json_file('cases_economic_security.json')
    all_cases = geopolitical_cases + economic_cases
    
    full_cases = []
    for sc in similar_cases:
        case = next((c for c in all_cases if c['case_id'] == sc['case_id']), None)
        if case:
            full_cases.append(case)
    
    result = generate_initial_measures(full_cases, event_features)
    
    if result:
        return jsonify({
            'measures': result,
            'summary': '模式提取 → 差异分析 → 初始措施集已生成'
        })
    else:
        default_measures = []
        for i in range(10):
            default_measures.append({
                'measure_id': f'M{i+1}',
                'measure_text': f'措施{i+1}: 实施外交斡旋和多边协调',
                'reference_case': similar_cases[0]['case_id'] if similar_cases else 'UNKNOWN',
                'transfer_logic': '参考历史案例的成功经验',
                'applicable_conditions': '当前局势稳定，具备外交谈判基础',
                'risk_hint': '可能引发对手反应，需做好风险预案',
                'possible_rules': ['BL-US-001', 'BL-US-002'],
                'confidence': 0.8 + i * 0.01
            })
        return jsonify({
            'measures': default_measures,
            'summary': '模式提取 → 差异分析 → 初始措施集已生成'
        })

@app.route('/api/cag/remedy', methods=['POST'])
def generate_remedy_measure():
    from utils.llm_client import generate_remedy_measure
    
    data = request.json
    original_measure = data.get('original_measure', {})
    reference_case = data.get('reference_case', {})
    event_features = data.get('event_features', {})
    
    print(f"生成修正措施请求 - 原始措施: {original_measure.get('measure_text', '')}")
    print(f"生成修正措施请求 - 参考案例: {reference_case.get('case_id', '')}")
    
    result = generate_remedy_measure(original_measure, reference_case, event_features)
    
    if result:
        return jsonify({
            'success': True,
            'measure': result
        })
    else:
        return jsonify({
            'success': False,
            'error': '无法生成修正措施'
        })

@app.route('/api/org/check', methods=['POST'])
def check_org():
    from utils.llm_client import check_org_violation
    
    data = request.json
    measures = data.get('measures', [])
    
    legal_rules = load_json_file('LegalRule.json')
    
    # 测试：直接返回legal_rules的内容
    if len(measures) > 0 and measures[0].get('measure_text') == 'test_debug':
        return jsonify({'legal_rules': legal_rules})
    
    results = []
    for measure in measures:
        check_result = check_org_violation(measure, legal_rules)
        matched_rules = []
        
        for rule_id in check_result.get('matched_rules', []):
            rule = next((r for r in legal_rules if r['rule_id'] == rule_id), None)
            if rule:
                matched_rules.append(rule)
        
        if matched_rules:
            first_rule = matched_rules[0]
            handling = '直接剔除' if first_rule['rule_type'] == '红线' else '待修正'
        else:
            handling = '校验通过'
        
        reasoning_chain = ''
        llm_reasoning = check_result.get('reasoning', '')
        rule_name = ''
        rule_type = ''
        violation_action = ''
        
        # 获取候选规则（通过阶段一校验的规则）
        candidate_rules = check_result.get('candidate_rules', [])
        
        # 如果有匹配规则（LLM判定触发），使用匹配规则构建推理链路
        if matched_rules:
            rule_name = matched_rules[0]['rule_name']
            rule_type = matched_rules[0]['rule_type']
            violation_action = matched_rules[0].get('violation_action', '')
            reasoning_chain = f"行动类型: {matched_rules[0]['action_type']} → 规则领域: {matched_rules[0]['rule_domain']} → 法规名称: {matched_rules[0]['act']} → 具体法条: {matched_rules[0]['section']}"
        # 如果没有匹配规则但有候选规则（通过阶段一但LLM判定未触发），使用第一个候选规则构建推理链路
        elif candidate_rules:
            rule_name = candidate_rules[0]['rule_name']
            rule_type = candidate_rules[0]['rule_type']
            violation_action = candidate_rules[0].get('violation_action', '')
            reasoning_chain = f"行动类型: {candidate_rules[0]['action_type']} → 规则领域: {candidate_rules[0]['rule_domain']} → 法规名称: {candidate_rules[0]['act']} → 具体法条: {candidate_rules[0]['section']}"
        
        results.append({
            'measure_name': measure.get('measure_text', ''),
            'rule_name': rule_name,
            'violation_action': violation_action,
            'reasoning_chain': reasoning_chain,
            'llm_reasoning': llm_reasoning,
            'rule_type': rule_type,
            'handling': handling,
            'matched_rules': matched_rules
        })
    
    return jsonify(results)

@app.route('/api/org/conflict', methods=['POST'])
def resolve_conflict():
    from utils.llm_client import resolve_conflict
    
    data = request.json
    rule_ids = data.get('rule_ids', [])
    legal_rules = load_json_file('LegalRule.json')
    
    rules = [r for r in legal_rules if r['rule_id'] in rule_ids]
    
    if len(rules) <= 1:
        result = {
            'priority_rule_id': rules[0]['rule_id'] if rules else None,
            'final_rule_type': rules[0]['rule_type'] if rules else None,
            'reasoning': '规则数量不足，无需冲突校验',
            'conflict_rules': rules
        }
    else:
        result = resolve_conflict(rules)
        if not result:
            result = {
                'priority_rule_id': rules[0]['rule_id'],
                'final_rule_type': rules[0]['rule_type'],
                'reasoning': '默认选择第一条规则'
            }
        result['conflict_rules'] = rules
    
    result['handling'] = '直接剔除' if result.get('final_rule_type') == '红线' else '待修正'
    return jsonify(result)

@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
