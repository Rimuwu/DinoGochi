import pymongo

client = pymongo.MongoClient('localhost', 27017)

for i in client.list_databases():
    if i['name'] not in ['admin', 'local', 'bot', 'config']:
        client.drop_database(i['name'])
    print(i)