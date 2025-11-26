Jointelli_21h01_短信推送
这是一个用于从金英拓联5G CPE EVO (型号: 21H01) 设备抓取短信并自动推送至钉钉群机器人的Python脚本。

功能特点
🔐 自动登录CPE: 使用salt和SHA256加密方式安全登录CPE设备后台

📩 短信监控: 定时轮询CPE设备，自动检测和获取新接收的短信

🤖 钉钉推送: 通过钉钉自定义机器人（支持加签安全设置）将新短信实时推送到钉钉群

前置要求
Python 环境
Python 3.6 或更高版本

所需包: requests

设备与账号
金英拓联5G CPE EVO (型号: 21H01) 设备并已联网

具有访问CPE设备管理后台的管理员账号

钉钉群聊及已添加的自定义机器人（需开启加签安全设置）

安装与配置
bash
git clone https://github.com/NingLing520/jointelli_21h01_SMSpush.git #拉取仓库
cd jointelli_21h01_SMSpush
pip install -r requirements.txt #安装依赖
#编辑sms.py 配置钉钉机器人

在钉钉群中添加自定义机器人

安全设置选择"加签"，并记录下secret

记录webhook地址中的access_token

修改脚本配置
编辑脚本开头的配置区域：

python
CPE_BASE = "http://192.168.0.1"  # 您的CPE设备管理地址
USERNAME = "superadmin"          # CPE管理员用户名
PASSWORD = "your_password"       # CPE管理员密码

DING_ACCESS_TOKEN = "your_dingtalk_access_token"  # 钉钉机器人access_token
DING_SECRET = "your_dingtalk_secret"              # 钉钉机器人加签secret
使用方法
直接运行
bash
python sms_to_dingtalk.py
作为服务运行
建议使用以下方式在后台运行：

Linux/macOS: nohup 或 systemd

Windows: 任务计划程序 或 nssm

配置说明
配置项	说明
CPE_BASE	CPE设备管理后台地址，默认为 http://192.168.0.1
USERNAME	CPE设备登录用户名，默认为 superadmin
PASSWORD	CPE设备登录密码
DING_ACCESS_TOKEN	钉钉机器人Webhook的access_token参数
DING_SECRET	钉钉机器人安全设置的加签secret
CHECK_INTERVAL	短信检查间隔（秒），默认为5秒
钉钉消息格式
推送的钉钉消息格式如下：

text
📩【新短信】
来自：10086
时间：2025-11-26 12:44:21
内容：【流量查询】尊敬的客户您好...
许可证
MIT License

贡献
欢迎提交Issue和Pull Request！

