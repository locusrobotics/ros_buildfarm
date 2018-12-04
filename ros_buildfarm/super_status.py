def merge_statuses(statuses):
    if len(statuses) == 1:
        return list(statuses)[0]
    all_waiting = True
    all_broken = True
    for status in statuses:
        if 'waiting' not in status:
            all_waiting = False
        if 'build' not in status:
            all_broken = False
    if all_waiting:
        return 'waiting for new/re-release'
    elif all_broken:
        return 'does not build on some platforms'
    else:
        return 'mixed'
