[![wxauto](https://github.com/cluic/wxauto/blob/WeChat3.9.11/utils/wxauto.png)](https://docs.wxauto.org)
# wxauto  (适用PC微信3.9.11.17版本）

### 欢迎指出bug，欢迎pull requests

Windows版本微信客户端自动化，可实现简单的发送、接收微信消息、保存聊天图片

**3.9.11.17版本微信安装包下载**：
[点击下载](https://github.com/tom-snow/wechat-windows-versions/releases/download/v3.9.11.17/WeChatSetup-3.9.11.17.exe)

**文档**：
[使用文档](https://docs.wxauto.org) |
[云服务器wxauto部署指南](https://docs.wxauto.org/other/deploy)

|  环境  | 版本 |
| :----: | :--: |
|   OS   | [![Windows](https://img.shields.io/badge/Windows-10\|11\|Server2016+-white?logo=windows&logoColor=white)](https://www.microsoft.com/)  |
|  微信  | [![Wechat](https://img.shields.io/badge/%E5%BE%AE%E4%BF%A1-3.9.11.X-07c160?logo=wechat&logoColor=white)](https://pan.baidu.com/s/1FvSw0Fk54GGvmQq8xSrNjA?pwd=vsmj) |
| Python | [![Python](https://img.shields.io/badge/Python-3.X-blue?logo=python&logoColor=white)](https://www.python.org/) **(不支持3.7.6和3.8.1)**|



[![Star History Chart](https://api.star-history.com/svg?repos=cluic/wxauto&type=Date)](https://star-history.com/#cluic/wxauto)

## 获取wxauto
cmd窗口：
```shell
pip install wxauto
```
python窗口：
```python
>>> import wxauto
>>> wxauto.VERSION
'3.9.11.17'
>>> wx = wxauto.WeChat()
初始化成功，获取到已登录窗口：xxx
```

## 示例
> [!NOTE]
> 如有问题请先查看[使用文档](https://docs.wxauto.org)

**请先登录PC微信客户端**

```python
from wxauto import *


# 获取当前微信客户端
wx = WeChat()


# 获取会话列表
wx.GetSessionList()

# 向某人发送消息（以`文件传输助手`为例）
msg = '你好~'
who = '文件传输助手'
wx.SendMsg(msg, who)  # 向`文件传输助手`发送消息：你好~


# 向某人发送文件（以`文件传输助手`为例，发送三个不同类型文件）
files = [
    'D:/test/wxauto.py',
    'D:/test/pic.png',
    'D:/test/files.rar'
]
who = '文件传输助手'
wx.SendFiles(filepath=files, who=who)  # 向`文件传输助手`发送上述三个文件


# 下载当前聊天窗口的聊天记录及图片
msgs = wx.GetAllMessage(savepic=True)   # 获取聊天记录，及自动下载图片
```
## 注意事项
目前还在开发中，测试案例较少，使用过程中可能遇到各种Bug

## 交流

[微信交流群](https://wxauto.loux.cc/docs/intro#-%E4%BA%A4%E6%B5%81)

## 最后
如果对您有帮助，希望可以帮忙点个Star，如果您正在使用这个项目，可以将右上角的 Unwatch 点为 Watching，以便在我更新或修复某些 Bug 后即使收到反馈，感谢您的支持，非常感谢！

## 免责声明
代码仅用于对UIAutomation技术的交流学习使用，禁止用于实际生产项目，请勿用于非法用途和商业用途！如因此产生任何法律纠纷，均与作者无关！

# 微信微博热搜与AI助理机器人

这是一个基于 Python 和 `wxauto` 库实现的微信机器人，能够提供实时的微博热搜信息，并集成AI模型提供智能问答功能。用户可以通过简单的指令查询热搜榜，也可以与AI进行对话。

## ✨ 功能特性

- **实时热搜查询**: 获取最新的微博热搜榜 Top 50。
- **热搜榜前五**: 快速查看当前最热门的前五条热搜。
- **指定排名查询**: 查询特定排名的热搜详情。
- **AI智能问答**: 集成大型语言模型，提供智能聊天和问答功能。
- **自动推送**: 当热搜前五名发生变化时，自动向指定联系人或群聊推送更新。
- **灵活控制**: 可以随时开启或关闭自动推送功能。
- **日志记录**: 记录所有收发消息及系统事件，便于调试和追踪。

## 📂 项目结构

```
.
├── bot_main.py             # 机器人主程序
├── gpt_handler.py          # AI问答处理模块
├── hot_search_db.py        # 数据库操作模块
├── hot_search_formatter.py   # 消息格式化模块
├── logs/                     # 日志目录
├── requirements.txt          # Python 依赖
└── README.md                 # 项目说明
```

## 🚀 快速开始

### 1. 环境准备

- Python 3.x
- 一台安装并登录了微信PC版的Windows电脑。
- 一个可用的 MySQL 数据库。
- 一个 DeepSeek 的 API Key。

### 2. 安装依赖

克隆本项目到本地，然后通过 pip 安装所需的依赖库：

```bash
pip install -r requirements.txt
```

### 3. 数据库设置

机器人需要从 MySQL 数据库中读取热搜数据。

1.  **数据库连接**:
    打开 `hot_search_db.py` 文件，根据您的数据库配置修改以下连接信息：
    ```python
    return pymysql.connect(
        host='localhost',  # 数据库服务器地址
        user='root',       # 数据库用户名
        password='123456', # 数据库密码
        database='weibo_hot', # 数据库名称
        port=3306,         # 数据库端口
        charset='utf8mb4', # 字符集
    )
    ```

2.  **数据表**:
    请确保数据库中存在名为 `hot_top50_final` 的表，并且该表由另外的爬虫程序持续更新。机器人本身不包含爬虫功能，只负责读取和展示数据。该表需要包含以下字段：
    - `rank_num` (INT): 排名
    - `title` (VARCHAR): 标题
    - `hot_value` (VARCHAR): 热度值
    - `link` (VARCHAR): 链接
    - `analysis_content` (TEXT): AI分析内容 (可选)
    - `fetch_time` (DATETIME): 抓取时间
    - `analysis_time` (DATETIME): 分析时间
    - `update_time` (DATETIME): 更新时间

### 4. 配置机器人

1.  **设置监听对象**:
    打开 `bot_main.py` 文件，配置您希望机器人监听的聊天对象：
    ```python
    # 设置需要监听的聊天窗口列表
    self.listen_list = [
        '小号'        # 在这里填入您想监听的联系人或群聊名称
    ]
    ```

2.  **设置AI模型**:
    本项目使用 DeepSeek 作为大型语言模型提供方。请在您的系统环境变量中设置 `DEEPSEEK_API_KEY`。
    - Windows: `set DEEPSEEK_API_KEY=你的API_KEY`
    - Linux/macOS: `export DEEPSEEK_API_KEY=你的API_KEY`
    
    机器人启动后，`gpt_handler.py` 会自动读取此环境变量。

### 5. 运行机器人

确保您的微信PC版已经登录，然后运行主程序：

```bash
python bot_main.py
```

机器人启动后，会开始监听指定聊天窗口的消息。

## 🤖 如何使用

在您配置的聊天窗口中发送以下指令或内容：

- `#微博热搜`: 获取完整的 Top 50 微博热搜榜。
- `#热搜前五`: 获取当前热搜榜前五名。
- `#热搜<数字>`: 获取指定排名的热搜，例如 `#热搜1`。
- `#开启自动推送`: 开启热搜前五变化的自动推送功能。
- `#关闭自动推送`: 关闭自动推送功能。
- **其他任意内容**: 发送除上述指令外的任何文本消息，都将由AI助手进行回复。

---

祝您使用愉快！



