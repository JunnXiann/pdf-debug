import pandas as pd
from pymongo import MongoClient

excel_path = "SX倾斜data.xlsx"
df = pd.read_excel(excel_path)
df.drop(columns=['bid', '面积', '图片', '页码', '文件路径', '标签'], inplace=True)
df.rename(columns={'角度': 'degree'}, inplace=True)

uri = ""
client = MongoClient(uri)
db = client['tripitaka-aux']
collection = db['sx_fold']

for _, row in df.iterrows():
    if row['异常'] != '异常':
        key = row['fold_id']
        update_data = row.drop(['fold_id', '异常']).to_dict()
        collection.update_one({'fold_id': key}, {'$set': update_data})

print("Data updated successfully.")

