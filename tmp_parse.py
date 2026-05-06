import sys, re, json

html = sys.stdin.read()
pushes = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html)
print(f'Found {len(pushes)} push payloads')

for i, p in enumerate(pushes):
    if any(w in p.lower() for w in ['price', 'offer', 'minprice', 'hotel']):
        unescaped = p.replace('\\"', '"').replace('\\\\', '\\').replace('\\n', '\n')
        # Try to find JSON objects
        objs = re.findall(r'\{[^{}]+\}', unescaped)
        for j, obj in enumerate(objs[:5]):
            try:
                data = json.loads(obj)
                print(f'\nPush {i}, obj {j}:')
                print(json.dumps(data, indent=2, ensure_ascii=False)[:300])
            except:
                pass
