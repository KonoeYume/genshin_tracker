"""Keep overview fields, limiting sections to families with goal shortages."""


def from_overview(data):
    sections=[]
    for section in data['sections']:
        category=section['category']
        if category in ('character_exp','weapon_exp'):
            kind='character' if category=='character_exp' else 'weapon'
            exp=data['experience'][kind]
            if exp['required']>exp['owned']:
                sections.append(section)
            continue
        items=section['materials']
        selected=[]
        start=0
        while start<len(items):
            end=start+1
            while end<len(items) and items[end]['family']==items[start]['family']:
                end+=1
            group=items[start:end]
            if any(item['still_needed']>0 or item['convert_for_goal']>0 for item in group):
                selected.extend(group)
            start=end
        if selected:sections.append({**section,'materials':selected})
    return {**data,'sections':sections}
