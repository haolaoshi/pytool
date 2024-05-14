import os  
import re  
import csv  
from datetime import datetime  
import datetime
import sys  
def convert_double_to_datetime(double_time):  
    #因为要修复的数据是2024-05-10 所以这里写死，如果后续要使用，应该优化为从日志中获取
    base_date = datetime.datetime(2024, 5, 10)    
    fraction = double_time - int(double_time)  
    total_seconds = fraction * 86400  
    hours = int(total_seconds // 3600)  
    remaining_seconds = int(total_seconds % 3600)  
    minutes = int(remaining_seconds // 60)  
    seconds = int(remaining_seconds % 60)  
    converted_time = base_date + datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)  
    todate_before = converted_time.strftime('%Y-%m-%d %H:%M:%S') 
    
    return f"to_date('"+todate_before+"', 'yyyy-mm-dd hh24:mi:ss')"
def extract_tablename_with_regex(filename):  
    parts = filename.split('_')  
    if len(parts) > 1 and parts[-1].endswith('.bak'):  
        if '.' in parts[-1]:  
            parts[-1] = parts[-1].split('.')[0]  
        return '_'.join(parts[:-1])  
    else:  
        return None  
      
def generate_insert_statement_with_values(table_name, columns, values):  
    processed_values = []  
    for i, value in enumerate(values):  
        #针对特殊列进行处理，不加引号；如果太多的列需要处理，可以创建一个字典来映射索引和列名，然后根据索引获取列名
        if table_name == 'Call_Jour_21' and (i == 2 or i == 3) or table_name == 'Agent_Contentment_List' and (i == 1) :  # 索引从0开始，所以第3列是索引2，第4列是索引3  
            processed_values.append(str(value))   
        else:  
            processed_values.append("'" + str(value).replace("'", "''") + "'")   
    values_str = ', '.join(processed_values)  
    columns_str = ', '.join(columns)  
    sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str});"  
    return sql  
  
def process_log_files(log_directory, output_file):  
    files = [f for f in os.listdir(log_directory) if re.match(r'.*\.bak$', f)]  
    files.sort()  
  
    with open(output_file, 'w', encoding='utf-8') as out_file:  
        for file_name in files:  
            table_name = extract_tablename_with_regex(file_name)
            file_path = os.path.join(log_directory, file_name)  
            with open(file_path, 'r', encoding='utf-8') as log_file:  
                reader = csv.reader(log_file)  
                columns = next(reader)  
                for row in reader:  
                    #针对特殊列进行处理，这是delphi的日期格式是double，转化为oracle日期格式
                    if table_name == 'Call_Jour_21': 
                        row[2] = convert_double_to_datetime(float(row[2]))
                        row[3] = convert_double_to_datetime(float(row[3]))
                    elif table_name == 'Agent_Contentment_List':
                        row[1] = convert_double_to_datetime(float(row[1]))
                    insert_stmt = generate_insert_statement_with_values(table_name, columns, row)  
                    out_file.write(insert_stmt + '\n')  

if __name__ == "__main__":
    log_directory = sys.argv[1] if len(sys.argv) > 1 else None
    output_file = log_directory + '.sql'
    process_log_files(log_directory, output_file)
  
