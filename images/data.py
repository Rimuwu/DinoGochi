import json

with open('dino_data.json') as f:
    json_f = json.load(f)

def save(json_f):

    with open('dino_data.json', 'w') as f:
        json.dump(json_f, f)

def work(json_f):
    dinol = []
    eggl = []

    for i in json_f['elements'].keys():
        el = json_f['elements'][i]
        if el['type'] == "dino":
            dinol.append(int(i))
        elif el['type'] == "egg":
            eggl.append(int(i))

    json_f['data'] = {'dino': dinol, 'egg': eggl}
    save(json_f)

work(json_f)
