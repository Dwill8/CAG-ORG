
const API_BASE = '/api';

let currentEventFeatures = {};
let currentSimilarCases = [];
let currentMeasures = [];

function showSection(sectionId) {
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    document.querySelectorAll('.section').forEach(section => section.classList.remove('active'));
    
    event.target.classList.add('active');
    document.getElementById(`${sectionId}-section`).classList.add('active');
    
    if (sectionId === 'cases') {
        loadGeopoliticalCases();
        loadEconomicCases();
    } else if (sectionId === 'rules') {
        loadRules();
    } else if (sectionId === 'llm') {
        loadLLMConfig();
    }
}

function showCaseTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    event.target.classList.add('active');
    document.getElementById(`${tabId}-tab`).classList.add('active');
}

async function loadGeopoliticalCases() {
    const response = await fetch(`${API_BASE}/cases/geopolitical`);
    const cases = await response.json();
    const tbody = document.getElementById('geopolitical-body');
    tbody.innerHTML = '';
    
    cases.forEach(c => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${c.case_id}</td>
            <td>${c.case_label}</td>
            <td>${c.case_type}</td>
            <td>${c.trigger_event}</td>
            <td>${c.strategic_goal}</td>
            <td>${c.decision_measures.join('<br>')}</td>
        `;
        tbody.appendChild(row);
    });
}

async function loadEconomicCases() {
    const response = await fetch(`${API_BASE}/cases/economic_security`);
    const cases = await response.json();
    const tbody = document.getElementById('economic-body');
    tbody.innerHTML = '';
    
    cases.forEach(c => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${c.case_id}</td>
            <td>${c.case_label}</td>
            <td>${c.case_type}</td>
            <td>${c.trigger_event}</td>
            <td>${c.strategic_goal}</td>
            <td>${c.decision_measures.join('<br>')}</td>
        `;
        tbody.appendChild(row);
    });
}

async function loadRules() {
    const response = await fetch(`${API_BASE}/rules`);
    const rules = await response.json();
    const tbody = document.getElementById('rules-body');
    tbody.innerHTML = '';
    
    rules.forEach(r => {
        const row = document.createElement('tr');
        const ruleTypeClass = r.rule_type === '红线' ? 'tag tag-red' : 'tag tag-yellow';
        row.innerHTML = `
            <td>${r.rule_id}</td>
            <td>${r.rule_name}</td>
            <td>${r.domain}</td>
            <td><span class="${ruleTypeClass}">${r.rule_type}</span></td>
            <td>${r.act}</td>
            <td>${r.section}</td>
            <td>${r.violation_action}</td>
            <td>${r.handling}</td>
        `;
        tbody.appendChild(row);
    });
}

async function loadLLMConfig() {
    const response = await fetch(`${API_BASE}/llm/config`);
    const config = await response.json();
    
    document.getElementById('llm-api-key').value = config.api_key;
    document.getElementById('llm-api-url').value = config.api_url;
    document.getElementById('llm-model').value = config.model;
    document.getElementById('llm-temperature').value = config.temperature;
}

async function saveLLMConfig() {
    const config = {
        api_key: document.getElementById('llm-api-key').value,
        api_url: document.getElementById('llm-api-url').value,
        model: document.getElementById('llm-model').value,
        temperature: parseFloat(document.getElementById('llm-temperature').value)
    };
    
    const response = await fetch(`${API_BASE}/llm/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    });
    
    const result = await response.json();
    const status = document.getElementById('llm-status');
    
    if (result.success) {
        status.className = 'status-message status-success';
        status.textContent = '配置保存成功';
    } else {
        status.className = 'status-message status-error';
        status.textContent = '配置保存失败';
    }
    
    setTimeout(() => {
        status.textContent = '';
        status.className = 'status-message';
    }, 3000);
}

async function parseEvent() {
    const eventText = document.getElementById('event-input').value;
    
    if (!eventText.trim()) {
        alert('请输入事件描述');
        return;
    }
    
    const response = await fetch(`${API_BASE}/event/parse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_text: eventText })
    });
    
    currentEventFeatures = await response.json();
    
    const resultDiv = document.getElementById('event-result');
    resultDiv.innerHTML = `
        <table class="result-table">
            <thead>
                <tr>
                    <th>字段</th>
                    <th>值</th>
                </tr>
            </thead>
            <tbody>
                <tr><td>事件类型</td><td>${currentEventFeatures.event_type}</td></tr>
                <tr><td>地区</td><td>${currentEventFeatures.region}</td></tr>
                <tr><td>主体</td><td>${currentEventFeatures.subject}</td></tr>
                <tr><td>对手</td><td>${currentEventFeatures.opponent}</td></tr>
                <tr><td>盟友</td><td>${currentEventFeatures.allies?.join(', ') || ''}</td></tr>
                <tr><td>触发因素</td><td>${currentEventFeatures.trigger_factors?.join(', ') || ''}</td></tr>
                <tr><td>战略目标</td><td>${currentEventFeatures.strategic_goal}</td></tr>
                <tr><td>约束标签</td><td>${currentEventFeatures.constraint_tags?.map(t => '<span class=\"tag\">' + t + '</span>').join(' ') || ''}</td></tr>
                <tr><td>风险标签</td><td>${currentEventFeatures.risk_tags?.map(t => '<span class=\"tag tag-red\">' + t + '</span>').join(' ') || ''}</td></tr>
                <tr><td>可能涉及规则</td><td>${currentEventFeatures.possible_rules?.join(', ') || ''}</td></tr>
            </tbody>
        </table>
    `;
}

async function searchCases() {
    if (!Object.keys(currentEventFeatures).length) {
        alert('请先解析事件');
        return;
    }
    
    const response = await fetch(`${API_BASE}/cag/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_features: currentEventFeatures })
    });
    
    const result = await response.json();
    currentSimilarCases = result.cases;
    
    const resultDiv = document.getElementById('search-result');
    let html = '';
    
    if (result.low_similarity_warning) {
        html += '<div class="warning-box">⚠️ 无高相似案例，仅供研究参考</div>';
    }
    
    html += `
        <table class="result-table">
            <thead>
                <tr>
                    <th>案例ID</th>
                    <th>案例标签</th>
                    <th>案例类型</th>
                    <th>相似度分数</th>
                    <th>匹配标签</th>
                    <th>相似理由</th>
                    <th>差异提示</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    currentSimilarCases.forEach(c => {
        const scoreColor = c.similarity_score >= 0.6 ? '#38a169' : '#e53e3e';
        html += `
            <tr>
                <td>${c.case_id}</td>
                <td>${c.case_label}</td>
                <td>${c.case_type}</td>
                <td><span style="color: ${scoreColor}; font-weight: bold;">${(c.similarity_score * 100).toFixed(1)}%</span></td>
                <td>${c.matched_tags?.map(t => '<span class=\"tag tag-green\">' + t + '</span>').join(' ') || ''}</td>
                <td>${c.similar_reason}</td>
                <td>${c.difference_hint}</td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    resultDiv.innerHTML = html;
}

async function generateMeasures() {
    if (!currentSimilarCases.length) {
        alert('请先检索相似案例');
        return;
    }
    
    console.log('生成措施 - 当前事件特征:', currentEventFeatures);
    console.log('生成措施 - 当前相似案例:', currentSimilarCases);
    
    const response = await fetch(`${API_BASE}/cag/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            similar_cases: currentSimilarCases, 
            event_features: currentEventFeatures 
        })
    });
    
    const result = await response.json();
    currentMeasures = result.measures;
    
    const resultDiv = document.getElementById('measures-result');
    
    let html = '<div class="summary-box">📋 ' + result.summary + '</div>';
    
    html += `
        <table class="result-table">
            <thead>
                <tr>
                    <th>措施ID</th>
                    <th>措施文本</th>
                    <th>参考案例</th>
                    <th>迁移逻辑</th>
                    <th>适用条件</th>
                    <th>风险提示</th>
                    <th>可能触发规则</th>
                    <th>置信度</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    currentMeasures.forEach(m => {
        html += `
            <tr>
                <td>${m.measure_id}</td>
                <td>${m.measure_text}</td>
                <td>${m.reference_case}</td>
                <td>${m.transfer_logic}</td>
                <td>${m.applicable_conditions}</td>
                <td><span class="tag tag-red">${m.risk_hint}</span></td>
                <td>${m.possible_rules?.join(', ') || ''}</td>
                <td>${(m.confidence * 100).toFixed(1)}%</td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    resultDiv.innerHTML = html;
}

async function checkORG() {
    if (!currentMeasures.length) {
        alert('请先生成初始措施');
        return;
    }
    
    const response = await fetch(`${API_BASE}/org/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ measures: currentMeasures })
    });
    
    const results = await response.json();
    
    const resultDiv = document.getElementById('org-result');
    
    let html = `
        <table class="result-table">
            <thead>
                <tr>
                    <th>措施名称</th>
                    <th>法条名称</th>
                    <th>推理链路</th>
                    <th>红线底线类型</th>
                    <th>处理方式</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    results.forEach((r, index) => {
        const handlingClass = r.handling === '直接剔除' ? 'tag tag-red' : 
                             r.handling === '待修正' ? 'tag tag-yellow' : 'tag tag-green';
        
        let conflictBtn = '';
        if (r.matched_rules && r.matched_rules.length > 1) {
            const ruleIds = r.matched_rules.map(r => r.rule_id).join(',');
            conflictBtn = '<button class="btn btn-danger" onclick="resolveConflict(\'' + ruleIds + '\', ' + index + ')">冲突校验</button>';
        }
        
        html += `
            <tr>
                <td>${r.measure_name}</td>
                <td>${r.rule_name || '-'}</td>
                <td>${r.reasoning_chain || '-'}</td>
                <td><span class="${handlingClass}">${r.rule_type || '-'}</span></td>
                <td><span class="${handlingClass}">${r.handling}</span></td>
                <td>${conflictBtn || '-'}</td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    resultDiv.innerHTML = html;
}

async function resolveConflict(ruleIds, rowIndex) {
    const response = await fetch(`${API_BASE}/org/conflict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rule_ids: ruleIds.split(',') })
    });
    
    const result = await response.json();
    
    let rulesHtml = '<h3>冲突规则详情：</h3>';
    result.conflict_rules.forEach((rule, index) => {
        rulesHtml += `
            <div style="border: 1px solid #ccc; padding: 10px; margin: 5px 0; background: #f9f9f9;">
                <strong>规则${index + 1}：${rule.rule_id}</strong><br>
                规则名称：${rule.rule_name}<br>
                规则领域：${rule.rule_domain}<br>
                规则类型：<span style="color: ${rule.rule_type === '红线' ? '#e53e3e' : '#d69e2e'}">${rule.rule_type}</span><br>
                法律类型：${rule.rule_class}<br>
                颁布年份：${rule.enacted_year}<br>
                行动类型：${rule.action_type}<br>
                法规名称：${rule.act}<br>
                具体法条：${rule.section}<br>
                违规行为：${rule.violation_action}<br>
                处理方式：${rule.handling}
            </div>
        `;
    });
    
    const modalHtml = `
        <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                    background: white; padding: 20px; border-radius: 8px; 
                    box-shadow: 0 4px 20px rgba(0,0,0,0.2); max-width: 800px; 
                    max-height: 80vh; overflow-y: auto; z-index: 1000;">
            <h2>🔍 冲突校验结果</h2>
            ${rulesHtml}
            <hr>
            <strong>优先级规则ID：</strong>${result.priority_rule_id}<br>
            <strong>最终规则类型：</strong><span style="color: ${result.final_rule_type === '红线' ? '#e53e3e' : '#d69e2e'}">${result.final_rule_type}</span><br>
            <strong>处理方式：</strong>${result.handling}<br>
            <strong>推理过程：</strong>${result.reasoning}<br>
            <button onclick="document.body.removeChild(document.getElementById('conflict-modal'))" 
                    style="margin-top: 15px; padding: 8px 16px; background: #4299e1; color: white; 
                           border: none; border-radius: 4px; cursor: pointer;">
                关闭
            </button>
        </div>
        <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; 
                    background: rgba(0,0,0,0.5); z-index: 999;" 
             onclick="document.body.removeChild(document.getElementById('conflict-modal'))"></div>
    `;
    
    const modalDiv = document.createElement('div');
    modalDiv.id = 'conflict-modal';
    modalDiv.innerHTML = modalHtml;
    document.body.appendChild(modalDiv);
}

document.addEventListener('DOMContentLoaded', () => {
    loadGeopoliticalCases();
    loadEconomicCases();
});
