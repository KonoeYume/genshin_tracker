"""Atomic bulk goal updates; never lower a target below recorded progress."""

CAPS=(20,40,50,60,70,80,90)


def apply(db, scope, level=None, ascension=None, talent=None):
    if scope=='reset':
        total=0
        for table in ('character_progress','weapon_copies','traveller_progress'):
            count=db.execute(f'''UPDATE {table} SET target_level=current_level,
                target_ascension=current_ascension''').rowcount
            total+=count
        for table in ('talent_progress','traveller_talent_progress'):
            total+=db.execute(f'UPDATE {table} SET target_level=current_level').rowcount
        return {'updated':total,'scope':'reset'}
    if scope not in ('characters','weapons','traveller'):
        raise ValueError('Choose characters, weapons, Traveller, or reset')
    if type(level) is not int or not 1<=level<=90 or type(ascension) is not int or not 0<=ascension<=6:
        raise ValueError('Enter a level from 1 to 90 and ascension from 0 to 6')
    if level>CAPS[ascension]:
        raise ValueError('Target level exceeds the selected ascension cap')
    if scope!='weapons' and (type(talent) is not int or not 1<=talent<=10):
        raise ValueError('Enter a talent target from 1 to 10')
    if scope=='characters':
        rows=db.execute('SELECT current_level,current_ascension,character_id FROM character_progress').fetchall()
        for current,current_asc,cid in rows:
            target_asc=max(ascension,current_asc)
            target_level=max(level,current)
            if target_level>CAPS[target_asc]:raise ValueError(f'Character {cid} has an invalid current level/ascension')
            db.execute('''UPDATE character_progress SET target_level=?,target_ascension=?
                WHERE character_id=?''',(target_level,target_asc,cid))
        db.execute('UPDATE talent_progress SET target_level=MAX(current_level,?)',(talent,))
        return {'updated':len(rows),'scope':scope}
    if scope=='weapons':
        rows=db.execute('''SELECT wc.id,w.rarity,wc.current_level,wc.current_ascension
            FROM weapon_copies wc JOIN weapons w ON w.id=wc.weapon_id''').fetchall()
        for copy_id,rarity,current,current_asc in rows:
            limit=4 if rarity<=2 else 6
            target_asc=max(min(ascension,limit),current_asc)
            target_level=max(min(level,CAPS[limit]),current)
            if target_asc>limit or target_level>CAPS[target_asc]:
                raise ValueError(f'Weapon copy {copy_id} has incompatible level/ascension')
            db.execute('UPDATE weapon_copies SET target_level=?,target_ascension=? WHERE id=?',
                       (target_level,target_asc,copy_id))
        return {'updated':len(rows),'scope':scope}
    row=db.execute('SELECT current_level,current_ascension FROM traveller_progress WHERE id=1').fetchone()
    if row is None:raise ValueError('Traveller progress is missing')
    target_asc=max(ascension,row[1]);target_level=max(level,row[0])
    if target_level>CAPS[target_asc]:raise ValueError('Traveller has an invalid current level/ascension')
    db.execute('UPDATE traveller_progress SET target_level=?,target_ascension=? WHERE id=1',
               (target_level,target_asc))
    db.execute('UPDATE traveller_talent_progress SET target_level=MAX(current_level,?)',(talent,))
    return {'updated':1,'scope':scope}
