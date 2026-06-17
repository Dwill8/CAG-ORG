
# 美国国家决策智能体原型系统开发计划

## 项目结构
```
20260616mvp/
├── data/                    # 数据文件夹
│   ├── cases_geopolitical.json
│   ├── cases_economic_security.json
│   └── LegalRule.json
├── config/                  # 配置文件夹
│   └── llm_config.json
├── backend/                 # 后端代码
│   ├── app.py
│   ├── routes/
│   │   ├── data_routes.py
│   │   ├── llm_routes.py
│   │   ├── event_routes.py
│   │   ├── cag_routes.py
│   │   └── org_routes.py
│   └── utils/
│       ├── llm_client.py
│       └── similarity.py
├── frontend/                # 前端代码
│   ├── index.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── main.js
│       ├── data_display.js
│       ├── llm_config.js
│       └── decision_flow.js
└── start_server.py          # 启动脚本
```

## 开发任务

### Phase 1: 项目初始化
1. 创建项目目录结构
2. 创建虚拟环境配置
3. 安装依赖

### Phase 2: 数据层
4. 创建JSON数据文件（案例库、规则库）
5. 创建LLM配置文件

### Phase 3: 后端开发
6. 创建Flask主应用
7. 实现数据展示API（模块一）
8. 实现LLM配置API（模块二）
9. 实现事件解析API（模块三）
10. 实现CAG相似检索API（模块四）
11. 实现CAG泛化推理API（模块五）
12. 实现ORG校验API（模块六）

### Phase 4: 前端开发
13. 创建主页面HTML结构
14. 实现CSS样式
15. 实现左侧导航功能
16. 实现数据展示模块
17. 实现LLM配置模块
18. 实现决策运行模块（事件解析→相似检索→泛化推理→ORG校验）

### Phase 5: 测试与启动
19. 启动开发服务器
20. 验证功能
