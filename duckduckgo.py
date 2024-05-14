import errno
import logging
import os
import datetime
import sys
import tarfile
import shutil
from email import policy
from email.parser import BytesParser
import tempfile
import zipfile


#默认邮件目录
MAIL_DIR = "D:\\temp\\haolaos"  
#21版本代码根目录
V21_ROOT_DIR = "D:\\duck\\Sources\\x32"
#23版本代码根目录
V23_ROOT_DIR = "D:\\duck\\Sources\\x64"


default_password = "haolaos"
TAR_GZ_EXT = ".tar.gz"
LOG_DIR = "D:\\temp\\haolaos"



LOG_FILE = os.path.join(LOG_DIR, "log.txt")

# 确保日志目录存在，如果不存在则创建
try:
    os.makedirs(LOG_DIR)
except OSError as e:
    if e.errno != errno.EEXIST:
        raise
# 配置日志
logging.basicConfig(level=logging.DEBUG, filename=LOG_FILE, filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

# 添加控制台日志处理器，用于输出DEBUG及以上级别的日志
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger('').addHandler(console_handler)
  
def get_email_date(eml_file):
    with open(eml_file, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)
        email_date_str = msg["Date"]
        email_date = datetime.datetime.strptime(
            email_date_str, "%a, %d %b %Y %H:%M:%S %z").replace(tzinfo=datetime.timezone.utc)
        return email_date



class NoEMLFilesFound(Exception):
    """
    自定义异常，用于表示未找到EML文件的情况。
    """
    pass
def safe_open(file_path, mode):
    """
    安全打开文件，避免路径穿越问题。
    """
    base_dir = os.path.dirname(file_path)
    if not base_dir or not base_dir.startswith(MAIL_DIR):
        raise ValueError("Invalid file path.")
    return open(file_path, mode)
 
 
def copy_dir_merge(src_dir, dst_dir, overwrite=False):  
    # 确保源目录存在  
    if not os.path.exists(src_dir):  
        logging.error(f"源目录 {src_dir} 不存在")  
        return  
  
    # 确保目标目录存在  
    if not os.path.exists(dst_dir):  
        os.makedirs(dst_dir)  
  
    # 遍历源目录中的文件和子目录  
    for root, dirs, files in os.walk(src_dir):  
        rel_path = os.path.relpath(root, src_dir)  # 相对于src_dir的路径  
        dst_path = os.path.join(dst_dir, rel_path)  # 在dst_dir中的对应路径  
  
        # 创建目标路径中的目录  
        if not os.path.exists(dst_path):  
            os.makedirs(dst_path)  
  
        # 复制文件  
        for file in files:  
            src_file = os.path.join(root, file)  
            dst_file = os.path.join(dst_path, file)  
  
            # 如果目标文件已存在  
            if os.path.exists(dst_file):   
                shutil.copy2(src_file, dst_file) 
                logging.info('覆盖文件：' + dst_file) 
            else:  
                # 如果目标文件不存在，就直接拷贝  
                shutil.copy2(src_file, dst_file)
                logging.warn('新增文件：' + dst_file) 
                  
    shutil.rmtree(src_dir)     


def safe_extract(attachment_path, dest_dir): 
    """
    安全解压附件到指定目录。
    
    该函数首先尝试将附件解压到一个临时目录，然后根据附件类型（加密zip或其它）进行处理，
    最终将需要的内容提取到目标目录中。如果目标目录包含"x64"，则会将"IPT"目录下的内容
    覆盖到"x64"目录下，否则覆盖到目标目录的"IPT"子目录下。
    
    """
    file_name = os.path.basename(attachment_path)
    try: 
        try:
            with tempfile.TemporaryDirectory(dir=tempfile.gettempdir()) as temp_dir:
                #如果是加密的zip，先解压出tar包  到临时目录，再删除zip
                if file_name.endswith(".zip"): 
                    with zipfile.ZipFile(attachment_path, "r") as zip_ref:
                        password = default_password.encode() if default_password else None
                        zip_ref.setpassword(password) 
                        zip_ref.extractall(temp_dir)

                    # 删除原始的.zip文件
                    os.remove(attachment_path)
                    # 把attachment_path字符串中结尾的.zip后缀去掉 追加上.gz 
                    file_name = file_name[:-4] + ".gz"  
                else:
                    #如果不是加密的zip，直接移动到临时目录
                    shutil.move(attachment_path, temp_dir)
               
                with tarfile.open(os.path.join(temp_dir, file_name), "r:gz") as tar: 
                    tar.extractall(temp_dir) 
                    #如果dest_dir包含x64，需要将解压包中的IPT目录下的内容覆盖到x64下面（上移一层），然后删除ipt_dir目录
                    if dest_dir == V23_ROOT_DIR: 
                        copy_dir_merge(os.path.join(temp_dir, "IPT"), dest_dir,True) 
                    else: 
                        copy_dir_merge(os.path.join(temp_dir, "IPT"), os.path.join(dest_dir,"IPT"),True) 
        except Exception as e:
            # 根据实际情况处理异常，例如记录日志、提示用户等
            logging.error(f"创建临时目录时发生错误：{e}")
     
    except (zipfile.BadZipFile, tarfile.TarError) as e:
        # 捕获并处理压缩文件相关的错误
        logging.error(f"Error extracting file: {e}")
    except Exception as e:
        # 捕获其他潜在错误
        logging.error(f"Unexpected error: {e}")
    finally:
        pass

def process_email_attachments(filtered_files):
    """
    处理日期从小到大排序的电子邮件附件。
    
    参数:
    filtered_files - 一个包含已过滤电子邮件文件路径的列表。
    
    说明:
    根据电子邮件文件中的开头字符串，是21版本还是23版本，附件提取到不同的目录。
    """    
    #添加一个自增变量，提示这是第几份邮件
    i = 0
    for eml_file in filtered_files:
        i+=1
        
        try:
            with safe_open(eml_file, "rb") as f:
                msg = BytesParser(policy=policy.default).parse(f)
                #获取邮件正文内容,以可读格式，不含html标签 提取邮件正文内容
                email_body = msg.get_body(preferencelist=("plain", "html")).get_content()
                #获取邮件主题
                msg.subject = msg.get("Subject")
                email_date = get_email_date(eml_file)
                logging.info(f'\n')
                logging.info(f"==================================================================")
                logging.info(f"=========================正在处理第{i}份邮件========================")
                logging.info(f"==================================================================")
                 
                logging.info(f"邮件日期：【{email_date} 】")
                logging.info(f"邮件主题：【{msg.subject} 】")
                logging.info(f"邮件正文：\n{email_body}")
                for part in msg.iter_attachments():
                    attachment_name = part.get_filename()
                    if attachment_name and attachment_name.startswith("source_code_"):
                        attachment_path = os.path.join(MAIL_DIR, attachment_name)
                        with safe_open(attachment_path, "wb") as attachment_file:
                            attachment_file.write(part.get_payload(decode=True))
                        logging.info(f"Extracted: {attachment_path}")
                      
                        if "21版本" in eml_file: 
                            safe_extract(attachment_path, V21_ROOT_DIR)
                        elif "23版本" in eml_file: 
                            safe_extract(attachment_path, V23_ROOT_DIR) 
                        else:
                            logging.debug(f"do not  processing {eml_file}: {e}")
            os.remove(eml_file)
        except Exception as e:
            logging.error(f"Failed to process email: {eml_file}")
            logging.error(e)

def find_eml_files(directory):
    """
    在指定目录及其子目录中查找所有 .eml 文件。
    
    参数:
    directory (str): 需要搜索的目录路径。
    
    返回:
    list: 包含所有找到的 .eml 文件的完整路径的列表。
    """
    if not os.path.isdir(directory):
        logging.error(f"指定的目录不存在: {directory}")
        return
    eml_files = []
    try:
        # 使用生成器代替列表，以优化内存使用和性能
        for root, __,files in os.walk(directory):
            for file in files:
                if file.endswith(".eml"): 
                    eml_files.append(os.path.join(root, file))
    except OSError as e:
        # 添加异常处理来增强代码的健壮性
        logging.error(f"无法访问目录或文件: {e}")
    return eml_files

def extract_attachments(start_date=None, check_interval=2):
    #如果是自动扫描，确定起始日期，默认只扫最近2天的邮件
    if start_date:
        start_date = datetime.datetime.strptime(
            start_date, "%Y%m%d").replace(tzinfo=datetime.timezone.utc)
    else:
        start_date = datetime.datetime.now(
            datetime.timezone.utc) - datetime.timedelta(days=check_interval)
  
    eml_files = find_eml_files(MAIL_DIR)
    if eml_files is None: 
        raise NoEMLFilesFound("No eml files were found in the specified directory. Please check the provided path.")
 
    # 过滤出符合日期要求的eml文件    
    filtered_files = []
    for eml_file in eml_files:
        with open(eml_file, "rb") as f:
            msg = BytesParser(policy=policy.default).parse(f)
            email_date_str = msg["Date"]
            email_date = datetime.datetime.strptime(
                email_date_str, "%a, %d %b %Y %H:%M:%S %z").replace(tzinfo=datetime.timezone.utc)
            if email_date >= start_date:
                filtered_files.append(eml_file)
            else:
                logging.debug("too old email, %s  will pass!" % f.name)
    # 按日期排序
    filtered_files.sort(key=lambda x: get_email_date(x))
    process_email_attachments(filtered_files)

if __name__ == "__main__":
    #从命令行参数中获取起始日期
    start_date = sys.argv[1] if len(sys.argv) > 1 else None
    extract_attachments(start_date)
