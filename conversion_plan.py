"""Plan inventory conversions within one material family without changing inventory."""


def plan(owned, required, rate=3, interchangeable=False):
    """Return (unmet per item, converted outputs received per item).

    Tiered families are ordered low to high. A higher tier is served first,
    while every tier's own requirement is reserved before its surplus is used.
    Weekly boss drops are interchangeable at 1:1 within one boss family.
    """
    if len(owned) != len(required) or any(x < 0 for x in [*owned,*required]):
        raise ValueError('Inventory and requirements must match and be nonnegative')
    net = [have - need for have,need in zip(owned,required)]
    outputs = [0] * len(net)
    if interchangeable:
        for recipient in range(len(net)):
            for donor in range(len(net)):
                if donor == recipient or net[recipient] >= 0:
                    continue
                amount = min(-net[recipient], max(0,net[donor]))
                net[recipient] += amount
                net[donor] -= amount
                outputs[recipient] += amount
    else:
        if rate < 2:
            raise ValueError('Tier conversion rate must be at least two')

        def supply(tier):
            if tier == 0:
                return max(0,net[0])
            return max(0,net[tier] + supply(tier-1)//rate)

        def spend(tier, amount):
            if amount == 0:
                return
            if tier == 0:
                if net[0] < amount:
                    raise AssertionError('Conversion plan exceeded available inventory')
                net[0] -= amount
            elif net[tier] >= amount:
                net[tier] -= amount
            else:
                # Fill this tier's own deficit as well as the amount used above.
                created = amount-net[tier]
                spend(tier-1, rate*created)
                net[tier] = 0
                outputs[tier] += created

        for tier in range(len(net)-1,0,-1):
            deficit = max(0,-net[tier])
            crafted = min(deficit,supply(tier-1)//rate)
            spend(tier-1,rate*crafted)
            net[tier] += crafted
            outputs[tier] += crafted
    return [max(0,-balance) for balance in net], outputs
