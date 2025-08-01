<h1 style="text-align: center;">数据库和Web服务器根目录备份工具</h1>

# 简介
备份本机的MySQL/MariaDB、PostgreSQL数据库和/var/www至当前目录的Backup文件夹下，并生成zip压缩包。

# 特征
- 支持MySQL/MariaDB和PostgreSQL数据库
- 备份/var/www
- 在备份文件内内嵌每个文件的sha256校验和以支持数据完整性校验
- 自动清理旧备份以节省空间
- 详细的日志记录
- 为Linux设计

# 依赖项
- [humanize](https://github.com/python-humanize/humanize)

# 使用方法
1. 安装Python
2. [安装uv](https://docs.astral.sh/uv/getting-started/installation/)
3. 克隆本仓库
    ```shell
    git clone https://github.com/TheWhiteDog9487/DatabaseAndWebsiteBackup
    cd DatabaseAndWebsiteBackup
    ```
4. 运行脚本
    ```shell
    uv run Backup.py
    ```

# 未来（可能有的）更新
- 协程
- 将备份内容同步至Cloudflare R2
- **注册为systemd服务（重要）**

什么时候做啊，没个准数呢  
可能什么时候会更新，也有可能什么时候提桶跑路了ㄟ(≧◇≦)ㄏ

# 注意事项
**本项目不保证使用方法和文件结构的向后兼容**

# 许可证
WTFPL

# 碎碎念
[Copilot](https://copilot.github.com/)太好用了  
我+Copilot+Copilot Edit就这么一路把这东西给莽了出来