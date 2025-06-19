"""
微博热搜机器人主程序
负责监听微信消息并根据指令提供微博热搜服务
"""
from wxauto import WeChat
import time
import os
import datetime
import sys
import re
import threading
import hot_search_db as hot_db  # 导入热搜数据库模块
import hot_search_formatter as formatter  # 导入热搜格式化模块
import gpt_handler  # 导入GPT回复模块

# 添加当前目录到系统路径，以便导入同级模块
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)


class WeiboBot:
    """微博热搜机器人类，封装微信监听和消息处理功能"""
    
    def __init__(self):
        """初始化机器人，设置日志和监听列表"""
        # 设置日志目录
        self.log_dir = 'logs'
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
        # 获取今天的日期作为日志文件名
        self.log_file = os.path.join(self.log_dir, f'chat_log_{datetime.datetime.now().strftime("%Y-%m-%d")}.txt')
        
        # 初始化微信对象
        self.wx = WeChat()
        
        # 获取机器人自己的昵称
        sessions = self.wx.GetSessionList()
        self.my_name = sessions.get('MyAccount')
        if self.my_name:
            self.log_message("SYSTEM", "Bot", f"成功获取到机器人用户名: {self.my_name}")
        else:
            self.log_message("ERROR", "Bot", "获取机器人用户名失败，可能会处理自己的消息")
        
        # 设置需要监听的聊天窗口列表
        self.listen_list = [
            '小号'
        ]

        # 定义指令列表
        self.commands = {
            "#微博热搜": self.handle_weibo_hot,
            "#热搜前五": self.handle_top_five_hot_search,
            "#开启自动推送": self.handle_toggle_auto_push,
            "#关闭自动推送": self.handle_toggle_auto_push,
        }

        # 热搜自动推送设置
        self.auto_push_enabled = True  # 是否启用自动推送
        self.push_interval = 60  # 推送间隔，默认1小时
        self.last_push_time = datetime.datetime.now() - datetime.timedelta(hours=1)  # 上次推送时间，初始化为1小时前
        
        # 存储上次检测到的前五热搜标题，用于比较是否有变化
        self.last_top_five_titles = []
        
        # 记录启动日志
        self.log_message("SYSTEM", "Bot", f"机器人启动，监听列表: {', '.join(self.listen_list)}")

    def log_message(self, message_type, sender, content):
        """
        记录消息到日志文件
        
        Args:
            message_type: 消息类型（SYSTEM/RECEIVED/ERROR）
            sender: 发送者
            content: 消息内容
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] [{message_type}] [{sender}]: {content}\n")
            
    def start_listening(self):
        """开始监听微信消息"""
        # 添加所有聊天窗口到监听列表
        for chat_name in self.listen_list:
            self.wx.AddListenChat(who=chat_name)
            self.log_message("SYSTEM", "Bot", f"开始监听: {chat_name}")
            
        print(f"机器人已启动，日志文件: {self.log_file}")
        
        # 启动时推送一次热搜前五
        self.push_hot_search_to_all(is_startup=True)
        self.log_message("SYSTEM", "Bot", "启动时推送热搜前五")
        
        # 启动热搜自动推送线程
        if self.auto_push_enabled:
            self.start_auto_push_thread()
            self.log_message("SYSTEM", "Bot", f"热搜自动推送已启动，每{self.push_interval//60}分钟检查一次更新")
        
        # 主循环，每1秒检查一次新消息
        while True:
            msgs = self.wx.GetListenMessage()
            for chat in msgs:
                who = chat.who  # 聊天窗口名（人或群名）
                one_msgs = msgs[chat]  # 该窗口的消息列表
                
                for msg in one_msgs:
                    msgtype = msg.type  # 消息类型
                    content = msg.content  # 消息内容
                    sender = msg.sender if hasattr(msg, 'sender') else who
                    
                    # 检查消息是否由机器人自己或系统发送，如果是则忽略
                    if sender == self.my_name or sender == 'Self' or sender == 'SYS':
                        continue
            
                    # 记录收到的消息
                    self.log_message("RECEIVED", f"{who}/{sender}", content)
                    print(f"【{who}】：{content}")
                            
                    # 处理消息指令
                    self.process_message(chat, who, sender, msgtype, content)
                    
            time.sleep(1)  # 等待1秒
    
    def start_auto_push_thread(self):
        """启动自动推送线程"""
        thread = threading.Thread(target=self.auto_push_loop)
        thread.daemon = True
        thread.start()
        print("自动推送线程已启动")
    
    def auto_push_loop(self):
        """自动推送循环"""
        while True:
            try:
                # 首先检查自动推送是否启用
                if not self.auto_push_enabled:
                    # 如果自动推送已关闭，则不执行推送逻辑
                    time.sleep(10)  # 每10秒检查一次是否重新启用
                    continue
                    
                # 检查是否需要推送（距离上次推送已经过了足够时间）
                now = datetime.datetime.now()
                if (now - self.last_push_time).total_seconds() >= self.push_interval:
                    # 检查前五热搜是否有变化
                    has_update = self.check_top_five_changed()
                    if has_update:
                        # 获取热搜数据并推送
                        self.push_hot_search_to_all(is_startup=False)
                        # 更新上次推送时间
                        self.last_push_time = now
                        self.log_message("SYSTEM", "Bot", f"检测到前五热搜变化，已自动推送热搜更新")
            except Exception as e:
                print(f"自动推送异常: {str(e)}")
                self.log_message("ERROR", "Bot", f"自动推送异常: {str(e)}")
            
            # 等待一段时间再次检查
            time.sleep(10)  # 每10秒检查一次
    
    def check_top_five_changed(self):
        """
        检查前五热搜是否有变化（标题或排名变化）
        
        Returns:
            bool: 是否有变化
        """
        try:
            # 获取前5条热搜数据
            hot_searches = hot_db.get_top_hot_searches(5)
            if not hot_searches:
                return False
            
            # 提取前5条热搜的标题和排名
            current_hot_searches = [(hot['rank_num'], hot['title']) for hot in hot_searches]
            
            # 如果是第一次检查，记录热搜信息并返回False
            if not self.last_top_five_titles:
                self.last_top_five_titles = current_hot_searches
                return False
            
            # 检查前五热搜标题或排名是否有变化
            if current_hot_searches != self.last_top_five_titles:
                # 记录变化详情
                changes = []
                for i, (curr, last) in enumerate(zip(current_hot_searches, self.last_top_five_titles)):
                    if curr != last:
                        changes.append(f"位置{i+1}: {last[1]}({last[0]}) -> {curr[1]}({curr[0]})")
                
                change_log = "，".join(changes)
                self.log_message("SYSTEM", "Bot", f"检测到前五热搜变化: {change_log}")
                
                # 更新记录的热搜信息
                self.last_top_five_titles = current_hot_searches
                return True
            
            return False
        except Exception as e:
            self.log_message("ERROR", "Bot", f"检查前五热搜变化异常: {str(e)}")
            return False
    
    def push_hot_search_to_all(self, is_startup=False):
        """
        向所有监听对象推送热搜
        
        Args:
            is_startup: 是否是启动时的推送
        """
        try:
            # 获取前5条热搜数据
            hot_searches = hot_db.get_top_hot_searches(10)
            if not hot_searches:
                self.log_message("ERROR", "Bot", "获取热搜数据失败，无法推送")
                return
            
            # 格式化前5条热搜数据
            hot_text = formatter.format_top_five_hot_searches(hot_searches)
            
            # 添加自动推送标识
            if is_startup:
                hot_text = "【启动推送】\n" + hot_text
            else:
                hot_text = "【自动推送】\n" + hot_text
            
            # 向所有监听对象发送消息
            for chat_name in self.listen_list:
                try:
                    self.wx.SendMsg(hot_text, chat_name)
                    self.log_message("SENT", "Bot", f"已向 {chat_name} 推送热搜更新")
                except Exception as e:
                    self.log_message("ERROR", "Bot", f"向 {chat_name} 推送热搜失败: {str(e)}")
        
        except Exception as e:
            self.log_message("ERROR", "Bot", f"推送热搜异常: {str(e)}")
            
    def process_message(self, chat, who, sender, msgtype, content):
        """
        处理收到的消息
        
        Args:
            chat: 聊天窗口对象
            who: 聊天窗口名称
            sender: 消息发送者
            msgtype: 消息类型
            content: 消息内容
        """
        content_stripped = content.strip()
        
        # 检查是否是固定指令
        if content_stripped in self.commands:
            # 如果是开启或关闭推送，需要传递参数
            if content_stripped in ["#开启自动推送", "#关闭自动推送"]:
                self.commands[content_stripped](chat, who, content_stripped)
            else:
                self.commands[content_stripped](chat, who)
            return

        # 检查是否是带参数的指令，如 #热搜29
        if re.match(r'^#热搜\d+$', content_stripped):
            rank = int(content_stripped[3:])
            self.handle_single_hot_search(chat, who, rank)
            return

        # 如果不是任何指令，则调用大模型回复
        if not content_stripped:
            return # 忽略空消息

        try:
            self.log_message("INFO", "Bot", f"向GPT发送消息: {content}")
            gpt_reply = gpt_handler.get_gpt_reply(content)
            chat.SendMsg(gpt_reply)
            self.log_message("SENT", "Bot", f"回复 {who} (GPT): {gpt_reply}")
        except Exception as e:
            error_msg = f"调用GPT失败: {str(e)}"
            chat.SendMsg(error_msg)
            self.log_message("ERROR", "Bot", error_msg)
            
    def handle_weibo_hot(self, chat, who):
        """
        处理微博热搜请求
        
        Args:
            chat: 聊天窗口对象
            who: 聊天窗口名称
        """
        try:
            # 获取前50条热搜数据
            hot_searches = hot_db.get_all_hot_searches(50)
            
            if not hot_searches:
                error_msg = "获取热搜数据失败，请稍后再试"
                chat.SendMsg(error_msg)
                self.log_message("ERROR", "Bot", error_msg)
                return
            
            # 格式化热搜数据（包含排名、标题和热度）
            hot_text = formatter.format_all_hot_searches(hot_searches)
            
            # 发送消息
            chat.SendMsg(hot_text)
            
            # 记录发送的回复
            self.log_message("SENT", "Bot", f"回复 {who}: 微博热搜数据")
            
        except Exception as e:
            error_msg = f"获取微博热搜失败: {str(e)}"
            chat.SendMsg(error_msg)
            self.log_message("ERROR", "Bot", error_msg)
            
    def handle_top_five_hot_search(self, chat, who):
        """
        处理热搜前五请求
        
        Args:
            chat: 聊天窗口对象
            who: 聊天窗口名称
        """
        try:
            # 获取前10条热搜数据
            hot_searches = hot_db.get_top_hot_searches(10)
            
            if not hot_searches:
                error_msg = "获取热搜数据失败，请稍后再试"
                chat.SendMsg(error_msg)
                self.log_message("ERROR", "Bot", error_msg)
                return
            
            # 格式化前5条热搜数据
            hot_text = formatter.format_top_five_hot_searches(hot_searches)
            
            # 发送消息
            chat.SendMsg(hot_text)
            
            # 记录发送的回复
            self.log_message("SENT", "Bot", f"回复 {who}: 热搜前五数据")
            
        except Exception as e:
            error_msg = f"获取热搜前五失败: {str(e)}"
            chat.SendMsg(error_msg)
            self.log_message("ERROR", "Bot", error_msg)
            
    def handle_single_hot_search(self, chat, who, rank):
        """
        处理单条热搜查询请求
        
        Args:
            chat: 聊天窗口对象
            who: 聊天窗口名称
            rank: 热搜排名
        """
        try:
            # 检查排名是否在有效范围内
            if rank < 1 or rank > 50:
                reply = "热搜排名必须在1-50之间"
                chat.SendMsg(reply)
                self.log_message("SENT", "Bot", f"回复 {who}: {reply}")
                return
            
            # 获取指定排名的热搜
            hot = hot_db.get_hot_search_by_rank(rank)
            
            if not hot:
                reply = f"未找到排名为{rank}的热搜"
                chat.SendMsg(reply)
                self.log_message("SENT", "Bot", f"回复 {who}: {reply}")
                return
            
            # 格式化单条热搜数据
            hot_text = formatter.format_single_hot_search(hot)
            
            # 发送消息
            chat.SendMsg(hot_text)
            
            # 记录发送的回复
            self.log_message("SENT", "Bot", f"回复 {who}: 单条热搜数据")
            
        except Exception as e:
            error_msg = f"获取单条热搜失败: {str(e)}"
            chat.SendMsg(error_msg)
            self.log_message("ERROR", "Bot", error_msg)

    def handle_toggle_auto_push(self, chat, who, command):
        """处理开启/关闭自动推送的指令"""
        if command == "#开启自动推送":
            self.auto_push_enabled = True
            reply = "已开启热搜自动推送"
        else: # command == "#关闭自动推送"
            self.auto_push_enabled = False
            reply = "已关闭热搜自动推送"
        
        chat.SendMsg(reply)
        self.log_message("SENT", "Bot", f"回复 {who}: {reply}")


# 程序入口点
if __name__ == "__main__":
    try:
        # 启动机器人
        bot = WeiboBot()
        bot.start_listening()
    except KeyboardInterrupt:
        print("程序被手动中断")
    except Exception as e:
        print(f"程序异常: {e}")
