# 虎扑世界杯评论爬虫

搜索虎扑"世界杯"相关帖子，提取评论并以 JSON / CSV 格式保存。

## 功能

- 搜索虎扑"世界杯"关键词帖子，支持多页翻页
- 提取每篇帖子的所有评论（支持评论翻页）
- 自动重试失败的请求，随机 User-Agent 降低封禁概率
- 输出 JSON + CSV（UTF-8 BOM）两种格式

## 环境要求

- Python 3.8+
- pip

## 安装

```bash
# 创建虚拟环境
python -m venv .venv

# 激活
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 配置

编辑 `hupu_worldcup_spider.py` 中的 `CONFIG` 字典：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `keyword` | `世界杯` | 搜索关键词 |
| `max_search_pages` | `4` | 搜索页数 |
| `max_posts` | `20` | 最多爬取帖子数 |
| `max_comments_per_post` | `50` | 每帖最多评论数 |
| `delay_min` / `delay_max` | `1.5` / `3.0` | 请求间隔（秒） |
| `timeout` | `15` | 请求超时（秒） |
| `retries` | `3` | 失败重试次数 |

## 运行

```bash
python hupu_worldcup_spider.py
```

## 输出

| 文件 | 格式 | 说明 |
|------|------|------|
| `worldcup_comments.json` | JSON | 完整数据结构，含嵌套 |
| `worldcup_comments.csv` | CSV | 表格格式，UTF-8 BOM 编码 |

### CSV 字段

`post_id`, `post_title`, `post_forum`, `floor`, `username`, `user_id`, `content`, `likes`, `time`, `location`, `quote`

## 项目结构

```
├── hupu_worldcup_spider.py   爬虫主程序
├── requirements.txt           依赖清单
├── .venv/                     虚拟环境（不提交）
├── worldcup_comments.json     运行产物
├── worldcup_comments.csv      运行产物
└── README.md                  本文件

## 联系方式

q_wr28857wfu@outlook.com
```

## 免责声明

本工具仅用于学习和研究，请合理设置请求间隔，遵守网站 `robots.txt` 协议。
