# SWUST 新生指南 - 大学新生信息检索平台

面向西南科技大学 2026 级新生的极简信息检索平台。新生搜索关键词即可找到入学、学习、生活相关的常见问题和答案。

## 快速开始

### 环境要求

- Python 3.12+
- Windows / macOS / Linux

### 安装步骤

```bash
# 1. 进入项目目录
cd freshman_search

# 2. 创建虚拟环境（推荐）
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# 3. 安装依赖
pip install -r requirements.txt

# 4. 初始化数据库
python manage.py migrate

# 5. 导入演示数据
python manage.py seed_data

# 6. 创建管理员账号
python manage.py createsuperuser

# 7. 启动开发服务器
python manage.py runserver

# 8. 访问
# 前台：http://127.0.0.1:8000/
# 后台：http://127.0.0.1:8000/admin/
```

## 功能概览

### 新生访客

- 按关键词搜索问题
- 按分类浏览问题
- 查看问题详情（官方信息/经验信息区分标注）
- 提交"有帮助"/"没有帮助"反馈
- 搜索无结果时提交未解决问题

### 管理员（Django Admin）

- 管理知识条目（增删改查、发布/下架、推荐）
- 管理问题分类
- 查看搜索记录和无结果搜索词
- 查看用户反馈和帮助率
- 处理未解决问题

## 运行测试

```bash
python manage.py test knowledge
```

## 技术栈

- Python 3.12 / Django 5.2 / SQLite
- Django 模板系统 + Bootstrap 5
- markdown-it-py（安全的 Markdown 渲染）

## 项目结构

```
freshman_search/
├── manage.py
├── config/              # Django 项目配置
│   ├── settings.py
│   └── urls.py
├── knowledge/           # 核心应用
│   ├── models.py        # 5 个数据模型
│   ├── views.py         # 视图函数
│   ├── admin.py         # Django Admin 配置
│   ├── urls.py          # URL 路由
│   ├── tests.py         # 28 个自动化测试
│   ├── templatetags/    # 自定义模板过滤器
│   └── management/commands/seed_data.py  # 演示数据生成
├── templates/           # HTML 模板
│   ├── base.html
│   ├── home.html
│   ├── search_results.html
│   ├── category_detail.html
│   ├── question_detail.html
│   ├── submit_question.html
│   ├── submit_success.html
│   ├── about.html
│   ├── 404.html
│   └── 500.html
├── static/              # 静态文件
│   ├── css/style.css
│   └── js/main.js
├── requirements.txt
├── .env.example
└── .gitignore
```

## 环境变量

复制 `.env.example` 为 `.env` 并修改（开发环境可直接使用默认值）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SECRET_KEY` | (开发用默认值) | Django 密钥 |
| `DEBUG` | `True` | 生产环境设为 `False` |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | 允许访问的主机 |
| `CONTENT_VERIFY_EXPIRY_DAYS` | `180` | 内容核验过期天数 |

## 后续规划

以下功能暂不开发，视项目验证结果决定是否加入：

- 用户注册登录系统
- 完善的推荐算法
- 全文搜索引擎（Elasticsearch）
- 数据分析看板
- 移动端小程序
- AI 智能问答

## 许可

本项目仅用于学习和验证目的。演示数据仅供参考，不构成任何官方承诺。
