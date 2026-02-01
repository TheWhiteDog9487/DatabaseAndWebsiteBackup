<h1 style="text-align: center;">数据库和Web服务器根目录备份工具</h1>

# 简介
备份本机的MySQL/MariaDB、PostgreSQL数据库和/var/www至当前目录的Backup文件夹下，并生成zip压缩包。

# 功能特性
- 支持MySQL/MariaDB和PostgreSQL数据库
- 备份/var/www
- 在备份文件内内嵌每个文件的sha256校验和以支持数据完整性校验
- 自动清理旧备份以节省空间
- 自动备份到Cloudflare R2或其他S3兼容存储
- 自动确保本程序上传的备份数据总大小不超过R2免费层级
- 多线程同时进行备份压缩
- 根据`CustomPathList.txt`内提供的路径进行自定义位置的备份
- 在可用的情况下使用zstd以提高压缩率和压缩速度
- 详细的日志记录
- 为Linux设计

# 依赖项
- [humanize](https://github.com/python-humanize/humanize)
- [types-boto3](https://pypi.org/project/types-boto3)
- [Boto3](https://github.com/boto/boto3)

# 需要设置的环境变量
- S3相关( 如果不需要使用S3自动上传的功能可以不管 )  
  如果这四个变量中的任意一个不存在，则自动跳过上传备份
    - R2_Endpoint ：S3终结点URL
    - R2_Access_Key ：访问密钥ID
    - R2_Secret_Key ：机密访问密钥
    - R2_Bucket_Name ：存储桶名称

# 运行参数
- --skip-database-backup ：跳过数据库备份
- --skip-website-backup ：跳过/var/www备份
- --skip-certbot-backup ：跳过Certbot备份
- --skip-custom-path-backup ：跳过自定义路径备份
- --skip-upload ：跳过上传备份到S3兼容存储

# 使用方法
1. [安装uv](https://docs.astral.sh/uv/getting-started/installation/)
2. 克隆本仓库
    ```shell
    git clone https://github.com/TheWhiteDog9487/DatabaseAndWebsiteBackup
    cd DatabaseAndWebsiteBackup
    ```
3. 运行脚本
    ```shell
    uv run Main.py
    # 如果您需要备份PostgreSQL，请使用root执行上面的命令，或者使用下面的命令
    sudo uv run Main.py
    ```

# 未来（可能有的）更新
- **注册为systemd服务（重要）**
- **更改为持续性后台服务模式（重要）**

什么时候做啊，没个准数呢  
可能什么时候会更新，也有可能什么时候提桶跑路了ㄟ(≧◇≦)ㄏ

# 注意事项
**本项目不保证使用方法和文件结构的向后兼容**

# 许可证
WTFPL

# 碎碎念
[Copilot](https://copilot.github.com/)太好用了  
我+Copilot+Copilot Edit就这么一路把这东西给莽了出来